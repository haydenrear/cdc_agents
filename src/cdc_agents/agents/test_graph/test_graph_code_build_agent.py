import typing
import injector
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agent.agent import A2AAgent, A2AReactAgent
from cdc_agents.agent.agent_orchestrator import TestGraphOrchestrated
from cdc_agents.agents.code_build_agent import CodeBuildAgent
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
from cdc_agents.config.cdc_server_config_props import CdcServerConfigProps
from cdc_agents.model_server.model_provider import ModelProvider
from cdc_agents.tools.tool_call_decorator import ToolCallDecorator
from python_di.configs.autowire import injectable
from python_di.configs.component import component


@component(bind_to=[A2AAgent, A2AReactAgent, TestGraphOrchestrated])
@injectable()
class TestGraphCodeBuildAgent(CodeBuildAgent, TestGraphOrchestrated):
    """
    TestGraph variant of CodeBuildAgent specialized for test_graph integration workflows.
    Focuses on building test code, test dependencies, and test-specific artifacts.
    """

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver, model_provider: ModelProvider,
                 cdc_server: CdcServerConfigProps, tool_call_decorator: ToolCallDecorator):
        self_card: AgentCardItem = agent_config.agents[self.__class__.__name__]
        CodeBuildAgent.__init__(self, agent_config, memory_saver, model_provider, cdc_server, tool_call_decorator)
        TestGraphOrchestrated.__init__(self, self_card)

    @property
    def agent_name(self) -> str:
        return self.__class__.__name__

