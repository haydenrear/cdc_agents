import abc

from langchain.agents import create_react_agent

from cdc_agents.agent.agent import A2AAgent, StateGraphOrchestrator, OrchestratedAgent, A2AOrchestratorAgent, \
    BaseAgent, NextAgentResponse
import dataclasses
import enum
import typing
from typing import Any, Dict, AsyncIterable

import httpx
import injector
import torch
from langchain_core.messages import AIMessage, ToolMessage, BaseMessage
from langchain_core.tools import tool

from cdc_agents.agent.agent import A2AAgent, ResponseFormat
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
from python_di.configs.autowire import injectable
from python_di.configs.component import component
from python_di.inject.profile_composite_injector.composite_injector import profile_scope
from python_di.inject.profile_composite_injector.scopes.profile_scope import ProfileScope


class DeepResearchOrchestrated(BaseAgent, abc.ABC):
    """
    Marker interface for DI, marking the agents being orchestrated.
    """
    @property
    @abc.abstractmethod
    def orchestrator_prompt(self):
        """
        :return: what information to provide the orchestrator in a prompt.
        """
        pass


@tool
def call_a_friend():
    """Call a human in the loop to validate we're moving the correct direction.

    Args:

    Returns:

    """
    raise NotImplementedError

@component(bind_to=[A2AAgent])
@injectable()
class DeepCodeAgent(A2AOrchestratorAgent, DeepResearchOrchestrated):

    SYSTEM_INSTRUCTION = (
        """
        You are an orchestrator agent that delegates to other agents to retrieve contextual information for generating code 
        that can add features and submit bug patches across multiple repositories and projects.
        The agents that you orchestrate have access to tools that they can use to provide contextual information to you, orchestrate
        tooling to facilitate adding contextual information to you, generate the code, and run the code to provide feedback
        and testing services.
        """
    )

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps):
        agent = 'DeepCodeAgent'
        A2AAgent.__init__(self,
                          agent_config.agents[agent].agent_descriptor.model
                          if agent in agent_config.agents.keys() else None,
                          [call_a_friend],
                          self.SYSTEM_INSTRUCTION)
        self.agent_config: AgentCardItem = agent_config.agents[agent] \
            if agent in agent_config.agents.keys() else None

    @property
    def orchestrator_prompt(self):
        pass

    def invoke(self, query, sessionId) -> str:
        config = {"configurable": {"thread_id": sessionId}}
        if isinstance(query, dict) and "messages" in query.keys():
            self.graph.invoke(query, config)
        else:
            self.graph.invoke({"messages": [{"content": query}]}, config)

        return self.get_agent_response(config)

    async def stream(self, query, sessionId, graph=None) -> AsyncIterable[Dict[str, Any]]:
        return self.stream_agent_response_graph(query, sessionId, self.graph)

    def get_agent_response(self, config, graph=None):
        return self.get_agent_response_graph(config, self.graph)

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]


@component(bind_to=[A2AAgent])
@injectable()
class DeepCodeOrchestrator(StateGraphOrchestrator):

    @injector.inject
    def __init__(self,
                 agents: typing.List[DeepResearchOrchestrated],
                 orchestrator_agent: DeepCodeAgent,
                 props: AgentConfigProps):
        StateGraphOrchestrator.__init__(self,
                                        {a.agent_name: OrchestratedAgent(a) for a in agents if
                                            isinstance(a, A2AAgent)},
                                        orchestrator_agent, props)

    @property
    def agent_name(self) -> str:
        return f'Graph orchestrator agent; {self.orchestrator_agent.agent_name}'

    def orchestration_prompt(self):
        return "hello!"

    def parse_orchestration_response(self, last_message: BaseMessage) -> typing.Union[BaseMessage, NextAgentResponse]:
        found = list(filter(lambda x: 'NEXT AGENT:' in x, last_message.content if isinstance(last_message.content, list) else [last_message.content]))
        if len(found) == 0:
            return last_message
        else:
            split = found[0].split('NEXT AGENT:')
            if len(split) <= 1:
                return last_message
            f = split[1].strip()
            return NextAgentResponse(f)

