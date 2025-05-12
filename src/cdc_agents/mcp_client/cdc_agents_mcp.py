import json
import typing

import asyncio
import dataclasses
import logging
import importlib
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, AsyncIterable, Sequence

from pydantic import BaseModel

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    Tool,
    ClientCapabilities,
)

import injector
from cdc_agents.agent.a2a import A2AAgent
from cdc_agents.common.types import AgentCard, SendTaskStreamingRequest, TaskSendParams, SendTaskStreamingResponse, \
    JSONRPCError, JSONRPCResponse, Message, TextPart
from cdc_agents.config.agent_config_props import AgentConfigProps
from cdc_agents.agent.task_manager import AgentTaskManager
from cdc_agents.model_server.model_provider import ModelProvider
from python_di.configs.autowire import injectable
from python_di.configs.component import component
from python_di.inject.profile_composite_injector.composite_injector import profile_scope
from python_util.logger.logger import LoggerFacade

class PushEvent(BaseModel):
    eventName: str
    data: dict[str, Any]

# Pydantic models for agent inputs/outputs
class AgentQuery(BaseModel):
    query: str
    context: Optional[Dict[str, Any]] = None


class TaskStatus(BaseModel):
    task_id: str


class CancelTask(BaseModel):
    task_id: str


class ListTasks(BaseModel):
    status: Optional[str] = "all"


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
        model_provider: ModelProvider,
        memory_saver = None,
        agents: List[A2AAgent] = None
    ):
        self.agent_config_props = agent_config_props
        self.model_provider = model_provider
        self.memory_saver = memory_saver

        self.server = Server("cdc-agents-mcp")
        self.agent_tools: List[AgentTool] = []

        # Initialize agent tools
        if agents:
            self._initialize_agent_tools(agents)
        else:
            self._discover_agents()

        self.tasks = {agent.agent_name: agent.task_manager for agent in agents}

        # Register server methods
        self._register_server_methods()

        # Start server if configured to do so
        if agent_config_props.initialize_server:
            self.start_server()

    def _initialize_agent_tools(self, agents: List[A2AAgent]):
        """Initialize agent tools from the provided agents list"""
        for agent in agents:
            agent_name = agent.agent_name

            task_manager = AgentTaskManager(agent, PushNotificationSenderAuth())
            agent.set_task_manager(task_manager)
            self.tasks[agent_name] = task_manager

            if agent_name in self.agent_config_props.agents:
                agent_config = self.agent_config_props.agents[agent_name]
                agent_card = agent_config.agent_card

                # Get the most meaningful description
                description = agent_card.description
                if hasattr(agent, "orchestrator_prompt") and agent.orchestrator_prompt:
                    description = agent.orchestrator_prompt

                # Create the tool
                self.agent_tools.append(
                    AgentTool(
                        name=agent_name,
                        description=description,
                        agent=agent,
                        agent_card=agent_card)
                )
                LoggerFacade.info(f"Added agent tool: {agent_name}")
            else:
                LoggerFacade.warn(f"Agent {agent_name} not found in configuration, skipping")

    def _discover_agents(self):
        """Discover available agents from the configuration"""
        LoggerFacade.info("Discovering available agents from configuration")

        for agent_name, agent_config in self.agent_config_props.agents.items():
            try:
                # Try to create the agent from the configuration
                agent_card = agent_config.agent_card

                if hasattr(agent_config, 'agent_clazz') and agent_config.agent_clazz:
                    # Import the agent class
                    module_path, class_name = agent_config.agent_clazz.rsplit('.', 1)
                    module = importlib.import_module(module_path)
                    agent_class = getattr(module, class_name)

                    # Initialize the agent
                    model = self.model_provider.retrieve_model(agent_config)

                    # Get the appropriate constructor parameters
                    import inspect
                    sig = inspect.signature(agent_class.__init__)
                    params = {}

                    # Match parameters based on signature
                    if 'agent_config' in sig.parameters:
                        params['agent_config'] = agent_config
                    if 'model' in sig.parameters:
                        params['model'] = model
                    if 'memory_saver' in sig.parameters and self.memory_saver:
                        params['memory_saver'] = self.memory_saver
                    if 'model_provider' in sig.parameters:
                        params['model_provider'] = self.model_provider

                    # Create agent instance
                    agent = agent_class(**params)

                    # Add to tools
                    description = agent_card.description
                    if hasattr(agent, "orchestrator_prompt") and agent.orchestrator_prompt:
                        description = agent.orchestrator_prompt

                    self.agent_tools.append(
                        AgentTool(
                            name=agent_name,
                            description=description,
                            agent=agent,
                            agent_card=agent_card
                        )
                    )
                    LoggerFacade.info(f"Discovered and added agent tool: {agent_name}")
                else:
                    LoggerFacade.warning(f"Agent {agent_name} has no agent_clazz defined, skipping")
            except Exception as e:
                LoggerFacade.error(f"Failed to create agent {agent_name}: {str(e)}")

    def _register_server_methods(self):
        """Register all the server method decorators"""

        @self.server.list_tools()
        async def list_tools() -> List[Tool]:
            tools = []

            # Add tools for each agent
            for tool in self.agent_tools:
                tools.append(
                    Tool(
                        name=tool.name,
                        description=tool.description,
                        inputSchema=AgentQuery.schema()
                    )
                )

            # Add management tools
            tools.extend([
                Tool(
                    name="get_task_status",
                    description="Get the status of a running or completed task",
                    inputSchema=TaskStatus.schema()
                ),
                Tool(
                    name="cancel_task",
                    description="Cancel a running task",
                    inputSchema=CancelTask.schema()
                ),
                Tool(
                    name="list_tasks",
                    description="List all tasks with optional status filtering",
                    inputSchema=ListTasks.schema()
                )
            ])

            return tools

        @self.server.call_tool()
        async def call_tool(name: str, arguments: dict) -> List[TextContent]:
            # Check if this is a management tool
            if name == "get_task_status":
                result = await self._handle_get_task_status(arguments)
                return [TextContent(type="text", text=json.dumps(result))]

            elif name == "cancel_task":
                result = await self._handle_cancel_task(arguments)
                return [TextContent(type="text", text=json.dumps(result))]

            elif name == "list_tasks":
                result = await self._handle_list_tasks(arguments)
                return [TextContent(type="text", text=json.dumps(result))]

            # Otherwise, it's an agent tool - find the agent
            agent_tool = next((t for t in self.agent_tools if t.name == name), None)
            if not agent_tool:
                return [TextContent(
                    type="text",
                    text=f"Error: Unknown tool '{name}'"
                )]

            # Generate task ID and prepare for execution
            task_id = str(uuid.uuid4())
            query = arguments.get("query", "")
            context = arguments.get("context", {})

            if not query:
                return [TextContent(
                    type="text",
                    text="Error: Query parameter is required"
                )]

            # Create task in the task manager
            message = Message(role="user", parts=[{"type": "text", "text": query}])
            task_send_params = TaskSendParams(
                id=task_id,
                sessionId=task_id,  # Use task_id as session_id for simplicity
                message=message,
                acceptedOutputModes=["text"]
            )

            # Use TaskManager to create task
            manager: AgentTaskManager = self.tasks.get(agent_tool.name)

            res = self._call_agent_tool_get_responses(agent_tool.agent, query, task_id)

            if isinstance(res, JSONRPCResponse):
                return [TextContent(type="test", text=PushEvent(eventName="", data={}))]

            server_push = []

            try:
                # Send initial notification
                # TODO: SSE push
                server_push.append(
                    TextContent(
                        type="text",
                        text=json.dumps(PushEvent(
                            eventName="agent_response",
                            data={
                                "content": f"Starting {agent_tool.name} agent with query: {query}",
                                "is_final": False,
                                "agent": agent_tool.name,
                                "task_id": task_id,
                                "timestamp": self.server.now()
                            }
                        )))
                )

                async for chunk in res:
                    # Check if task was cancelled
                    is_cancelled = False
                    if manager:
                        task = manager.task(task_id)
                        is_cancelled = task and task.status.state == TaskState.CANCELLED

                    if is_cancelled:
                        server_push.append(
                            TextContent(
                                type="text",
                                text=PushEvent(
                                eventName="agent_response",
                                data={
                                    "content": "Task was cancelled by user request",
                                    "is_final": True,
                                    "agent": agent_tool.name,
                                    "task_id": task_id,
                                    "timestamp": self.server.now()
                                }
                            ))
                        )
                        break

                    server_push.append(
                        TextContent(
                            type="text",
                            text=PushEvent(
                            eventName="agent_response",
                            data={
                                "content": chunk,
                                "is_final": False,
                                "agent": agent_tool.name,
                                "task_id": task_id,
                                "timestamp": self.server.now()
                            }
                        ))
                    )


                return server_push

            except asyncio.CancelledError:
                # Task was cancelled
                if manager:
                    task_status = TaskStatus(state=TaskState.CANCELLED)
                    manager.update_store(task_id, task_status)

                server_push.append(
                    TextContent(
                        type="text",
                        text=PushEvent(
                        eventName="agent_response",
                        data={
                            "content": "Task was cancelled",
                            "is_final": True,
                            "agent": agent_tool.name,
                            "task_id": task_id,
                            "timestamp": self.server.now()
                        }
                    )
                ))

                return server_push

            except Exception as e:
                # Handle errors
                error_msg = f"Error executing agent {agent_tool.name}: {str(e)}"
                LoggerFacade.error(error_msg)

                if manager:
                    task_status = TaskStatus(state=TaskState.FAILED, message=Message(role="system", parts=[{"type": "text", "text": str(e)}]))
                    manager.update_store(task_id, task_status)

                server_push.append(
                    PushEvent(
                        eventName="agent_response",
                        data={
                            "content": f"Error: {error_msg}",
                            "is_final": True,
                            "agent": agent_tool.name,
                            "task_id": task_id,
                            "timestamp": self.server.now()
                        }
                    )
                )

                return server_push



    async def _call_agent_tool_get_responses(self, agent: A2AAgent, query: str, task_id: str) -> typing.Generator[SendTaskStreamingResponse, None, None] | JSONRPCResponse:
        """
        Process agent response as an async iterable to enable streaming

        Args:
            agent: The agent to process the query
            query: The user query
            task_id: Unique identifier for this task

        Yields:
            Chunks of the response as they become available
        """
        tasks: AgentTaskManager = self.tasks[agent.agent_name]
        return tasks.on_send_task_subscribe(SendTaskStreamingRequest(params=TaskSendParams(
            id=task_id, sessionId=task_id,
            message=Message(role="user", parts=[TextPart(text=query)]))))


    async def _handle_get_task_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
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

    async def _handle_cancel_task(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task cancellation requests"""
        task_id = arguments.get("task_id")
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
            task_status = TaskStatus(state=TaskState.CANCELLED)
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

    async def _handle_list_tasks(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
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

    def _get_agent_capabilities(self, agent: A2AAgent) -> List[str]:
        """Get the capabilities of an agent"""
        capabilities = []
        
        # Check for supported content types
        if hasattr(agent, "SUPPORTED_CONTENT_TYPES"):
            capabilities.extend([f"content_type:{ct}" for ct in agent.SUPPORTED_CONTENT_TYPES])
            
        # Check for specific tool capabilities
        if hasattr(agent, "tools") and agent.tools:
            capabilities.extend([f"tool:{tool.__name__}" for tool in agent.tools if hasattr(tool, "__name__")])
            
        return capabilities

    async def start_server(self):
        """Start the MCP server - Expose agents as tools themselves for easy integration"""
        LoggerFacade.info("Starting MCP server for CDC agents")
        
        options = self.server.create_initialization_options()
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream, options, raise_exceptions=True)

    def start_server_sync(self):
        """Start the server synchronously (for non-async contexts)"""
        asyncio.run(self.start_server())

