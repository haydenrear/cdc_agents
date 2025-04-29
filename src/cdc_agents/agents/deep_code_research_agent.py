from cdc_agents.agent.agent import A2AAgent, StateGraphA2AOrchestrator, OrchestratedAgent, A2AOrchestratorAgent
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
from cdc_agents.agents.commit_diff_context_server_agent import DeepResearchOrchestrated
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
from python_di.configs.autowire import injectable
from python_di.configs.component import component

@tool
def call_a_friend():
    """Call a human in the loop to validate we're moving the correct direction.

    Args:

    Returns:

    """
    raise NotImplementedError()

@component()
@injectable()
class DeepCodeAgent(A2AOrchestratorAgent, DeepResearchOrchestrated):

    SYSTEM_INSTRUCTION = (
        """
        You are a specialized assistant for code context information.
        # Your sole purpose is to use the 'get_exchange_rate' tool to answer questions about currency exchange rates.
        # If the user asks about anything other than currency conversion or exchange rates,
        # politely state that you cannot help with that topic and can only assist with currency-related queries. 
        # Do not attempt to answer unrelated questions or use tools for other purposes.
        # Set response status to input_required if the user needs to provide more information.
        # Set response status to error if there is an error while processing the request.
        # Set response status to completed if the request is complete.
        """
    )

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps):
        A2AAgent.__init__(self,
                          agent_config.agents['DeepCodeAgent'].agent_descriptor.model if 'DeepCodeAgent' in agent_config.agents.keys() else None,
                          [call_a_friend],
                          self.SYSTEM_INSTRUCTION)
        self.agent_config: AgentCardItem = agent_config.agents['DeepCodeAgent'] \
            if 'DeepCodeAgent' in agent_config.agents.keys() else None

    def invoke(self, query, sessionId) -> str:
        config = {"configurable": {"thread_id": sessionId}}
        self.graph.invoke({"messages": [("user", query)]}, config)
        return self.get_agent_response(config)

    async def stream(self, query, sessionId) -> AsyncIterable[Dict[str, Any]]:
        return self.stream_agent_response_graph(query, sessionId, self.graph)

    def get_agent_response(self, config):
        return self.get_agent_response_graph(config, self.graph)


    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]


@component()
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