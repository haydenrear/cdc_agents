from typing import Any, Dict, AsyncIterable

import injector
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agent.agent import A2AAgent, A2AReactAgent
from cdc_agents.agents.deep_code_research_agent import DeepResearchOrchestrated
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
from cdc_agents.model_server.model_provider import ModelProvider
from python_di.configs.autowire import injectable
from python_di.configs.component import component
from langchain_core.tools import tool


# @component(bind_to=[DeepResearchOrchestrated, A2AAgent, A2AReactAgent])
# @injectable()
class SummarizerAgent(DeepResearchOrchestrated, A2AReactAgent):

    SYSTEM_INSTRUCTION = (
        """
        """
    )

    # @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver, model_provider: ModelProvider):
        A2AReactAgent.__init__(self,agent_config,
                          [], self.SYSTEM_INSTRUCTION, memory_saver, model_provider)

    @property
    def orchestrator_prompt(self):
        return """
        An agent that facilitates the running of the code after making code changes, to validate code changes with respect
        for particular tickets, bug changes, or any other unit of work.
        """

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

