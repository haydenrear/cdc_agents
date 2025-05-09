import abc
import asyncio
import atexit

from cdc_agents.agent.a2a import A2AAgent
import json
import subprocess
import typing
import uuid
from typing import Any, Dict, AsyncIterable

from langchain_core.callbacks import Callbacks
from langchain_core.messages import ToolMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from cdc_agents.config.agent_config_props import AgentConfigProps, AgentMcpTool, AgentCardItem
from cdc_agents.model_server.model_provider import ModelProvider


class A2ASmolAgent(A2AAgent, abc.ABC):
    def __init__(self, agent_config: AgentConfigProps, tools, system_instruction,
                 memory: MemorySaver, model = None):
        this_agent_name = self.__class__.__name__
        model = agent_config.agents[this_agent_name].agent_descriptor.model \
            if this_agent_name in agent_config.agents.keys() else None \
            if model is None else model
        A2AAgent.__init__(self, model, tools, system_instruction, memory)
#       TODO: create different types of SmolAgent, and then stream result as in above - can be streamed to langgraph
#           graph the same, but can have python code calling instead of tool calling, and can have multi-agent.


class A2AReactAgent(A2AAgent, abc.ABC):

    def __init__(self, agent_config: AgentConfigProps, tools, system_instruction,
                 memory: MemorySaver, model_server_provider: ModelProvider, model = None):
        self.model_server_provider = model_server_provider
        this_agent_name = self.__class__.__name__
        self.model = self.model_server_provider.retrieve_model(
            agent_config.agents[this_agent_name] if this_agent_name in agent_config.agents.keys() else None, model)
        A2AAgent.__init__(self, self.model, tools, system_instruction, memory)
        self.graph = create_react_agent(
            self.model, tools=self.tools, checkpointer=self.memory,
            prompt = self.system_instruction)
        self.agent_config: AgentCardItem = agent_config.agents[this_agent_name] \
            if this_agent_name in agent_config.agents.keys() else None

    def add_mcp_tools(self, additional_tools: typing.Dict[str, AgentMcpTool] = None, loop=None):
        if loop:
            loop.run_until_complete(self.add_mcp_tools_async(additional_tools, loop))
        else:
            asyncio.get_event_loop().run_until_complete(self.add_mcp_tools_async(additional_tools, loop))

    async def add_mcp_tools_async(self, additional_tools: typing.Dict[str, AgentMcpTool] = None, loop=None):
        if additional_tools is not None:
            for k,v in additional_tools.items():
                async with MultiServerMCPClient({k: v.tool_options}) as client:
                    tools = client.get_tools()
                    for t in tools:
                        tool_name = k
                        agent_tool = additional_tools[tool_name]
                        t.description = f"""
                            {t.description}
                            {self._get_tool_prompt(agent_tool)}
                        """

                        self.tools.append(await self._next_tool(loop, t, k, v))

                    if v.stop_tool:
                        subprocess.run(v.stop_tool, shell=True)
                        atexit.register(lambda: subprocess.run(v.stop_tool, shell=True))

            self.graph = create_react_agent(
                self.model, tools=self.tools, checkpointer=self.memory,
                prompt = self.system_instruction)

    async def _next_tool(self, loop, t, k, v):
        class SynchronousMcpAdapter(StructuredTool):
            def __init__(self, other, to_run_loop):
                StructuredTool.__init__(self, **other.__dict__)
                self.__loop__ = to_run_loop

            async def arun(
                    self,
                    tool_input: typing.Union[str, dict],
                    verbose: typing.Optional[bool] = None,
                    start_color: typing.Optional[str] = "green",
                    color: typing.Optional[str] = "green",
                    callbacks: Callbacks = None,
                    *,
                    tags: typing.Optional[list[str]] = None,
                    metadata: typing.Optional[dict[str, Any]] = None,
                    run_name: typing.Optional[str] = None,
                    run_id: typing.Optional[uuid.UUID] = None,
                    config: typing.Optional[RunnableConfig] = None,
                    tool_call_id: typing.Optional[str] = None,
                    **kwargs: Any,
            ):
                async with MultiServerMCPClient({k: v.tool_options}) as c:
                    for tool in c.get_tools():
                        if self.name == tool.name:
                            return await tool.arun(tool_input, verbose, start_color, color, callbacks, tags=tags,
                                                   metadata=metadata,run_name=run_name, run_id=run_id,config=config,
                                                   tool_call_id=tool_call_id, **kwargs)

                    return ToolMessage(
                        content=f"Failed to run tool. Could not find matching tools for {self.name}",
                        name=self.name,
                        tool_call_id=tool_input.get("id") if isinstance(tool_input, dict) else None,
                        status="error")

            def run(
                    self,
                    tool_input: typing.Union[str, dict],
                    verbose: typing.Optional[bool] = None,
                    start_color: typing.Optional[str] = "green",
                    color: typing.Optional[str] = "green",
                    callbacks: Callbacks = None,
                    *,
                    tags: typing.Optional[list[str]] = None,
                    metadata: typing.Optional[dict[str, Any]] = None,
                    run_name: typing.Optional[str] = None,
                    run_id: typing.Optional[uuid.UUID] = None,
                    config: typing.Optional[RunnableConfig] = None,
                    tool_call_id: typing.Optional[str] = None,
                    **kwargs: Any,
            ):
                to_run_loop = self.__loop__
                close_loop = False

                try:
                    asyncio.get_running_loop()
                    return ToolMessage(
                        content="Failed to run tool. MCP tools cannot run inside already running event loop. "
                                "Must have called sync inside async, and cannot then call async.",
                        name=self.name,
                        tool_call_id=tool_input.get("id") if isinstance(tool_input, dict) else None,
                        status="error")
                except RuntimeError as r:
                    pass

                if to_run_loop is None:
                    try:
                        to_run_loop = asyncio.get_event_loop()
                    except:
                        try:
                            to_run_loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(to_run_loop)
                            close_loop = True
                        except:
                            pass

                ran = to_run_loop.run_until_complete(self.arun(tool_input, verbose, start_color,
                                                               color, callbacks, tags=tags, metadata=metadata,
                                                               run_name=run_name, run_id=run_id,
                                                               config=config, tool_call_id=tool_call_id, **kwargs))

                if close_loop:
                    to_run_loop.close()
                    asyncio.set_event_loop(None)

                if isinstance(ran, str):
                    ran = json.loads(ran)

                if v.stop_tool:
                    subprocess.run(v.stop_tool, shell=True)

                if isinstance(ran, ToolMessage):
                    return ran

                return ToolMessage(
                    content=ran,
                    name=self.name,
                    tool_call_id=tool_call_id if tool_call_id else tool_input.get("id")
                    if isinstance(tool_input, dict) else None,
                    status="success" if isinstance(ran, dict) else "error")

        s = SynchronousMcpAdapter(t, loop)
        return s

    def _get_tool_prompt(self, agent_tool):
        if agent_tool.tool_prompt is not None and len(agent_tool.tool_prompt) != 0:
            return f"""
            Please note the following when using this tool:
            {agent_tool.tool_prompt} 
            """
        return ""

    def invoke(self, query, sessionId):
        config = {"configurable": {"thread_id": sessionId}}
        invoked = self.graph.invoke(query, config)
        next_message = self.pop_to_process_task(sessionId)
        while next_message is not None:
            query = self.task_manager.get_user_query_message(next_message)
            invoked = self.graph.invoke(query, config)
            next_message = self.pop_to_process_task(sessionId)
        #         TODO: self.get_agent_response_graph(invoked)
        return self.get_agent_response(config)

    async def stream(self, query, session_id, graph=None) -> AsyncIterable[Dict[str, Any]]:
        return self.stream_agent_response_graph(query, session_id, self.graph)

    def get_agent_response(self, config, graph=None):
        return self.get_agent_response_graph(config, self.graph)


