import typing
import injector
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agent.agent import A2AAgent, A2AReactAgent
from cdc_agents.agent.agent_orchestrator import TestGraphOrchestrated
from cdc_agents.agents.cdc_server_agent import BaseCdcCodeSearchAgent, CdcServerAgentToolCallProvider
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
from cdc_agents.config.cdc_server_config_props import CdcServerConfigProps
from cdc_agents.model_server.model_provider import ModelProvider
from python_di.configs.autowire import injectable
from python_di.configs.component import component


@component(bind_to=[A2AAgent, A2AReactAgent, TestGraphOrchestrated])
@injectable()
class TestGraphCdcCodeSearchAgent(BaseCdcCodeSearchAgent, TestGraphOrchestrated):
    """
    TestGraph variant of CdcCodeSearchAgent specialized for test_graph integration workflows.
    Focuses on searching test code, test configurations, and test-related artifacts.
    """

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver, model_provider: ModelProvider,
                 cdc_server: CdcServerConfigProps, tool_call_provider: CdcServerAgentToolCallProvider):
        BaseCdcCodeSearchAgent.__init__(self, agent_config, memory_saver, model_provider, cdc_server, tool_call_provider, TestGraphOrchestrated)
