import abc
import asyncio
import dataclasses
import typing
from typing import Any, Dict, AsyncIterable
from typing import Literal

from langchain.agents import AgentExecutor
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.messages import HumanMessage, BaseMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_ollama import ChatOllama, OllamaLLM
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import MessagesState, END
from langgraph.graph import StateGraph
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from pydantic import BaseModel
from pydantic_core.core_schema import model_field, model_schema

from cdc_agents.common.types import PushTaskEvent, PushTaskEventResponseItem
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentMcpTool, AgentCardItem
from cdc_agents.model_server.model_provider import ModelProvider
from python_util.logger.logger import LoggerFacade

class TaskEventHook(abc.ABC):
    @abc.abstractmethod
    def do_on_event(self, request: PushTaskEvent, *args, **kwargs) -> PushTaskEventResponseItem:
        pass

    def __call__(self, request: PushTaskEvent, *args, **kwargs) -> PushTaskEventResponseItem:
        return self.do_on_event(*args, **kwargs)

class ResponseFormat(BaseModel):
    """Respond to the user in this format."""
    status: Literal["input_required", "completed", "error"] = "input_required"
    message: str

class BaseAgent(abc.ABC):

    @abc.abstractmethod
    def invoke(self, query, sessionId) -> str:
        pass

    @property
    @abc.abstractmethod
    def agent_name(self) -> str:
        pass

    @property
    def terminal_string(self) -> str:
        return "FINAL ANSWER"

    def is_terminate_node(self, last_message, state) -> bool:
        return self.message_contains(last_message, self.terminal_string)

    def message_contains(self, last_message, answer) -> bool:
        return answer in last_message.content or any([answer in c for c in last_message.content])

class A2AAgent(BaseAgent, abc.ABC):
    def __init__(self, model=None, tools=None, system_instruction=None,
                 memory: MemorySaver = MemorySaver(),
                 task_event_hooks: typing.Optional[typing.List[TaskEventHook]] = None):
        self._task_event_hooks = task_event_hooks
        self.model = model
        self.tools = tools
        self.system_instruction = system_instruction
        self.memory = memory
        self._agent_name = self.__class__.__name__

    @property
    def task_event_hooks(self) -> list[TaskEventHook]:
        return self._task_event_hooks

    @property
    def supported_content_types(self) -> list[str]:
        if not hasattr(self, 'SUPPORTED_CONTENT_TYPES'):
            raise NotImplementedError("Could not find supported content.")

        return getattr(self, 'SUPPORTED_CONTENT_TYPES')

    @property
    def agent_name(self) -> str:
        return self._agent_name

    @abc.abstractmethod
    async def stream(self, query, sessionId, graph=None) -> AsyncIterable[Dict[str, Any]]:
        pass

    @abc.abstractmethod
    def get_agent_response(self, config, graph):
        pass

    @abc.abstractmethod
    def add_mcp_tools(self, additional_tools: typing.Dict[str, AgentMcpTool] = None):
        pass

    @abc.abstractmethod
    async def add_mcp_tools_async(self, additional_tools: typing.Dict[str, AgentMcpTool] = None):
        pass

class A2ASmolAgent(A2AAgent, abc.ABC):
    def __init__(self, agent_config: AgentConfigProps, tools, system_instruction,
                 memory: MemorySaver, model = None, task_event_hooks: typing.Optional[typing.List[TaskEventHook]] = None):
        this_agent_name = self.__class__.__name__
        model = agent_config.agents[this_agent_name].agent_descriptor.model \
            if this_agent_name in agent_config.agents.keys() else None \
            if model is None else model
        A2AAgent.__init__(self, model, tools, system_instruction, memory, task_event_hooks)
#       TODO: create different types of SmolAgent, and then stream result as in above - can be streamed to langgraph
#           graph the same, but can have python code calling instead of tool calling, and can have multi-agent.


class A2AReactAgent(A2AAgent, abc.ABC):

    def __init__(self, agent_config: AgentConfigProps, tools, system_instruction,
                 memory: MemorySaver, model_server_provider: ModelProvider, model = None,
                 task_event_hooks: typing.Optional[typing.List[TaskEventHook]] = None):
        self.model_server_provider = model_server_provider
        this_agent_name = self.__class__.__name__
        self.model = self.model_server_provider.retrieve_model(
            agent_config.agents[this_agent_name] if this_agent_name in agent_config.agents.keys() else None, model)
        A2AAgent.__init__(self, self.model, tools, system_instruction, memory, task_event_hooks)
        self.graph = create_react_agent(
            self.model, tools=self.tools, checkpointer=self.memory,
            prompt = self.system_instruction)
        self.agent_config: AgentCardItem = agent_config.agents[this_agent_name] \
            if this_agent_name in agent_config.agents.keys() else None

    def add_mcp_tools(self, additional_tools: typing.Dict[str, AgentMcpTool] = None):
        asyncio.run(self.add_mcp_tools_async(additional_tools))

    async def add_mcp_tools_async(self, additional_tools: typing.Dict[str, AgentMcpTool] = None):
        if additional_tools is not None:
            async with MultiServerMCPClient({s.name: s.tool_options for k,s in additional_tools.items()}) as client:
                self.tools.extend(client.get_tools())
            self.graph = create_react_agent(
                self.model, tools=self.tools, checkpointer=self.memory,
                prompt = self.system_instruction)

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

    def get_next_node(self, last_executed_agent: BaseAgent, last_message: typing.Union[BaseMessage, NextAgentResponse], state):
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

    def next_node(self, agent: BaseAgent, state: MessagesState, session_id)-> Command[typing.Union[str, END]] :
        result = agent.invoke(state, session_id)
        last_message: BaseMessage = result["messages"][-1]

        last_message = HumanMessage(content=last_message.content, name=agent.agent_name)

        result["messages"][-1] = last_message

        last_message = self.parse_orchestration_response(last_message)

        goto = self.get_next_node(agent, last_message, state)

        if goto == self.orchestrator_agent.agent_name and agent.agent_name == self.orchestrator_agent.agent_name:
            last_message.content.append(f"Did not receive a {self.terminal_string} delimited with {self.terminal_string} or which agent to forward to. "
                                        f"Please either summarize into a {self.terminal_string} or delegate to one of you're agents who will.")

        return Command(
            update={"messages": result["messages"]},
            goto=goto)

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


