import typing
import injector
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agent.agent import A2AAgent, A2AReactAgent
from cdc_agents.agent.agent_orchestrator import TestGraphOrchestrated
from cdc_agents.agents.human_delegate_agent import HumanDelegateAgent
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
from cdc_agents.config.cdc_server_config_props import CdcServerConfigProps
from cdc_agents.config.human_delegate_config_props import HumanDelegateConfigProps
from cdc_agents.model_server.model_provider import ModelProvider
from cdc_agents.tools.tool_call_decorator import ToolCallDecorator
from python_di.configs.autowire import injectable
from python_di.configs.component import component


@component(bind_to=[A2AAgent, A2AReactAgent, TestGraphOrchestrated])
@injectable()
class TestGraphHumanDelegateAgent(HumanDelegateAgent, TestGraphOrchestrated):
    """
    TestGraph variant of HumanDelegateAgent specialized for test_graph integration workflows.
    Focuses on delegating test validation, test result review, and manual test execution to humans.
    """

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver, model_provider: ModelProvider,
                 cdc_server: HumanDelegateConfigProps):
        self_card: AgentCardItem = agent_config.agents[self.__class__.__name__]
        HumanDelegateAgent.__init__(self, agent_config, memory_saver, model_provider, cdc_server)
        TestGraphOrchestrated.__init__(self, self_card)


