import dataclasses
import time
import typing
import uuid
from typing import Dict, List, Any, Optional, Union, AsyncGenerator

import asyncio
import injector
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from cdc_agents.agent.a2a import A2AAgent
from cdc_agents.agent.agent import A2AReactAgent
from cdc_agents.agent.task_manager import AgentTaskManager
from cdc_agents.common.types import (
    AgentCard, SendTaskStreamingRequest, TaskSendParams, SendTaskStreamingResponse,
    JSONRPCResponse, Message, TextPart, CancelTaskRequest, TaskIdParams, TaskState, TaskStatus,
    Task
)
from cdc_agents.common.utils.push_notification_auth import PushNotificationSenderAuth
from cdc_agents.config.agent_config_props import AgentConfigProps
from cdc_agents.config.runner_props import RunnerConfigProps
from cdc_agents.model_server.model_provider import ModelProvider
from python_di.configs.autowire import injectable
from python_di.configs.component import component
from python_di.inject.profile_composite_injector.composite_injector import profile_scope
from python_util.logger.logger import LoggerFacade


class PushEvent(BaseModel):
    eventName: str
    task_id: str
    data: dict[str, Any]

# Pydantic models for agent inputs/outputs
class AgentQuery(BaseModel):
    query: str
    task_id: typing.Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class CancelTask(BaseModel):
    task_id: str
    metadata: Optional[Dict[str, Any]] = None


class ListTasks(BaseModel):
    status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


@dataclasses.dataclass
class AgentTool:
    """Represents an agent exposed as an MCP tool"""
    name: str
    description: str
    agent: A2AAgent
    agent_card: AgentCard


