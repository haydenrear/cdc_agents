import abc
import dataclasses
import typing
from typing import AsyncIterable, Dict, Any, Optional
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.utils import Input, Output
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import END
from langgraph.graph import StateGraph, MessagesState
from langgraph.types import Command, Runnable

from cdc_agents.agent.a2a import A2AAgent, BaseAgent
from cdc_agents.agent.agent import A2AReactAgent
from cdc_agents.common.types import Message
from cdc_agents.config.agent_config_props import AgentConfigProps
from python_util.logger.logger import LoggerFacade


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


class OrchestratedAgent:
    """
    Contains any arbitrary A2AAgent that can call invoke.
    """

    def __init__(self, agent: A2AAgent):
        self.agent = agent


@dataclasses.dataclass(init=True)
class OrchestratorAgentGraph:
    state_graph: StateGraph


class DelegatingToolA2AAgentOrchestrator(AgentOrchestrator, abc.ABC):
    """
    Generate a tool for each agent being orchestrated, then pass them into one model.
    """
    pass


class OrchestratorAgent(A2AReactAgent, abc.ABC):
    pass


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
        self.graph = self._build_graph()

    def get_next_node(self, last_executed_agent: BaseAgent, last_message: typing.Union[BaseMessage, NextAgentResponse],
                      state: MessagesState, config, message: typing.Optional[Message] = None):
        if message is not None and message.agent_route is not None:
            if message.agent_route not in self.agents.keys():
                LoggerFacade.error(f"Found message route {message.agent_route} not in keys {self.agents.keys()}")
            else:
                return message.agent_route

        if self.do_perform_summary(state, config):
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
    def do_perform_summary(self, state: typing.Union[MessagesState, typing.List[BaseMessage]], config) -> bool:
        if self.summarizer_agent is None:
            return False

        return False

    #  TODO: for example, if too many messages
    def do_collapse_summary_state(self, state: list[BaseMessage], agent: BaseAgent, config) -> list[BaseMessage]:
        from cdc_agents.agents.summarizer_agent import SummarizerAgent
        if isinstance(agent, SummarizerAgent):
            return agent.do_collapse(state, config)

        return state

    def invoke(self, query, sessionId):
        config, graph = self._create_invoke_graph(query, sessionId)
        return self.get_agent_response(config, graph)

    def next_node(self, agent: BaseAgent, state: MessagesState, config, *args, **kwargs) -> Command[typing.Union[str, END]]:
        session_id = config['configurable']['thread_id']
        result = agent.invoke(state, session_id)

        result['messages'] = self.do_collapse_summary_state(result['messages'], agent, config)

        last_message: BaseMessage = result['messages'][-1]

        last_message = HumanMessage(content=last_message.content, name=agent.agent_name)

        result["messages"][-1] = last_message

        last_message = self.parse_orchestration_response(last_message)

        return self.parse_messages(agent, last_message, result, session_id, state, config)

    def parse_messages(self, agent, last_message, result, session_id, state, config) -> Command[typing.Union[str, END]]:
        if self.do_perform_summary(result, config):
            goto = self.get_next_node(agent, last_message, state, session_id)
        elif self.task_manager:
            recent = self.pop_task_history(session_id)
            if recent is not None:
                # only route to a single agent at a time, but can add as many other messages to the context
                result['messages'].append(HumanMessage(content=self._parse_content(recent), name="pushed task"))

                while recent is not None and recent.agent_route is not None:
                    result['messages'].append(
                        HumanMessage(content=self._parse_content(self.peek_task_history(session_id)),
                                     name="pushed task"))
                    # if the next message appended, no matter what it is, pushes number of tokens too big, then
                    # ignore that message for now, keep it in TaskManager, and don't replace recent for the get_next_node
                    # call for below
                    if self.do_perform_summary(result['messages'], config):
                        # pop the message we just added to check if it pushes over token limit for summary
                        result['messages'].pop()
                        break
                    else:
                        # pop already appended to result, but still in task manager queue, remove from task manager
                        # queue here and set to recent to check if go out of loop now.
                        recent = self.pop_task_history(session_id)

            goto = self.get_next_node(agent, last_message, state, session_id, recent)
        else:
            goto = self.get_next_node(agent, last_message, state, session_id)
        if goto == self.orchestrator_agent.agent_name and agent.agent_name == self.orchestrator_agent.agent_name:
            last_message.content.append(
                f"Did not receive a {self.terminal_string} delimited with {self.terminal_string} or which agent to forward to. "
                f"Please either summarize into a {self.terminal_string} or delegate to one of you're agents who will.")
        return Command(update={"messages": result["messages"]},
                       goto=goto)

    def _parse_content(self, recent):
        content = []
        for p in recent.parts:
            if p.type is not None and p.type != 'text':
                LoggerFacade.error(f"Found unknown message type, {p.type}")
            else:
                content.append(p.text)

        return content

    def _create_orchestration_graph(self) -> OrchestratorAgentGraph:
        return OrchestratorAgentGraph(self._create_state_graph())

    def _create_state_graph(self) -> StateGraph:
        state_graph = StateGraph(MessagesState)
        state_graph.add_node(self.orchestrator_agent.agent_name,
                             lambda state, config: self.next_node_inner(self.orchestrator_agent))

        for agent_name, agent in self.agents.items():
            state_graph.add_node(agent_name,
                                 lambda state, config, next_agent=agent.agent: self.next_node_inner(next_agent))

        state_graph.set_entry_point(self.orchestrator_agent.agent_name)
        return state_graph

    def next_node_inner(self, agent):
        from langchain_core.runnables import RunnableLambda
        return RunnableLambda(lambda s, config, *args, **kwargs: self.next_node(agent, s, config=config, *args, **kwargs))

    def _create_orchestration_config(self, sessionId) -> RunnableConfig:
        return {
            "configurable": {"thread_id": sessionId},
            "recursion_limit": self.max_recurs}

    def _create_invoke_graph(self, query, sessionId):
        self.graph = self._create_compile_graph()
        config = self._create_orchestration_config(sessionId)
        self.graph.invoke({"messages": [("user", query)]}, config)
        return config, self.graph

    def _create_compile_graph(self):
        if self.graph is None:
            self.graph = self._build_graph()
        return self.graph

    def _build_graph(self):
        a = self._create_orchestration_graph()
        state_graph = a.state_graph
        return state_graph.compile(checkpointer=self.memory)

    def get_agent_response(self, config, graph=None):
        if graph is None:
            LoggerFacade.error("Graph was None for State Graph - get_agent_response must be called after invoked.")
        found = self.get_agent_response_graph(config, graph)
        return found

    async def stream(self, query, session_id, graph=None) -> AsyncIterable[Dict[str, Any]]:
        if graph is None:
            _, graph = self._create_invoke_graph(query, session_id)
        return self.stream_agent_response_graph(query, session_id, graph)
