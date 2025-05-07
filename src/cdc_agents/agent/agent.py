import abc
import asyncio
import atexit

from cdc_agents.agent.a2a import BaseAgent, A2AAgent
from cdc_agents.common.types import TaskHookMessage, Message
import dataclasses
import json
import subprocess
import typing
import uuid
from typing import Any, Dict, AsyncIterable
from typing import Literal

from langchain_core.callbacks import Callbacks
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.messages import HumanMessage, BaseMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import MessagesState, END
from langgraph.graph import StateGraph
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from pydantic import BaseModel

from cdc_agents.config.agent_config_props import AgentConfigProps, AgentMcpTool, AgentCardItem
from cdc_agents.model_server.model_provider import ModelProvider
from python_util.logger.logger import LoggerFacade


class ResponseFormat(BaseModel):
    """Respond to the user in this format."""
    status: Literal["input_required", "completed", "error"] = "input_required"
    message: str


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
                            if tool_input is not None:
                                return await tool.arun(tool_input, verbose, start_color, color, callbacks, **kwargs)
                            else:
                                return await tool.arun(tags, metadata, run_name, run_id, config, tool_call_id, **kwargs)

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

                if tool_input is not None:
                    ran = to_run_loop.run_until_complete(self.arun(tool_input, verbose, start_color,
                                                                   color, callbacks, **kwargs))
                else:
                    ran = to_run_loop.run_until_complete(self.arun(tags, metadata, run_name, run_id,
                                                                   config, tool_call_id, **kwargs))

                if close_loop:
                    to_run_loop.close()
                    asyncio.set_event_loop(None)

                if isinstance(ran, str):
                    ran = json.loads(ran)

                if v.stop_tool:
                    subprocess.run(v.stop_tool, shell=True)

                return ToolMessage(
                    content=ran,
                    name=self.name,
                    tool_call_id=tool_input.get("id") if isinstance(tool_input, dict) else None,
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
        return self.graph.invoke(query, config)

    async def stream(self, query, session_id, graph=None) -> AsyncIterable[Dict[str, Any]]:
        return self.stream_agent_response_graph(query, session_id, self.graph)

    def get_agent_response(self, config, graph=None):
        return self.get_agent_response_graph(config, self.graph)

    @staticmethod
    def get_agent_response_graph(config, graph):
        current_state = graph.get_state(config)
        structured_response = current_state.values.get('messages')
        if structured_response and isinstance(structured_response, ResponseFormat):
            if structured_response.status == "input_required":
                return {
                    "is_task_complete": False,
                    "require_user_input": True,
                    "content": structured_response.message
                }
            elif structured_response.status == "error":
                return {
                    "is_task_complete": False,
                    "require_user_input": True,
                    "content": structured_response.message
                }
            elif structured_response.status == "completed":
                return {
                    "is_task_complete": True,
                    "require_user_input": False,
                    "content": structured_response.message
                }

        return {
            "is_task_complete": False,
            "require_user_input": True,
            "content": "We are unable to process your request at the moment. Please try again.",
        }

    @staticmethod
    async def stream_agent_response_graph(query, sessionId, graph) -> AsyncIterable[Dict[str, Any]]:
        inputs = {"messages": [("user", query)]}
        config = {"configurable": {"thread_id": sessionId}}

        for item in graph.stream(inputs, config, stream_mode="values"):
            message = item["messages"][-1]
            if (
                    isinstance(message, AIMessage)
                    and message.tool_calls
                    and len(message.tool_calls) > 0
            ):
                yield {
                    "is_task_complete": False,
                    "require_user_input": False,
                    "content": "Looking up the exchange rates...",
                }
            elif isinstance(message, ToolMessage):
                yield {
                    "is_task_complete": False,
                    "require_user_input": False,
                    "content": "Processing the exchange rates..",
                }


class OrchestratorAgent(A2AReactAgent, abc.ABC):
    pass

@dataclasses.dataclass(init=True)
class NextAgentResponse:
    next_agent: str

class AgentOrchestrator(A2AAgent, abc.ABC):

    @abc.abstractmethod
    def orchestration_prompt(self):
        pass

    @abc.abstractmethod
    def parse_orchestration_response(self, last_message) -> typing.Union[BaseMessage, NextAgentResponse]:
        pass

class DelegatingToolA2AAgentOrchestrator(AgentOrchestrator, abc.ABC):
    """
    Generate a tool for each agent being orchestrated, then pass them into one model.
    """
    pass

class OrchestratedAgent:
    """
    Contains any arbitrary A2AAgent that can call invoke.
    """
    def __init__(self, agent: A2AAgent):
        self.agent = agent

@dataclasses.dataclass(init=True)
class OrchestratorAgentGraph:
    state_graph: StateGraph
    config: RunnableConfig

class StateGraphOrchestrator(AgentOrchestrator, abc.ABC):
    """
    Facilitate multi-agent through lang-graph state graph. This means multiple models, each with smaller prompt from lower number of tools.
    """
    def __init__(self, agents: typing.Dict[str, OrchestratedAgent], orchestrator_agent: OrchestratorAgent,
                 props: AgentConfigProps, memory: MemorySaver):
        """
        :param agents: agents being orchestrated
        :param orchestrator_agent: agent doing orchestration
        """
        A2AAgent.__init__(self)
        self.memory = memory
        self.props = props
        self.orchestrator_agent = orchestrator_agent
        self.agents = agents
        self.max_recurs = props.orchestrator_max_recurs if props.orchestrator_max_recurs else 5000
        from cdc_agents.agents.summarizer_agent import SummarizerAgent
        self.summarizer_agent = agents.get(SummarizerAgent.__name__)

    def get_next_node(self, last_executed_agent: BaseAgent, last_message: typing.Union[BaseMessage, NextAgentResponse],
                      state: MessagesState, session_id, message: typing.Optional[Message] = None):
        if message is not None and message.agent_route is not None:
            if message.agent_route not in self.agents.keys():
                LoggerFacade.error(f"Found message route {message.agent_route} not in keys {self.agents.keys()}")
            return message.agent_route

        if self.do_perform_summary(state):
            from cdc_agents.agents.summarizer_agent import SummarizerAgent
            return SummarizerAgent.__name__

        if isinstance(last_message, BaseMessage):
            is_last_message = last_executed_agent.is_terminate_node(last_message, state)
            if is_last_message:
                if (self.props.let_orchestrated_agents_terminate
                        or self.orchestrator_agent.agent_name == last_executed_agent.agent_name):
                    return END
                else:
                    return self.orchestrator_agent.agent_name
            else:
                return self.orchestrator_agent.agent_name
        elif isinstance(last_message, NextAgentResponse):
            return last_message.next_agent

        raise NotImplementedError

    #  TODO: for example, if too many messages
    def do_perform_summary(self, state: MessagesState) -> bool:
        if self.summarizer_agent is None:
            return False

        return False

    #  TODO: for example, if too many messages
    def do_collapse_summary_state(self, state: list[BaseMessage], agent: BaseAgent) -> list[BaseMessage]:
        from cdc_agents.agents.summarizer_agent import SummarizerAgent
        if isinstance(agent, SummarizerAgent):
            return agent.do_collapse(state)

        return state

    def next_node(self, agent: BaseAgent, state: MessagesState, session_id)-> Command[typing.Union[str, END]] :
        result = agent.invoke(state, session_id)

        result['messages'] = self.do_collapse_summary_state(result['messages'], agent)

        last_message: BaseMessage = result['messages'][-1]

        last_message = HumanMessage(content=last_message.content, name=agent.agent_name)

        result["messages"][-1] = last_message

        last_message = self.parse_orchestration_response(last_message)

        goto = self._goto_node(agent, last_message, result, session_id, state)

        return Command(
            update={"messages": result["messages"]},
            goto=goto)

    def _goto_node(self, agent, last_message, result, session_id, state):
        if self.task_manager:
            recent = self.pop_task_history(session_id)
            if recent is not None:
                content = self._parse_content(recent)
                result['messages'].append(HumanMessage(content=content, name="pushed task"))
                goto = self.get_next_node(agent, last_message, state, session_id, recent)
            else:
                goto = self.get_next_node(agent, last_message, state, session_id)
        else:
            goto = self.get_next_node(agent, last_message, state, session_id)
        if goto == self.orchestrator_agent.agent_name and agent.agent_name == self.orchestrator_agent.agent_name:
            last_message.content.append(
                f"Did not receive a {self.terminal_string} delimited with {self.terminal_string} or which agent to forward to. "
                f"Please either summarize into a {self.terminal_string} or delegate to one of you're agents who will.")
        return goto

    def _parse_content(self, recent):
        content = []
        for p in recent.parts:
            if p.type is not None and p.type != 'text':
                LoggerFacade.error(f"Found unknown message type, {p.type}")
            else:
                content.append(p.text)

        return content

    def _create_orchestration_graph(self, session_id) -> OrchestratorAgentGraph:
        return OrchestratorAgentGraph(self._create_state_graph(session_id),
                                      self._create_orchestration_config(session_id))

    def _create_state_graph(self, session_id) -> StateGraph:
        state_graph = StateGraph(MessagesState)
        state_graph.add_node(self.orchestrator_agent.agent_name,
                             lambda state: self.next_node(self.orchestrator_agent, state, session_id))

        for agent_name, agent in self.agents.items():
            state_graph.add_node(agent_name, lambda state: self.next_node(agent.agent, state, session_id))

        state_graph.set_entry_point(self.orchestrator_agent.agent_name)
        return state_graph

    def _create_orchestration_config(self, sessionId) -> RunnableConfig:
        return {
            "configurable": {"thread_id": sessionId},
            "recursion_limit": self.max_recurs}

    def invoke(self, query, sessionId):
        config, graph = self._create_invoke_graph(query, sessionId)
        return self.get_agent_response(config, graph)

    def _create_invoke_graph(self, query, sessionId):
        a = self._create_orchestration_graph(sessionId)
        config = a.config
        state_graph = a.state_graph
        graph = state_graph.compile(checkpointer=MemorySaver())
        graph.invoke({"messages": [("user", query)]}, config)
        return config, graph

    def get_agent_response(self, config, graph = None):
        if graph is None:
            LoggerFacade.error("Graph was None for State Graph - get_agent_response must be called after invoked.")
        return self.get_agent_response_graph(config, graph)

    async def stream(self, query, sessionId, graph = None) -> AsyncIterable[Dict[str, Any]]:
        if graph is None:
            _, graph = self._create_invoke_graph(query, sessionId)
        return self.stream_agent_response_graph(query, sessionId, graph)


