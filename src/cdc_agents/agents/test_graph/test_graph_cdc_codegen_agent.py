import typing
import injector
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agent.agent import A2AAgent, A2AReactAgent
from cdc_agents.agent.agent_orchestrator import TestGraphOrchestrated
from cdc_agents.agents.cdc_server_agent import CdcCodegenAgent, CdcServerAgentToolCallProvider
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
from cdc_agents.config.cdc_server_config_props import CdcServerConfigProps
from cdc_agents.model_server.model_provider import ModelProvider
from python_di.configs.autowire import injectable
from python_di.configs.component import component


@component(bind_to=[A2AAgent, A2AReactAgent, TestGraphOrchestrated])
@injectable()
class TestGraphCdcCodegenAgent(CdcCodegenAgent, TestGraphOrchestrated):
    """
    TestGraph variant of CdcCodegenAgent specialized for test_graph integration workflows.
    Focuses on generating test code, test configurations, and test-specific implementations.
    """

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver,
                 model_provider: ModelProvider, cdc_server: CdcServerConfigProps,
                 tool_call_provider: CdcServerAgentToolCallProvider):
        self_card: AgentCardItem = agent_config.agents[self.__class__.__name__]
        CdcCodegenAgent.__init__(self, agent_config, memory_saver, model_provider, cdc_server, tool_call_provider)
        TestGraphOrchestrated.__init__(self, self_card)

