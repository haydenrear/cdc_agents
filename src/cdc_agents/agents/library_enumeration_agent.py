from typing import Any, Dict, AsyncIterable

import injector
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agent.agent import A2AReactAgent
from cdc_agents.agent.a2a import A2AAgent
from cdc_agents.agents.deep_code_research_agent import DeepResearchOrchestrated
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


@component(bind_to=[DeepResearchOrchestrated, A2AAgent, A2AReactAgent])
@injectable()
class LibraryEnumerationAgent(DeepResearchOrchestrated, A2AReactAgent):

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver, model_provider: ModelProvider):
        self_card: AgentCardItem = agent_config.agents[self.__class__.__name__]
        DeepResearchOrchestrated.__init__(self, self_card)
        A2AReactAgent.__init__(self,
                          agent_config,
                          [search_github_for_sources, search_gitlab_for_sources],
                          self_card.agent_descriptor.system_instruction, memory_saver, model_provider)

    @property
    def orchestrator_prompt(self):
        return """
        An agent that identifies important dependencies in the repository to be included in the code search when including
        code and code history in the context, and returns a mechanism for how those dependencies can be downloaded to be 
        used in the downstream tasks. 
        """


