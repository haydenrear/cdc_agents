import abc
import dataclasses
import time
from cdc_agents.agent.agent_state import AgentState
from langchain_core.runnables import AddableDict
import typing
from typing import AsyncIterable, Dict, Any, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.runnables.utils import Input, Output
from langgraph.checkpoint.memory import MemorySaver
from langgraph.constants import END
from langgraph.graph import StateGraph, MessagesState
from langgraph.types import Command, Runnable

from cdc_agents.model_server.model_provider import ModelProvider
from cdc_agents.agent.a2a import A2AAgent, BaseAgent
from cdc_agents.agent.agent import A2AReactAgent
from cdc_agents.common.server import TaskManager
from cdc_agents.common.types import Message, ResponseFormat, AgentGraphResponse, AgentGraphResult, WaitStatusMessage
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
from python_util.logger.logger import LoggerFacade


@dataclasses.dataclass(init=True)
class NextAgentResponse:
    next_agent: str


class AgentOrchestrator(A2AAgent, abc.ABC):

    @abc.abstractmethod
    def parse_orchestration_response(self, last_message: AgentGraphResult):
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


class OrchestratorAgent(abc.ABC):

    def __init__(self, self_card: AgentCardItem):
        self._orchestration_message = self_card.agent_descriptor.orchestration_message
        self._orchestration_prompt = self_card.agent_descriptor.orchestration_instruction

    @property
    def orchestration_prompt(self):
        return self._orchestration_prompt

    @property
    def orchestration_messages(self):
        return self._orchestration_message


