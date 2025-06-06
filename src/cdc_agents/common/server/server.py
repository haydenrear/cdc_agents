import importlib
import os.path
import typing

import asyncio
import pydantic
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse
from starlette.requests import Request

import python_util.io_utils.file_dirs
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
    SendTaskStreamingRequest, PostAgentResponse, AgentPosted, AgentCode, AgentDescriptor
)
from pydantic import ValidationError
import json
from typing import AsyncIterable, Any
from cdc_agents.common.server.task_manager import TaskManager

import logging

from cdc_agents.common.utils.push_notification_auth import PushNotificationSenderAuth
from cdc_agents.config.agent_config_props import AgentConfigProps
from python_util.logger.logger import LoggerFacade
from python_util.reflection import reflection_utils

logger = logging.getLogger(__name__)

def _add_managed_agents(agent_card: AgentCard, agent_config_props):
    if len(agent_card.names_of_managed_agents) != 0:
        agent_card.managed_agents.extend([ag.agent_card for ag in agent_config_props.agents.values()
                                          if ag.agent_card.name in agent_card.names_of_managed_agents])


def _add_all_managed_agents(agent_config_props: AgentConfigProps):
    for name, a in agent_config_props.agents.items():
        LoggerFacade.info(f"Loading agent: {name}")
        if a.exposed_externally:
            _add_managed_agents(a.agent_card, agent_config_props)

def create_json_response(result: Any) -> JSONResponse | EventSourceResponse:
    if isinstance(result, AsyncIterable):

        async def event_generator(result) -> AsyncIterable[dict[str, str]]:
            async for item in result:
                yield {"data": item.model_dump_json(exclude_none=True)}

        return EventSourceResponse(event_generator(result))
    elif isinstance(result, JSONRPCResponse):
        return JSONResponse(result.model_dump(exclude_none=True))
    elif isinstance(result, pydantic.BaseModel):
        return JSONResponse(content=result.model_dump(), status_code=200)
    else:
        logger.error(f"Unexpected result type: {type(result)}")
        raise ValueError(f"Unexpected result type: {type(result)}")


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
        self.endpoint = endpoint
        self.task_manager = task_manager
        self.agent_card = agent_card
        self.app = Starlette() if not starlette else starlette
        self.app.add_route(self.endpoint, self._process_request, methods=["POST"])
        self.app.add_route(
            f"/{endpoint}/.well-known/agent.json", self._get_agent_card, methods=["GET"])

    def start(self):
        if self.agent_card is None:
            raise ValueError("agent_card is not defined")

        if self.task_manager is None:
            raise ValueError("request_handler is not defined")

        import uvicorn

        uvicorn.run(self.app, host=self.host, port=self.port)

    def _get_agent_card(self, request: Request) -> JSONResponse:
        return JSONResponse(self.agent_card.model_dump(exclude_none=True))

    async def _process_request(self, request: Request):
        try:

            body = await request.json()
            json_rpc_request = A2ARequest.validate_python(body)

            if isinstance(json_rpc_request, GetTaskRequest):
                result = self.task_manager.on_get_task(json_rpc_request)
            elif isinstance(json_rpc_request, SendTaskRequest):
                result = self.task_manager.on_send_task(json_rpc_request)
            elif isinstance(json_rpc_request, SendTaskStreamingRequest):
                result = self.task_manager.on_send_task_subscribe(
                    json_rpc_request
                )
            elif isinstance(json_rpc_request, CancelTaskRequest):
                result = self.task_manager.on_cancel_task(json_rpc_request)
            elif isinstance(json_rpc_request, SetTaskPushNotificationRequest):
                result = self.task_manager.on_set_task_push_notification(json_rpc_request)
            elif isinstance(json_rpc_request, GetTaskPushNotificationRequest):
                result = self.task_manager.on_get_task_push_notification(json_rpc_request)
            elif isinstance(json_rpc_request, TaskResubscriptionRequest):
                result = self.task_manager.on_resubscribe_to_task(
                    json_rpc_request)
            else:
                logger.warning(f"Unexpected request type: {type(json_rpc_request)}")
                raise ValueError(f"Unexpected request type: {type(request)}")

            return create_json_response(result)

        except Exception as e:
            return _handle_exception(e)


class DynamicA2AServer:
    def __init__(
            self,
            agent_config_props: AgentConfigProps,
            endpoint="/dynamic_agents",
            agents: typing.Optional[typing.Dict] = None,
            starlette: typing.Optional[Starlette] = None
    ):
        self.host = agent_config_props.host
        self.port = agent_config_props.port
        self.endpoint = endpoint
        self.app = starlette if starlette is not None else Starlette()
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
            return _handle_exception(e)

    def _do_put_agent(self, body, agents):
        from cdc_agents.agent.task_manager import AgentTaskManager
        agent_card = AgentCard(**body['agent_card'])
        agent_code = AgentCode(**body['agent_code'])
        agent_descriptor = AgentDescriptor(**body['agent_descriptor'])

        host = body['host']
        port = body['port']

        py_file = agent_code.py_file

        if not py_file.endswith('.py'):
            py_file = f'{py_file}.py'

        to_write_to = os.path.join(python_util.io_utils.file_dirs.get_dir(__file__, 'agents'), py_file)

        if os.path.exists(to_write_to):
            return _handle_exception(FileExistsError(f"File {py_file} existed - could not save new agent."))

        with open(to_write_to, 'w') as py_file_out:
            py_file_out.write(agent_code.code)

        try:
            tools = [importlib.import_module(t) for t in agent_descriptor.tools]
            model = agent_descriptor.model
            system_promptss = agent_descriptor.system_prompts

            loaded = importlib.import_module(python_util.io_utils.file_dirs.create_py_import(to_write_to, __file__))
            notification_sender_auth = PushNotificationSenderAuth()
            notification_sender_auth.generate_jwk()

            for k, v in loaded.__dict__.items():
                from cdc_agents.agent.a2a import A2AAgent
                if isinstance(v, type) and reflection_utils.is_type_instance_of(A2AAgent, v):
                    agent: A2AAgent = v(model, tools, system_promptss)
                    importlib.import_module(agent_code.code)
                    _add_managed_agents(agent_card, self.agents)
                    agent_value = A2AServer(agent_card=agent_card,
                                            task_manager=AgentTaskManager(agent=agent,
                                                                          notification_sender_auth=notification_sender_auth),
                                            host=host,
                                            port=port)
                    agent_value.start() # TODO:
                    agents[agent.agent_name] = agent_value
                    return create_json_response(PostAgentResponse(result=AgentPosted(success=True, endpoint='/dynamic_agents/put_agent')).model_dump(exclude_none=True))

            if os.path.exists(to_write_to):
                os.remove(to_write_to)

            return _handle_exception(ModuleNotFoundError("Could not create agent."))
        except Exception as e:
            return _handle_exception(e)

