import abc

from langchain.agents import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agent.agent import A2AReactAgent
from cdc_agents.agent.agent_orchestrator import OrchestratorAgent, NextAgentResponse, OrchestratedAgent, \
    StateGraphOrchestrator
from cdc_agents.agent.a2a import BaseAgent, A2AAgent
import dataclasses
import enum
import typing
from typing import Any, Dict, AsyncIterable

import httpx
import injector
import torch
from langchain_core.messages import AIMessage, ToolMessage, BaseMessage
from langchain_core.tools import tool

from cdc_agents.agent.agent import A2AAgent
from cdc_agents.common.types import ResponseFormat, AgentGraphResponse
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem, AgentMcpTool
from cdc_agents.model_server.model_provider import ModelProvider
from python_di.configs.autowire import injectable
from python_di.configs.component import component
from python_di.inject.profile_composite_injector.composite_injector import profile_scope
from python_di.inject.profile_composite_injector.scopes.profile_scope import ProfileScope


class DeepResearchOrchestrated(BaseAgent, abc.ABC):

    def __init__(self, agent: AgentCardItem):
        self._orchestrator_prompt = agent.agent_descriptor.orchestrator_instruction

    """
    Marker interface for DI, marking the agents being orchestrated.
    """
    @property
    def orchestrator_prompt(self):
        """
        :return: what information to provide the orchestrator in a prompt.
        """
        return self._orchestrator_prompt

@component(bind_to=[A2AAgent, A2AReactAgent])
@injectable()
class DeepCodeAgent(OrchestratorAgent):

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver,
                 agents: typing.List[DeepResearchOrchestrated], model_provider: ModelProvider):
        orchestrator_prompts = {a.agent_name: a.orchestrator_prompt for a in agents}

        self_card: AgentCardItem = agent_config.agents[self.__class__.__name__]

        OrchestratorAgent.__init__(self, self_card)


        self.SYSTEM_INSTRUCTION = f"""
        {self.orchestration_prompt}
        {self._parse_agents_lines(orchestrator_prompts)}
        {self.orchestration_messages}
        """
        A2AReactAgent.__init__(self, agent_config, [], self.SYSTEM_INSTRUCTION, memory_saver,
                               model_provider)

    def _parse_agents_lines(self, orchestrator_prompts):
        return '\n\n'.join(self._parse_agents(orchestrator_prompts))

    def _parse_agents(self, orchestrator_prompts):
        return [f'''
        agent name: 
            {k} 
        agent info: 
            {v}
        ''' for k, v in orchestrator_prompts.items()]

    def invoke(self, query, sessionId) -> AgentGraphResponse:
        config = {"configurable": {"thread_id": sessionId}}
        if isinstance(query, dict) and "messages" in query.keys():
            self.graph.invoke(query, config)
        else:
            self.graph.invoke({"messages": [{"content": query}]}, config)

        return self.get_agent_response(config)

    def stream(self, query, sessionId, graph=None) -> AsyncIterable[Dict[str, Any]]:
        return self.stream_agent_response_graph(query, sessionId, self.graph)

    def get_agent_response(self, config, graph=None):
        return self.get_agent_response_graph(config, self.graph)



@component(bind_to=[A2AAgent, A2AReactAgent])
@injectable()
class DeepCodeOrchestrator(StateGraphOrchestrator):

    @injector.inject
    def __init__(self,
                 agents: typing.List[DeepResearchOrchestrated],
                 orchestrator_agent: DeepCodeAgent,
                 props: AgentConfigProps,
                 memory_saver: MemorySaver):
        StateGraphOrchestrator.__init__(self,
                                        {a.agent_name: OrchestratedAgent(a) for a in agents if
                                            isinstance(a, A2AAgent)},
                                        orchestrator_agent, props, memory_saver)

    @property
    def agent_name(self) -> str:
        return f'Graph orchestrator agent; {self.orchestrator_agent.agent_name}'

    def parse_orchestration_response(self, last_message: AgentGraphResponse) -> AgentGraphResponse:
        return last_message