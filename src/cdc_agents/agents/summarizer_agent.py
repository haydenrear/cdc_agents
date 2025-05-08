from typing import Any, Dict, AsyncIterable

import injector
from langchain_core.messages import BaseMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import MessagesState

from cdc_agents.agent.agent import A2AReactAgent
from cdc_agents.agent.a2a import A2AAgent
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
        An agent that summarizes the information to be provided. Used when there is too much data in the context to 
        provide to the agent, and then this information can be summarized or compactified so as to reduce the burden
        on the next agents. 
        """

    def do_collapse(self, message_state: list[BaseMessage], config) -> list[BaseMessage]:
        """
        This agent would return a collapsed message, summarizing all messages previously. So then the graph provides
        all messages including and up to that one. In this case, the SummarizerAgent retrieves the messages to be kept
        from the summarization message.
        :param config:
        :param message_state: all messages in the graph
        :return: the messages to exist in the graph after applying summarization - naively would pop the last.
        """
        return message_state

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

