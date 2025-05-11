import json

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
from cdc_agents.common.types import AgentCard
from cdc_agents.config.agent_config_props import AgentConfigProps
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
        self.logger = logging.getLogger(__name__)
        
        self.server = Server("cdc-agents-mcp")
        self.agent_tools: List[AgentTool] = []
        self.active_tasks: Dict[str, Dict[str, Any]] = {}
        
        # Initialize agent tools
        if agents:
            self._initialize_agent_tools(agents)
        else:
            self._discover_agents()

        # Register server methods
        self._register_server_methods()
        
        # Start server if configured to do so
        if agent_config_props.initialize_server:
            self.start_server()

    def _initialize_agent_tools(self, agents: List[A2AAgent]):
        """Initialize agent tools from the provided agents list"""
        for agent in agents:
            agent_name = agent.agent_name
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
                        agent_card=agent_card
                    )
                )
                self.logger.info(f"Added agent tool: {agent_name}")
            else:
                self.logger.warning(f"Agent {agent_name} not found in configuration, skipping")

    def _discover_agents(self):
        """Discover available agents from the configuration"""
        self.logger.info("Discovering available agents from configuration")
        
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
                    self.logger.info(f"Discovered and added agent tool: {agent_name}")
                else:
                    self.logger.warning(f"Agent {agent_name} has no agent_clazz defined, skipping")
            except Exception as e:
                self.logger.error(f"Failed to create agent {agent_name}: {str(e)}")

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
            
            # Start task and track it
            self.active_tasks[task_id] = {
                "agent": agent_tool.name,
                "query": query,
                "status": "running",
                "start_time": self.server.now(),
                "cancelled": False,
                "context": context
            }
            
            # Create result handler
            try:
                # Send initial notification
                server_push = []
                # TODO: SSE push
                server_push(
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

                # Process the query with streaming
                async for chunk in self._process_agent_response(agent_tool.agent, query, task_id):
                    # Check if task was cancelled
                    if task_id in self.active_tasks and self.active_tasks[task_id].get("cancelled", False):
                        server_push(
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

                        return [TextContent(
                            type="text",
                            content="Task was cancelled by user request")]

                    # Push chunk
                    server_push(
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


                # Update task status
                if task_id in self.active_tasks:
                    self.active_tasks[task_id]["status"] = "completed"
                    self.active_tasks[task_id]["end_time"] = self.server.now()

                # Send final notification
                server_push(
                    TextContent(
                        type="text",
                        text=PushEvent(
                        eventName="agent_response",
                        data={
                            "content": "Task completed successfully",
                            "is_final": True,
                            "agent": agent_tool.name,
                            "task_id": task_id,
                            "timestamp": self.server.now()
                        }
                    ))
                )

                return server_push

            except asyncio.CancelledError:
                # Task was cancelled
                if task_id in self.active_tasks:
                    self.active_tasks[task_id]["status"] = "cancelled"
                    self.active_tasks[task_id]["end_time"] = self.server.now()

                server_push(
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
                self.logger.error(error_msg)

                if task_id in self.active_tasks:
                    self.active_tasks[task_id]["status"] = "failed"
                    self.active_tasks[task_id]["error"] = str(e)
                    self.active_tasks[task_id]["end_time"] = self.server.now()

                await self.server.push(
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

                return error_msg
            
            # Start processing in background
            asyncio.create_task(process_agent())
            
            # Return initial response
            return [TextContent(
                type="text",
                text=f"Task {task_id} started with agent {agent_tool.name}. Watch for streaming updates."
            )]

    async def _process_agent_response(self, agent: A2AAgent, query: str, task_id: str) -> AsyncIterable[str]:
        """
        Process agent response as an async iterable to enable streaming
        
        Args:
            agent: The agent to process the query
            query: The user query
            task_id: Unique identifier for this task
            
        Yields:
            Chunks of the response as they become available
        """
        # Create a queue to hold chunks as they arrive
        queue = asyncio.Queue()
        
        # Define callback to enqueue chunks
        def chunk_callback(chunk: str) -> None:
            if chunk:
                try:
                    queue.put_nowait(chunk)
                except Exception as e:
                    self.logger.error(f"Error in chunk callback: {str(e)}")
        
        # Store task reference in active_tasks for possible cancellation
        try:
            proc_task = asyncio.create_task(agent.process(query, callback=chunk_callback))
            if task_id in self.active_tasks:
                self.active_tasks[task_id]["task"] = proc_task
            else:
                self.logger.warning(f"Task {task_id} no longer in active tasks when creating process task")
        except Exception as e:
            self.logger.error(f"Error creating agent process task: {str(e)}")
            yield f"Error starting agent task: {str(e)}"
            return
        
        try:
            # Yield chunks as they become available
            while True:
                # Check if this task has been cancelled
                if task_id in self.active_tasks and self.active_tasks[task_id].get("cancelled", False):
                    if not proc_task.done():
                        self.logger.info(f"Cancelling task {task_id}")
                        proc_task.cancel()
                    yield "Task was cancelled by user request"
                    break
                
                # Check if agent processing task is done
                if proc_task.done():
                    # Process any final result
                    try:
                        final_result = proc_task.result()
                        if final_result and not queue.empty():
                            # Only yield final result if it's different from any chunks already in queue
                            last_item = None
                            temp_queue = asyncio.Queue()
                            
                            # Check all items in queue
                            while not queue.empty():
                                item = await queue.get()
                                last_item = item
                                temp_queue.put_nowait(item)
                            
                            # Restore queue
                            while not temp_queue.empty():
                                queue.put_nowait(await temp_queue.get())
                                
                            if last_item != final_result:
                                queue.put_nowait(final_result)
                    except asyncio.CancelledError:
                        yield "Task was cancelled"
                        break
                    except Exception as e:
                        error_msg = f"Error retrieving final result: {str(e)}"
                        self.logger.error(error_msg)
                        queue.put_nowait(error_msg)
                    
                    # Yield any remaining chunks
                    while not queue.empty():
                        yield await queue.get()
                    break
                
                # Try to get a chunk with timeout
                try:
                    chunk = await asyncio.wait_for(queue.get(), timeout=0.1)
                    yield chunk
                except asyncio.TimeoutError:
                    # No chunks available yet, continue checking
                    await asyncio.sleep(0.1)
                    continue
                except asyncio.CancelledError:
                    yield "Task was cancelled"
                    break
                
        except asyncio.CancelledError:
            yield "Task was cancelled"
        except Exception as e:
            error_msg = f"Error in agent execution: {str(e)}"
            self.logger.error(error_msg)
            yield error_msg
            if not proc_task.done():
                proc_task.cancel()

    async def _handle_get_task_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle get task status requests"""
        task_id = arguments.get("task_id")
        if not task_id:
            return {"error": "Task ID is required"}
            
        if task_id in self.active_tasks:
            # Don't return the actual task object
            status_info = {k: v for k, v in self.active_tasks[task_id].items() if k != "task"}
            return status_info
        else:
            self.logger.warning(f"Task status requested for unknown task ID: {task_id}")
            return {"error": f"Task {task_id} not found", "status": "unknown", "task_id": task_id}

    async def _handle_cancel_task(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task cancellation requests"""
        task_id = arguments.get("task_id")
        if not task_id:
            return {"error": "Task ID is required", "success": False}
            
        if task_id not in self.active_tasks:
            self.logger.warning(f"Cancel requested for unknown task ID: {task_id}")
            return {"success": False, "message": f"Task {task_id} not found", "task_id": task_id}
            
        task_info = self.active_tasks[task_id]
        
        if task_info.get("status") != "running":
            return {"success": False, "message": f"Task {task_id} is not running (status: {task_info.get('status')})"}
            
        # Mark as cancelled
        task_info["cancelled"] = True
        task_info["status"] = "cancelled"
        task_info["end_time"] = self.server.now()
        
        # Cancel the task if it exists
        task_obj = task_info.get("task")
        if task_obj and not task_obj.done():
            try:
                task_obj.cancel()
                self.logger.info(f"Successfully cancelled task {task_id}")
            except Exception as e:
                self.logger.error(f"Error cancelling task {task_id}: {str(e)}")
            
        return {"success": True, "message": f"Task {task_id} cancelled successfully"}

    async def _handle_list_tasks(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle listing tasks"""
        status_filter = arguments.get("status", "all")
        
        tasks = []
        for task_id, task_info in self.active_tasks.items():
            if status_filter == "all" or task_info.get("status") == status_filter:
                tasks.append({
                    "task_id": task_id,
                    "agent": task_info.get("agent"),
                    "status": task_info.get("status"),
                    "start_time": task_info.get("start_time"),
                    "query": task_info.get("query")[:50] + "..." if len(task_info.get("query", "")) > 50 else task_info.get("query", "")
                })
        
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
        """Start the MCP server"""
        self.logger.info("Starting MCP server for CDC agents")
        
        options = self.server.create_initialization_options()
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(read_stream, write_stream, options, raise_exceptions=True)

    def start_server_sync(self):
        """Start the server synchronously (for non-async contexts)"""
        asyncio.run(self.start_server())