@component(profile=['main_profile', 'test'], scope=profile_scope)
@injectable()
class CdcMcpAgents:
    """
    MCP server implementation for CDC agents. Exposes all available agents as tools/calls with their
    description and I/O capabilities. Allows for streaming communication between clients and agents.
    """

    @injector.inject
    def __init__(
        self,
        agent_config_props: AgentConfigProps,
        runner_config_props: RunnerConfigProps,
        model_provider: ModelProvider,
        agents: List[A2AAgent] = None
    ):
        self.agent_config_props = agent_config_props
        self.model_provider = model_provider

        self.server: FastMCP = FastMCP("cdc-agents-mcp", stateless_http=True, json_response=True)
        self.agent_tools: List[AgentTool] = []

        # Initialize agent tools
        self.agents = agents or []

        self._initialize_agent_tools()

        self.tasks: dict[str, AgentTaskManager] = {agent.agent_name: typing.cast(AgentTaskManager, agent.task_manager) for agent in self.agents}

        # Register server methods
        self._register_server_methods()

        # Start server if configured to do so
        if runner_config_props.is_mcp():
            self.start_server_sync()

    @staticmethod
    def now():
        return time.time_ns()

    def _initialize_agent_tools(self):
        """Initialize agent tools from the provided agents list"""
        for agent in self.agents:
            agent_name = agent.agent_name

            task_manager = AgentTaskManager(agent, PushNotificationSenderAuth())
            agent.set_task_manager(task_manager)

            if agent_name in self.agent_config_props.agents:
                agent_config = self.agent_config_props.agents.get(agent_name)
                if not agent_config.exposed_externally:
                    continue
                if agent_config and agent_config.agent_card:
                    agent_card = agent_config.agent_card
                    description = agent_card.description or f"Agent tool for {agent_name}"

                    self.agent_tools.append(
                        AgentTool(
                            name=agent_name,
                            description=description,
                            agent=agent,
                            agent_card=agent_card))
                LoggerFacade.debug(f"Added agent tool: {agent_name}")
            else:
                LoggerFacade.warn(f"Agent {agent_name} not found in configuration, skipping")

    def _register_server_methods(self):
        """Register all the server method decorators"""

        # Register each agent tool individually
        for tool in self.agent_tools:
            self.server.add_tool(
                fn=self._create_agent_tool_handler(tool),
                name=tool.name,
                description=tool.description
            )

        # Add management tools
        self.server.add_tool(
            fn=self._create_get_task_status_handler(),
            name="get_task_status",
            description="Get the status of a running or completed task"
        )

        self.server.add_tool(
            fn=self._create_cancel_task_handler(),
            name="cancel_task",
            description="Cancel a running task"
        )

        self.server.add_tool(
            fn=self._create_list_tasks_handler(),
            name="list_tasks",
            description="List all tasks with optional status filtering"
        )

    def _create_get_task_status_handler(self):
        async def handler(arguments: TaskIdParams) -> Dict[str, Any]:
            result = await self._handle_get_task_status(arguments)
            return result
        return handler

    def _create_cancel_task_handler(self):
        async def handler(arguments: CancelTask) -> Task:
            result = await self._handle_cancel_task(arguments)
            return result
        return handler

    def _create_list_tasks_handler(self):
        async def handler(arguments: ListTasks) -> List[Dict[str, Any]]:
            result = await self._handle_list_tasks(arguments)
            return result
        return handler

    def _create_agent_tool_handler(self, agent_tool: AgentTool):
        async def handler(arguments: AgentQuery) -> typing.List[PushEvent]:
            # Generate task ID and prepare for execution
            LoggerFacade.debug(f"Received tool call {arguments}")
            task_id = str(uuid.uuid4()) if not arguments.task_id else arguments.task_id

            query = arguments.query

            events = []

            if not query:
                error_event = PushEvent(
                    task_id=task_id,
                    eventName="agent_error",
                    data={
                        "content": "Query parameter is required",
                        "is_final": True,
                        "agent": agent_tool.name,
                        "task_id": task_id,
                        "timestamp": self.now()
                    }
                )
                events.append(error_event)
                return events

            # Use TaskManager to create task
            manager: AgentTaskManager = self.tasks.get(agent_tool.agent.agent_name)

            if not manager:
                events.append(await _cancelled_event(agent_tool))
                return events

            res = await self._call_agent_tool_get_responses(agent_tool.agent, query, task_id)

            if isinstance(res, JSONRPCResponse):
                events.append(await parse_agent_json_resp(res, task_id))
                return events

            try:
                # Initial response
                initial_response = PushEvent(
                    task_id=task_id,
                    eventName="agent_response",
                    data={
                        "content": f"Starting {agent_tool.name} agent with query: {query}",
                        "is_final": False,
                        "agent": agent_tool.name,
                        "task_id": task_id,
                        "timestamp": self.now()
                    }
                )

                # For FastMCP, we need to yield responses directly as streaming
                events.append(initial_response)

                async for chunk in res:
                    if not chunk:
                        continue

                    chunk: SendTaskStreamingResponse = chunk

                    # Check if task was cancelled
                    try:
                        task = manager.task(task_id)
                        if task and task.status and task.status.state == TaskState.CANCELED:
                            cancel_event = await _cancelled_event(task_id)
                            events.append(cancel_event)
                            break
                    except Exception as e:
                        LoggerFacade.error(f"Error checking task status: {str(e)}")

                    parts = chunk.result.status.message.parts

                    for p in parts:
                        events.append(await parse_agent_part(p, task_id))

                return events

            except asyncio.CancelledError:
                cancel_event = await _cancelled_event(task_id)
                events.append(cancel_event)
                return events

            except Exception as e:
                error_event = await _error_event(e, task_id)
                events.append(error_event)
                return events

        async def parse_agent_json_resp(res, task_id):
            response_event = PushEvent(
                task_id=task_id,
                eventName="agent_response",
                data={
                    "content": res.result,
                    "is_final": False,
                    "agent": agent_tool.name,
                    "task_id": task_id,
                    "timestamp": self.now()
                }
            )
            return response_event

        async def _error_event(e, task_id):
            error_event = PushEvent(
                task_id=task_id,
                eventName="agent_error",
                data={
                    "content": f"Error: {str(e)}",
                    "is_final": True,
                    "agent": agent_tool.name,
                    "task_id": task_id,
                    "timestamp": self.now()
                }
            )
            return error_event

        async def parse_agent_part(p, task_id):
            if not isinstance(p, TextPart):
                error_event = PushEvent(
                    task_id=task_id,
                    eventName="agent_error",
                    data={
                        "content": f"Could not push part of type: {p.type}",
                        "is_final": False,
                        "agent": agent_tool.name,
                        "task_id": task_id,
                        "timestamp": self.now()
                    }
                )
                return error_event
            else:
                text_event = PushEvent(
                    task_id=task_id,
                    eventName="agent_response",
                    data={
                        "content": p.text,
                        "is_final": False,
                        "agent": agent_tool.name,
                        "task_id": task_id,
                        "timestamp": self.now()
                    }
                )
                return text_event

        async def _cancelled_event(task_id):
            cancel_event = PushEvent(
                task_id=task_id,
                eventName="agent_cancelled",
                data={
                    "content": "Task was cancelled",
                    "is_final": True,
                    "agent": agent_tool.name,
                    "task_id": task_id,
                    "timestamp": self.now()
                }
            )
            return cancel_event

        return handler

    async def _do_handle_call_tool_exception(self, agent_tool, e, manager, server_push, task_id):
        # Handle errors
        error_msg = f"Error executing agent {agent_tool.name}: {str(e)}"
        LoggerFacade.error(error_msg)
        if manager:
            task_status = TaskStatus(state=TaskState.FAILED,
                                     message=Message(role="agent", parts=[{"type": "text", "text": str(e)}]))
            manager.update_store(task_id, task_status)
        self._push_task_error(agent_tool, error_msg, server_push, task_id)
        return server_push

    async def _do_handle_call_tool_cancelled(self, agent_tool, manager, server_push, task_id):
        # Task was cancelled
        if manager:
            task_status = TaskStatus(state=TaskState.CANCELED)
            manager.update_store(task_id, task_status)
        self._push_cancelled_task(agent_tool, server_push, task_id)
        return server_push

    def _push_response(self, agent_tool: AgentTool, text: str, server_response: List, task_id: str) -> List[Dict[str, Any]]:
        response = PushEvent(
            task_id=task_id,
            eventName="agent_response",
            data={
                "content": text,
                "is_final": False,
                "agent": agent_tool.name,
                "task_id": task_id,
                "timestamp": self.now()
            }
        )
        serialized = response.model_dump()
        server_response.append(serialized)
        return server_response

    def _push_task_error(self, agent_tool: AgentTool, error_msg: str, server_push: List, task_id: str) -> List[Dict[str, Any]]:
        response = PushEvent(
            task_id=task_id,
            eventName="agent_error",
            data={
                "content": error_msg,
                "is_final": True,
                "agent": agent_tool.name,
                "task_id": task_id,
                "timestamp": self.now()
            }
        )
        serialized = response.model_dump()
        server_push.append(serialized)
        return server_push

    def _push_cancelled_task(self, agent_tool: AgentTool, server_push: List, task_id: str) -> List[Dict[str, Any]]:
        response = PushEvent(
            task_id=task_id,
            eventName="agent_cancelled",
            data={
                "content": "Task was cancelled",
                "is_final": True,
                "agent": agent_tool.name,
                "task_id": task_id,
                "timestamp": self.now()
            }
        )
        serialized = response.model_dump()
        server_push.append(serialized)
        return server_push

    async def _call_agent_tool_get_responses(self, agent: A2AAgent, query: str, task_id: str) -> Union[AsyncGenerator[SendTaskStreamingResponse, None], JSONRPCResponse]:
        """
        Process agent response as an async iterable to enable streaming

        Args:
            agent: The agent to process the query
            query: The user query
            task_id: Unique identifier for this task

        Yields:
            Chunks of the response as they become available
        """
        try:
            tasks: AgentTaskManager = self.tasks.get(agent.agent_name)
            if not tasks:
                return JSONRPCResponse(result=f"No task manager found for agent {agent.agent_name}")

            # Create task in the task manager
            message = Message(role="user", parts=[TextPart(type="text", text=query)])
            task_send_params = TaskSendParams(
                id=task_id,
                sessionId=task_id,  # Use task_id as session_id for simplicity
                message=message,
                acceptedOutputModes=["text"])

            response = tasks.on_send_task_subscribe(SendTaskStreamingRequest(params=task_send_params))

            # If it's a JSONRPCResponse, return it directly
            if isinstance(response, JSONRPCResponse):
                return response

            # If it's already an async generator, return it
            if hasattr(response, '__aiter__'):
                return response

            # If it's a regular generator, convert it to an async generator
            async def async_generator():
                for item in response:
                    yield item
                    await asyncio.sleep(0)  # Allow other tasks to run

            return async_generator()
        except Exception as e:
            LoggerFacade.error(f"Error in _call_agent_tool_get_responses: {str(e)}")
            return JSONRPCResponse(result=f"Error processing request: {str(e)}")


    async def _handle_get_task_status(self, arguments: TaskIdParams) -> Dict[str, Any]:
        """Handle get task status requests"""
        task_id = arguments.get("task_id")
        if not task_id:
            return {"error": "Task ID is required"}

        task_found = False
        status_info = {"task_id": task_id}

        # Try to get task from each agent's task manager
        for agent_name, task_manager in self.tasks.items():
            task = task_manager.task(task_id)
            if task:
                task_found = True
                status_info.update({
                    "status": task.status.state,
                    "message": task.status.message.model_dump() if task.status.message else None,
                    "agent": agent_name
                })
                break

        if task_found:
            return status_info
        else:
            LoggerFacade.warn(f"Task status requested for unknown task ID: {task_id}")
            return {"error": f"Task {task_id} not found", "status": "unknown", "task_id": task_id}

    async def _handle_cancel_task(self, arguments: CancelTask) -> Dict[str, Any]:
        """Handle task cancellation requests"""
        task_id = arguments.task_id
        if not task_id:
            return {"error": "Task ID is required", "success": False}

        task_found = False
        can_cancel = False
        task_manager = None
        agent_name = None

        # Find the task manager that contains this task
        for an, tm in self.tasks.items():
            task = tm.task(task_id)
            if task:
                task_found = True
                task_manager = tm
                agent_name = an
                can_cancel = task.status.state == TaskState.WORKING
                break

        # Update task status in task manager
        if task_found and can_cancel:
            task_status = TaskStatus(state=TaskState.CANCELED)
            task_manager.update_store(task_id, task_status)

            # Create a cancel task request
            cancel_request = CancelTaskRequest(id=task_id, params=TaskIdParams(id=task_id))
            task_manager.on_cancel_task(cancel_request)
            LoggerFacade.info(f"Successfully cancelled task {task_id} from agent {agent_name}")

        if not task_found:
            LoggerFacade.warn(f"Cancel requested for unknown task ID: {task_id}")
            return {"success": False, "message": f"Task {task_id} not found", "task_id": task_id}

        if not can_cancel:
            return {"success": False, "message": f"Task {task_id} is not in a state that can be cancelled"}

        return {"success": True, "message": f"Task {task_id} cancelled successfully"}

    async def _handle_list_tasks(self, arguments: ListTasks) -> Dict[str, Any]:
        """Handle listing tasks"""
        status_filter = arguments.get("status", "all")

        tasks = []
        task_ids = set()

        # Get tasks from all agent task managers
        for agent_name, task_manager in self.tasks.items():
            # To get all tasks, we need to check all task manager's internal tasks dictionary
            if hasattr(task_manager, 'tasks'):
                for task_id, task in task_manager.tasks.items():
                    if status_filter == "all" or task.status.state == status_filter:
                        tasks.append({
                            "task_id": task_id,
                            "agent": agent_name,
                            "status": task.status.state,
                            "start_time": task.status.created_at if hasattr(task.status, 'created_at') else None
                        })
                        task_ids.add(task_id)

        return {"tasks": tasks}

    def start_server_sync(self):
        """Start the server synchronously (for non-async contexts)"""
        self.server.run(transport='stdio')