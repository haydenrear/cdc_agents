import unittest.mock
import uuid

from langchain_core.messages import ToolMessage
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agents.deep_code_research_agent import DeepCodeOrchestrator
from cdc_agents.agents.test_graph.test_graph_agent_orchestrator import TestGraphOrchestrator
from cdc_agents.config.agent_config import AgentConfig
from cdc_agents.config.agent_config_props import AgentConfigProps
from cdc_agents.model_server.model_provider import ModelProvider
from cdc_agents.model_server.model_server_model import ModelServerModel
from cdc_agents_test.fixtures.agent_fixtures import (
    create_test_orchestrator, TestA2AAgent, TestOrchestratorAgent
)
from python_di.configs.bean import test_inject
from python_di.configs.test import test_booter, boot_test
from python_di.inject.profile_composite_injector.inject_context_di import autowire_fn


@test_booter(scan_root_module=AgentConfig)
class ServerRunnerBoot:
    pass

@boot_test(ctx=ServerRunnerBoot)
class TestGraphOrchestratorTest(unittest.IsolatedAsyncioTestCase):
    ai_suite: AgentConfigProps
    server: TestGraphOrchestrator
    model: ModelServerModel
    memory: MemorySaver
    model_provider: ModelProvider


    @test_inject(profile='test')
    @autowire_fn(profile='test')
    def construct(self,
                  ai_suite: AgentConfigProps,
                  server: TestGraphOrchestrator,
                  model: ModelServerModel,
                  memory_saver: MemorySaver,
                  model_provider: ModelProvider):
        TestGraphOrchestratorTest.memory = memory_saver
        TestGraphOrchestratorTest.ai_suite = ai_suite
        TestGraphOrchestratorTest.server = server
        TestGraphOrchestratorTest.model = model
        TestGraphOrchestratorTest.model_provider = model_provider

    def test_inject(self):
        assert self.server