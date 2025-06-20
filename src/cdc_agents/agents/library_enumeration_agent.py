from typing import Any, Dict, AsyncIterable

import injector
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agent.agent import A2AReactAgent
from cdc_agents.agent.a2a import A2AAgent
from cdc_agents.agent.agent_orchestrator import DeepResearchOrchestrated
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
from cdc_agents.model_server.model_provider import ModelProvider
from python_di.configs.autowire import injectable
from python_di.configs.component import component
from langchain_core.tools import tool


@tool
def search_github_for_sources():
    """
    """
    pass

@tool
def search_gitlab_for_sources():
    """
    """
    pass


class LibraryEnumerationBaseAgent(A2AReactAgent):
    """Base library enumeration agent that can be orchestrated by different orchestration types."""

    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver, model_provider: ModelProvider, orchestration_type: type):
        self_card: AgentCardItem = agent_config.agents[self.__class__.__name__]
        orchestration_type.__init__(self, self_card)
        A2AReactAgent.__init__(self,
                          agent_config,
                          [],
                          self_card.agent_descriptor.system_prompts, memory_saver, model_provider)


@component(bind_to=[DeepResearchOrchestrated, A2AAgent, A2AReactAgent])
@injectable()
class LibraryEnumerationAgent(LibraryEnumerationBaseAgent, DeepResearchOrchestrated):

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver, model_provider: ModelProvider):
        super().__init__(agent_config, memory_saver, model_provider, DeepResearchOrchestrated)
