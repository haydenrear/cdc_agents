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
def bootstrap_ai_character():
    """
    """
    pass

@tool
def message_human_delegate():
    """
    """
    pass

@tool
def check_human_delegate_messages():
    """
    """
    pass

@tool
def read_human_delegate_screen():
    """
    :return:
    """
    pass

@component(bind_to=[DeepResearchOrchestrated, A2AAgent, A2AReactAgent])
@injectable()
class HumanDelegateAgent(DeepResearchOrchestrated, A2AReactAgent):

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver, model_provider: ModelProvider):
        self_card: AgentCardItem = agent_config.agents[self.__class__.__name__]
        DeepResearchOrchestrated.__init__(self, self_card)
        A2AReactAgent.__init__(self, agent_config,
                               [bootstrap_ai_character, message_human_delegate, check_human_delegate_messages],
                               self_card.agent_descriptor.system_instruction, memory_saver, model_provider)
        self.agent_config: AgentCardItem = self_card

    @property
    def orchestrator_prompt(self):
        return """
        An agent that facilitates communication with human representatives, such as refining ticket or business requirements. 
        """


