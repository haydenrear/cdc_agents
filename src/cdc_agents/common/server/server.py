import importlib
import os.path
import typing

import asyncio
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from starlette.requests import Request

import python_util.io_utils.file_dirs
from cdc_agents.agent.agent import A2AAgent
from cdc_agents.common.types import (
    A2ARequest,
    JSONRPCResponse,
    InvalidRequestError,
    JSONParseError,
    GetTaskRequest,
    CancelTaskRequest,
    SendTaskRequest,
    SetTaskPushNotificationRequest,
    GetTaskPushNotificationRequest,
    InternalError,
    AgentCard,
    TaskResubscriptionRequest,
    SendTaskStreamingRequest, PostAgentResponse, AgentPosted, AgentCode, AgentDescriptor, PushTaskEvent,
)
from pydantic import ValidationError
import json
from typing import AsyncIterable, Any
from cdc_agents.common.server.task_manager import TaskManager

import logging

from cdc_agents.common.utils.push_notification_auth import PushNotificationSenderAuth
from python_util.logger.logger import LoggerFacade
from python_util.reflection import reflection_utils

logger = logging.getLogger(__name__)


class A2AServer:
    def __init__(
        self,
        host="0.0.0.0",
        port=5000,
        endpoint="/",
        agent_card: AgentCard = None,
        task_manager: TaskManager = None,
        starlette: typing.Optional[Starlette] = None
    ):
        self.host = host
        self.port = port
        self.endpoint = f'/{agent_card.name}/{endpoint}'
        self.task_manager = task_manager
        self.agent_card = agent_card
        self.app = Starlette() if not starlette else starlette
        self.app.add_route(self.endpoint, self._process_request, methods=["POST"])
        self.app.add_route(
            f"/{agent_card.name}/.well-known/agent.json", self._get_agent_card, methods=["GET"])
        self.app.add_route(f"/{agent_card.name}/tasks/pushEvent", self.receive_event, methods=["POST", "GET", "PUT"])

    def start(self):
        if self.agent_card is None:
            raise ValueError("agent_card is not defined")

        if self.task_manager is None:
            raise ValueError("request_handler is not defined")

        import uvicorn

        uvicorn.run(self.app, host=self.host, port=self.port)

    async def receive_event(self, request: Request):
        try:
            body = await request.json()
            evt = PushTaskEvent(**body)
            return await self.on_receive_event(evt)
        except Exception as e:
            return self._handle_exception(e)

    async def on_receive_event(self, request: PushTaskEvent) -> JSONResponse:
        LoggerFacade.debug("Received event.")
        res = await self.task_manager.on_push_task_event(request)
        return self._create_response(res)

    def _get_agent_card(self, request: Request) -> JSONResponse:
        return JSONResponse(self.agent_card.model_dump(exclude_none=True))

    async def _process_request(self, request: Request):
        try:
            body = await request.json()
            json_rpc_request = A2ARequest.validate_python(body)

            if isinstance(json_rpc_request, GetTaskRequest):
                result = await self.task_manager.on_get_task(json_rpc_request)
            elif isinstance(json_rpc_request, SendTaskRequest):
                result = await self.task_manager.on_send_task(json_rpc_request)
            elif isinstance(json_rpc_request, SendTaskStreamingRequest):
                result = await self.task_manager.on_send_task_subscribe(
                    json_rpc_request
                )
            elif isinstance(json_rpc_request, CancelTaskRequest):
                result = await self.task_manager.on_cancel_task(json_rpc_request)
            elif isinstance(json_rpc_request, SetTaskPushNotificationRequest):
                result = await self.task_manager.on_set_task_push_notification(json_rpc_request)
            elif isinstance(json_rpc_request, GetTaskPushNotificationRequest):
                result = await self.task_manager.on_get_task_push_notification(json_rpc_request)
            elif isinstance(json_rpc_request, TaskResubscriptionRequest):
                result = await self.task_manager.on_resubscribe_to_task(
                    json_rpc_request
                )
            else:
                logger.warning(f"Unexpected request type: {type(json_rpc_request)}")
                raise ValueError(f"Unexpected request type: {type(request)}")

            return self._create_response(result)

        except Exception as e:
            return self._handle_exception(e)

    def _handle_exception(self, e: Exception) -> JSONResponse:
        if isinstance(e, json.decoder.JSONDecodeError):
            json_rpc_error = JSONParseError()
        elif isinstance(e, ValidationError):
            json_rpc_error = InvalidRequestError(data=json.loads(e.json()))
        else:
            logger.error(f"Unhandled exception: {e}")
            json_rpc_error = InternalError()

        response = JSONRPCResponse(id=None, error=json_rpc_error)
        return JSONResponse(response.model_dump(exclude_none=True), status_code=400)

    def _create_response(self, result: Any) -> JSONResponse | EventSourceResponse:
        if isinstance(result, AsyncIterable):

            async def event_generator(result) -> AsyncIterable[dict[str, str]]:
                async for item in result:
                    yield {"data": item.model_dump_json(exclude_none=True)}

            return EventSourceResponse(event_generator(result))
        elif isinstance(result, JSONRPCResponse):
            return JSONResponse(result.model_dump(exclude_none=True))
        else:
            logger.error(f"Unexpected result type: {type(result)}")
            raise ValueError(f"Unexpected result type: {type(result)}")

