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


# @component(bind_to=[DeepResearchOrchestrated, A2AAgent, A2AReactAgent])
# @injectable()
class CodeRunnerAgent(DeepResearchOrchestrated, A2AReactAgent):

    SYSTEM_INSTRUCTION = (
        """
        You are a specialized assistant for running source code to test changes. You have access to various tools to 
        run the code, such as Docker, Git, and the file system. If you do not have enough information to run the code,
        then you can ask for more information. Otherwise, using the information provided to you, run the code and 
        provide feedback about the changes, such as by loading the log.
        """
    )

    # @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver, model_provider: ModelProvider):
        A2AReactAgent.__init__(self,agent_config,[], self.SYSTEM_INSTRUCTION,
                               memory_saver, model_provider)

    @property
    def orchestrator_prompt(self):
        return """
        An agent that facilitates the running of the code after making code changes, to validate code changes with respect
        for particular tickets, bug changes, or any other unit of work.
        """

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