class StateGraphOrchestrator(AgentOrchestrator, abc.ABC):
    """
    Facilitate multi-agent through lang-graph state graph. This means multiple models, each with smaller prompt from lower number of tools.
    """

    def __init__(self, agents: typing.Dict[str, OrchestratedAgent], orchestrator_agent: typing.Union[OrchestratorAgent, A2AAgent],
                 props: AgentConfigProps, memory: MemorySaver, model_provider: ModelProvider):
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
        self.summarizer_name = SummarizerAgent.__name__
        from langmem.short_term import SummarizationNode
        summarizer_card = typing.cast(AgentCardItem, self.props.agents[self.summarizer_name])
        self.summarizer_node = SummarizationNode(
            model=model_provider.retrieve_model(summarizer_card),
            **summarizer_card.options)
        self.graph = self._build_graph()

    def get_next_node(self, last_executed_agent: BaseAgent, graph_result: AgentGraphResult,
                      state: MessagesState, config):

        last_executed_agent_name = last_executed_agent.agent_name
        is_this_agent_orchestrator = self._is_orchestrator(last_executed_agent_name)

        if not is_this_agent_orchestrator:
            return self.summarizer_name
        elif last_executed_agent_name == self.summarizer_name:
            return self.orchestrator_agent.agent_name

        if graph_result.agent_route is not None and is_this_agent_orchestrator:
            if graph_result.agent_route not in self.agents.keys():
                LoggerFacade.error(f"Found message route {graph_result.agent_route} not in keys {self.agents.keys()}")
                graph_result.add_last_message(SystemMessage(content=f"""
                    Agent of name {graph_result.agent_route} was not found from previous message. Can you please to delegate to one of the valid agents:
                    {','.join([a for a in self.agents.keys()])} 
                """, name=self.orchestrator_agent.agent_name))
                return self.orchestrator_agent.agent_name
            else:
                return graph_result.agent_route
        elif graph_result.agent_route is not None and not is_this_agent_orchestrator:
            if graph_result.agent_route in self.agents.keys():
                LoggerFacade.error(f"Found agent routing directly to another agent: {last_executed_agent_name}. "
                                   f"Haven't handled this explicitly. Adding a message to the orchestrator that this happened.")
                graph_result.add_to_last_message(f'Found agent {last_executed_agent_name} routing to another agent {graph_result.agent_route}. '
                                                 f'Please consider this to determine whether to add context and route to this agent.')
            else:
                LoggerFacade.error(f"Found message route {graph_result.agent_route} not in keys {self.agents.keys()}")

        if graph_result.require_user_input and is_this_agent_orchestrator:
            return END

        if last_executed_agent.is_terminate_node(graph_result, state) and is_this_agent_orchestrator:
            return END

        return self.orchestrator_agent.agent_name

    def _is_orchestrator(self, name):
        return self.orchestrator_agent.agent_name == name

    def invoke(self, query, sessionId) -> AgentGraphResponse:
        config, graph = self._create_invoke_graph(query, sessionId)
        return self.get_agent_response(config, graph)

    def retrieve_status_messages(self, message: typing.Optional[BaseMessage]) -> typing.Optional[WaitStatusMessage]:
        if message is None:
            return None
        return self.get_status_message(message)

    def next_node(self, agent: BaseAgent, state: AgentState, config, *args, **kwargs) -> Command[typing.Union[str, END]]:
        # prev_messages = state.get('messages')
        # If received a message to route to another agent, route to that other agent.
        # if prev_messages is not None and len(prev_messages) > 1:
        #     second_to_last = prev_messages[-2]
        #     status_messages = self.retrieve_status_messages(second_to_last)
        #     wait_status_message = self.retrieve_status_messages(status_messages)
        #     if self._is_valid_wait_status(wait_status_message):
        #         # an agent is waiting, so call directly that agent  TODO: awaiting status update.
        #         return Command(update={"messages": prev_messages},
        #                        goto=wait_status_message.agent_route)

        config['configurable']['checkpoint_time'] = time.time_ns()
        session_id = config['configurable']['thread_id']
        state['session_id'] = session_id


        before_len = len(state['messages']) if 'messages' in state.keys() and state['messages'] else 0

        result: AgentGraphResponse = agent.invoke(state, session_id)

        config['configurable']['checkpoint_time'] = time.time_ns()

        if result.content.route_to == 'orchestrator':
            result.content.route_to = self.orchestrator_agent.agent_name

        messages = self._retrieve_messages(result.content, agent.agent_name)

        for m in messages[before_len:]:
            if not m.name:
                m.name = agent.agent_name

        messages = self._remove_prev_considers(messages)

        last_message: BaseMessage = messages.pop()

        if last_message.type == 'tool':
            messages.append(last_message)
            if agent.agent_name != self.orchestrator_agent.agent_name:
                # TODO: any of these should then be removed before adding this one
                messages.append(HumanMessage(content='Can you please consider whether the task is completed, considering the previous tool message response? '
                                                     'If so can you return the context of the result. If not, can you continue with the task by considering '
                                                     'what is still necessary and delegating to the agent that can help continue/complete the task?',
                                             name='human'))
        elif isinstance(result.content, ResponseFormat):
            if result.is_task_complete:
                message = last_message.content
                messages.append(AIMessage(content=message, name=agent.agent_name))
            else:
                message = last_message.content
                if agent.agent_name != self.orchestrator_agent.agent_name:
                    messages.append(AIMessage(content=message, name=agent.agent_name))
                    # TODO: any of these should then be removed before adding this one
                    messages.append(HumanMessage(content=f'Can you please consider whether the task is completed, considering the previous message from agent {agent.agent_name}? '
                                                         'If so can you return the context of the result. If not, can you continue with the task by considering '
                                                         'what is still necessary and delegating to the agent that can help continue/complete the task?',
                                                 name='human'))
                else:
                    messages.append(HumanMessage(content=message, name=agent.agent_name))


        agent_graph_parsed = AgentGraphResult(
            content=messages, is_task_complete=result.is_task_complete,
            require_user_input=result.require_user_input,
            agent_route=result.content.route_to if isinstance(result.content, ResponseFormat) else None,
            last_message=messages[-1])

        agent_graph_parsed = self.parse_orchestration_response(agent_graph_parsed)

        found = self.parse_messages(agent, agent_graph_parsed, session_id, state, config)

        return found

    def _remove_prev_considers(self, messages: typing.List[BaseMessage]):
        to_remove = []
        for m in messages:
            if m and m.content and isinstance(m.content, str) and m.content.startswith(
                    'Can you please consider whether the task is completed'):
                to_remove.append(m)
        for to_remove_item in to_remove:
            messages.remove(to_remove_item)

        return messages

    def _is_valid_wait_status(self, wait_status_message):
        return ((wait_status_message is not None) and
                (wait_status_message.agent_route in self.agents.keys() or self.orchestrator_agent.agent_name == wait_status_message.agent_route))

    def _retrieve_messages(self, content:  typing.Union[ResponseFormat, str, list[BaseMessage]], agent_name) -> typing.List[BaseMessage]:
        if isinstance(content, ResponseFormat):
            return self._retrieve_messages(content.history, agent_name)
        elif isinstance(content, list) and len(content) > 0 and isinstance(content[0], BaseMessage):
            return content
        elif isinstance(content, str):
            return [HumanMessage(content=content, name=agent_name)]
        elif content is None:
            raise ValueError("Found None content.")
        return [HumanMessage(content=f"Empty message found from {agent_name}. Please retry or redirect.", name=agent_name)]

    def parse_messages(self, agent, result: AgentGraphResult, session_id, state, config) -> Command[typing.Union[str, END]]:
        if self.task_manager:
            recent = self.pop_to_process_task(session_id)
            if recent is not None:
                # only route to a single agent at a time, but can add as many other messages to the context
                result.content.append(HumanMessage(content=self._parse_content(recent), name="pushed task"))

                while recent is not None and recent.agent_route is not None:
                    result.content.append(
                        HumanMessage(content=self._parse_content(self.peek_to_process_task(session_id)),
                                     name="pushed task"))
                    # pop already appended to result, but still in task manager queue, remove from task manager
                    # queue here and set to recent to check if go out of loop now.
                    recent = self.pop_to_process_task(session_id)

            goto = self.get_next_node(agent, result, state, session_id)
        else:
            goto = self.get_next_node(agent, result, state, session_id)
        if goto == self.orchestrator_agent.agent_name and agent.agent_name == self.orchestrator_agent.agent_name:
            result.add_to_last_message(
                f"Did not receive a {self.terminal_string} delimited with {self.terminal_string} or which agent to forward to. "
                f"Please either summarize into a {self.terminal_string} or delegate to one of you're agents who will.")

        if goto == END:
            result.content = self._remove_prev_considers(result.content)

        return Command(update={"messages": result.content},
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
        state_graph = StateGraph(AgentState)
        state_graph.add_node(self.orchestrator_agent.agent_name,
                             lambda state, config: self.next_node_inner(self.orchestrator_agent))

        state_graph.add_node(self.summarizer_name, self.summarizer_node)

        for agent_name, agent in self.agents.items():
            if agent_name != self.summarizer_name:
                state_graph.add_node(agent_name,
                                     lambda state, config, next_agent=agent.agent: self.next_node_inner(next_agent))

        state_graph.add_edge(self.summarizer_name, self.orchestrator_agent.agent_name)
        state_graph.set_entry_point(self.orchestrator_agent.agent_name)
        return state_graph

    def next_node_inner(self, agent):
        from langchain_core.runnables import RunnableLambda
        return RunnableLambda(lambda s, config, *args, **kwargs: self.next_node(agent, s, config=config, *args, **kwargs))

    def _create_orchestration_config(self, sessionId) -> RunnableConfig:
        return A2AReactAgent._parse_query_config_max(sessionId, self.max_recurs)

    def _create_invoke_graph(self, query, sessionId):
        self.graph = self._create_compile_graph()
        config = self._create_orchestration_config(sessionId)
        self.graph.invoke(TaskManager.get_user_query_message(query, sessionId), config)
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