class DynamicA2AServer:
    def __init__(
            self,
            host="0.0.0.0",
            port=5000,
            endpoint="/dynamic_agents",
            agents: typing.Optional[typing.Dict] = None
    ):
        self.host = host
        self.port = port
        self.endpoint = endpoint
        self.app = Starlette()
        self.app.add_route("/dynamic_agents/put_agent", self._put_agent_card, methods=["POST"])
        self.agents = {} if not agents else agents

    def start(self):
        import uvicorn
        uvicorn.run(self.app, host=self.host, port=self.port)

    async def _put_agent_card(self, request: Request) -> JSONResponse:
        try:
            body = await request.json()
            return self._do_put_agent(body, self.agents)
        except Exception as e:
            return self._handle_exception(e)

    @staticmethod
    def _do_put_agent(body, agents):
        from cdc_agents.agent.task_manager import AgentTaskManager
        agent_card = AgentCard(**body['agent_card'])
        agent_code = AgentCode(**body['agent_code'])
        agent_descriptor = AgentDescriptor(**body['agent_descriptor'])

        host = body['host']
        port = body['port']

        py_file = agent_code.py_file

        if not py_file.endswith('.py'):
            py_file = f'{py_file}.py'

        to_write_to = os.path.join(python_util.io_utils.file_dirs.get_dir(__file__, 'agents'),
                                   py_file)

        if os.path.exists(to_write_to):
            return DynamicA2AServer._handle_exception(FileExistsError(f"File {py_file} existed - could not save new agent."))

        with open(to_write_to, 'w') as py_file_out:
            py_file_out.write(agent_code.code)

        try:
            tools = [importlib.import_module(t) for t in agent_descriptor.tools]
            model = agent_descriptor.model
            system_instructions = agent_descriptor.system_instruction

            loaded = importlib.import_module(python_util.io_utils.file_dirs.create_py_import(to_write_to, __file__))
            notification_sender_auth = PushNotificationSenderAuth()
            notification_sender_auth.generate_jwk()

            for k, v in loaded.__dict__.items():
                if isinstance(v, type) and reflection_utils.is_type_instance_of(A2AAgent, v):
                    agent: A2AAgent = v(model, tools, system_instructions)
                    importlib.import_module(agent_code.code)
                    agent_value = A2AServer(agent_card=agent_card,
                                            task_manager=AgentTaskManager(agent=agent,
                                                                          notification_sender_auth=notification_sender_auth),
                                            host=host,
                                            port=port)
                    agent_value.start()
                    agents[agent.agent_name] = agent_value
                    return JSONResponse(
                        PostAgentResponse(
                            result=AgentPosted(success=True, endpoint='/dynamic_agents/put_agent')).model_dump(exclude_none=True),
                        status_code=200)

            if os.path.exists(to_write_to):
                os.remove(to_write_to)

            return DynamicA2AServer._handle_exception(ModuleNotFoundError("Could not create agent."))
        except Exception as e:
            return DynamicA2AServer._handle_exception(e)


    @staticmethod
    def _handle_exception(e: Exception) -> JSONResponse:
        if isinstance(e, json.decoder.JSONDecodeError):
            json_rpc_error = JSONParseError()
        elif isinstance(e, ValidationError):
            json_rpc_error = InvalidRequestError(data=json.loads(e.json()))
        else:
            logger.error(f"Unhandled exception: {e}")
            json_rpc_error = InternalError()

        response = JSONRPCResponse(id=None, error=json_rpc_error)
        return JSONResponse(response.model_dump(exclude_none=True), status_code=400)

    def _create_response(self, result: Any) -> JSONResponse | EventSourceResponse:
        if isinstance(result, AsyncIterable):

            async def event_generator(result) -> AsyncIterable[dict[str, str]]:
                async for item in result:
                    yield {"data": item.model_dump_json(exclude_none=True)}

            return EventSourceResponse(event_generator(result))
        elif isinstance(result, JSONRPCResponse):
            return JSONResponse(result.model_dump(exclude_none=True))
        else:
            logger.error(f"Unexpected result type: {type(result)}")
            raise ValueError(f"Unexpected result type: {type(result)}")
