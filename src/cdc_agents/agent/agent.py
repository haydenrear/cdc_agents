import abc
import time

import asyncio
import functools
import inspect
from uuid import UUID

from langchain.callbacks.base import BaseCallbackHandler
from langchain_core.agents import AgentAction

from python_di.inject.profile_composite_injector.inject_context_di import autowire_fn, InjectionDescriptor, \
    InjectionType
from cdc_agents.tools.tool_call_decorator import  ToolCallDecorator
import atexit

import nest_asyncio

from cdc_agents.common.server import TaskManager
from python_util.logger.logger import LoggerFacade

from cdc_agents.agent.a2a import A2AAgent
import json
import subprocess
import typing
import uuid
from typing import Any, Dict, AsyncIterable, Optional

from langchain_core.callbacks import Callbacks
from langchain_core.messages import ToolMessage, BaseMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import StructuredTool, BaseTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from cdc_agents.tools.tool_call_decorator import LoggingToolCallback


from cdc_agents.config.secret_config_props import SecretConfigProps
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentMcpTool, AgentCardItem
from cdc_agents.model_server.model_provider import ModelProvider
from cdc_agents.util.nest_async_util import do_run_on_event_loop


class A2ASmolAgent(A2AAgent, abc.ABC):
    def __init__(self, agent_config: AgentConfigProps, tools, system_instruction,
                 memory: MemorySaver, model = None):
        this_agent_name = self.__class__.__name__
        model = agent_config.agents[this_agent_name].agent_descriptor.model \
            if this_agent_name in agent_config.agents.keys() else None \
            if model is None else model
        A2AAgent.__init__(self, model, tools, system_instruction, memory)

class A2AReactAgent(A2AAgent, abc.ABC):

    def __init__(self, agent_config: AgentConfigProps, tools, system_instruction,
                 memory: MemorySaver,
                 model_server_provider: ModelProvider, model = None):
        self.model_server_provider = model_server_provider
        this_agent_name = self.__class__.__name__
        self.agent_config: AgentCardItem = agent_config.agents.get(this_agent_name)
        inputs = self.agent_config.agent_card.defaultInputModes
        self.model = self.model_server_provider.retrieve_model(
            agent_config.agents[this_agent_name] if this_agent_name in agent_config.agents.keys() else None, model)

        A2AAgent.__init__(self, self.model, tools, system_instruction, memory, inputs)

        self.add_mcp_tools(additional_tools=self.agent_config.mcp_tools)

        self._set_tools_return_direct()

        self._create_react_agent()

        # if self.graph.config is None:
        #     self.graph.config = {}
        #
        # cb = self.graph.config.get('callbacks')
        #
        # if cb is None:
        #     self.graph.config['callbacks'] = [LoggingToolCallback(self)]
        # else:
        #     cb.append(LoggingToolCallback(self))

    def _create_graph(self, mcp_tools):
        self.add_mcp_tools(additional_tools=mcp_tools)
        self._set_tools_return_direct()
        self._create_react_agent()

    def _create_react_agent(self):
        self.graph = create_react_agent(
            self.model, tools=self.tools, checkpointer=self.memory,
            prompt=self.system_instruction)

    def _set_tools_return_direct(self):
        for t in self.tools:
            t: BaseTool = t
            if not t.callbacks:
                t.callbacks = []
            t.return_direct = True

    @autowire_fn({
        'additional_tools': InjectionDescriptor(injection_ty=InjectionType.Provided),
        'loop': InjectionDescriptor(injection_ty=InjectionType.Provided),
        'secrets': InjectionDescriptor(injection_ty=InjectionType.Dependency)
    })
    def add_mcp_tools(self, additional_tools: typing.Dict[str, AgentMcpTool], secrets: SecretConfigProps, loop=None):
        done = do_run_on_event_loop(self.add_mcp_tools_async(secrets, additional_tools, loop), lambda s: None, loop)

    async def add_mcp_tools_async(self, secrets: SecretConfigProps, additional_tools: typing.Dict[str, AgentMcpTool] = None, loop=None):
        if additional_tools is not None:
            for k,v in additional_tools.items():
                if v and v.tool_options:
                    self._replace_tool_secrets(k, secrets, v.tool_options)
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
                        stop_tool = v.stop_tool
                        self.do_run_stop(stop_tool)
                        atexit.register(lambda stop_tool_=stop_tool: self.do_run_stop(stop_tool_))

    def _replace_tool_secrets(self, k, secrets, v):
        for m in secrets.mcp_tool_secrets:
            if m.tool_name == k:
                if isinstance(v, dict):
                    a = v.get('args')
                    if a and isinstance(a, list):
                        a = [
                            t_o.replace('{{' + m.secret_name + '}}', m.secret_value)
                            for t_o in a if isinstance(t_o, str)
                        ]
                        v['args'] = a

    def do_run_stop(self, stop_tool_):
        try:
            subprocess.run(stop_tool_, shell=True)
        except Exception as e:
            pass

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
                            try:
                                out = await tool.arun(tool_input, verbose, start_color, color, callbacks, tags=tags,
                                                       metadata=metadata,run_name=run_name, run_id=run_id,config=config,
                                                       tool_call_id=tool_call_id, **kwargs)
                                return out
                            except Exception as e:
                                failure = ToolMessage(
                                    content=f"Failed to run tool with err {e}. Could not find matching tools for {self.name} - are all the services running?",
                                    name=self.name,
                                    tool_call_id=tool_call_id if tool_call_id is not None else tool_input.get("id") if isinstance(tool_input, dict) else str(uuid.uuid4()),
                                    status="error")
                                return failure

                    failure = ToolMessage(
                        content=f"Failed to run tool. Could not find matching tools for {self.name}",
                        name=self.name,
                        tool_call_id=tool_call_id if tool_call_id is not None else tool_input.get("id") if isinstance(tool_input, dict) else str(uuid.uuid4()),
                        status="error")
                    return failure

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

                ran = do_run_on_event_loop(self.arun(tool_input, verbose, start_color,
                                                     color, callbacks, tags=tags, metadata=metadata,
                                                     run_name=run_name, run_id=run_id,
                                                     config=config, tool_call_id=tool_call_id, **kwargs),
                                           lambda err: ToolMessage(
                                               content=f"Failed to run tool. MCP tools cannot run inside already running event loop. "
                                                       f"Must have called sync inside async, and cannot then call async. Err: {err}",
                                               name=self.name,
                                               tool_call_id=tool_input.get("id") if isinstance(tool_input, dict) else None,
                                               status="error"),
                                           to_run_loop)

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
        config = self._parse_query_config(sessionId)
        invoked = self.graph.invoke(TaskManager.get_user_query_message(query, sessionId), config)
        next_message = self.pop_to_process_task(sessionId)
        while next_message is not None:
            query = self.task_manager.get_user_query_message(next_message, sessionId)
            config['configurable']['checkpoint_time'] = time.time_ns()
            invoked = self.graph.invoke(query, config)
            next_message = self.pop_to_process_task(sessionId)
        return self.get_agent_response(config)

    def stream(self, query, session_id, graph=None):
        yield from self.stream_agent_response_graph(query, session_id, self.graph)

    def get_agent_response(self, config, graph=None):
        return self.get_agent_response_graph(config, self.graph)


    def _parse_query_config(self, sessionId):
        if not isinstance(sessionId, dict):
            return sessionId
        else:
            config = {"configurable": {"thread_id": sessionId, 'checkpoint_time': time.time_ns()}}

        return config

