import abc

from cdc_agents.agent.agent import A2AAgent, StateGraphA2AOrchestrator, OrchestratedAgent, A2AOrchestratorAgent, \
    BaseAgent
import dataclasses
import enum
import typing
from typing import Any, Dict, AsyncIterable

import httpx
import injector
import torch
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool

from cdc_agents.agent.agent import A2AAgent, ResponseFormat
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
from python_di.configs.autowire import injectable
from python_di.configs.component import component

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
    raise NotImplementedError()

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
        A2AAgent.__init__(self,
                          agent_config.agents['DeepCodeAgent'].agent_descriptor.model
                          if 'DeepCodeAgent' in agent_config.agents.keys() else None,
                          [call_a_friend],
                          self.SYSTEM_INSTRUCTION)
        self.agent_config: AgentCardItem = agent_config.agents['DeepCodeAgent'] \
            if 'DeepCodeAgent' in agent_config.agents.keys() else None

    @property
    def orchestrator_prompt(self):
        pass

    def invoke(self, query, sessionId) -> str:
        config = {"configurable": {"thread_id": sessionId}}
        self.graph.invoke({"messages": [("user", query)]}, config)
        return self.get_agent_response(config)

    async def stream(self, query, sessionId, graph=None) -> AsyncIterable[Dict[str, Any]]:
        return self.stream_agent_response_graph(query, sessionId, self.graph)

    def get_agent_response(self, config, graph=None):
        return self.get_agent_response_graph(config, self.graph)


    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]


@component(bind_to=[A2AAgent])
@injectable()
class DeepCodeOrchestrator(StateGraphA2AOrchestrator):

    @injector.inject
    def __init__(self,
                 agents: typing.List[DeepResearchOrchestrated],
                 orchestrator_agent: DeepCodeAgent,
                 props: AgentConfigProps):
        StateGraphA2AOrchestrator.__init__(self,
                                           {a.agent_name: OrchestratedAgent(a) for a in agents if
                                            isinstance(a, A2AAgent)},
                                           orchestrator_agent, props)
    @property
    def agent_name(self) -> str:
        return f'Graph orchestrator agent; {self.orchestrator_agent.agent_name}'

