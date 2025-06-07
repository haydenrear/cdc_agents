import typing
import injector
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agent.agent import A2AAgent, A2AReactAgent
from cdc_agents.agent.agent_orchestrator import TestGraphOrchestrated
from cdc_agents.agents.library_enumeration_agent import LibraryEnumerationAgent
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
from cdc_agents.model_server.model_provider import ModelProvider
from python_di.configs.autowire import injectable
from python_di.configs.component import component


@component(bind_to=[A2AAgent, A2AReactAgent, TestGraphOrchestrated])
@injectable()
class TestGraphLibraryEnumerationAgent(LibraryEnumerationAgent, TestGraphOrchestrated):
    """
    TestGraph variant of LibraryEnumerationAgent specialized for test_graph integration workflows.
    Focuses on discovering and enumerating test libraries, testing frameworks, and test dependencies.
    """

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver, model_provider: ModelProvider):
        self_card: AgentCardItem = agent_config.agents[self.__class__.__name__]
        LibraryEnumerationAgent.__init__(self, agent_config, memory_saver, model_provider)
        TestGraphOrchestrated.__init__(self, self_card)

