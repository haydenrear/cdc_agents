import unittest.mock

from langchain_core.messages import ToolMessage
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agents.deep_code_research_agent import DeepCodeOrchestrator
from cdc_agents.common.server import TaskManager
from cdc_agents.common.types import ResponseFormat
from cdc_agents.config.agent_config import AgentConfig
from cdc_agents.config.agent_config_props import AgentConfigProps
from cdc_agents.model_server.model_provider import ModelProvider
from cdc_agents.model_server.model_server_model import ModelServerModel
from python_di.configs.bean import test_inject
from python_di.configs.test import test_booter, boot_test
from python_di.inject.profile_composite_injector.inject_context_di import autowire_fn


@test_booter(scan_root_module=AgentConfig)
class ServerRunnerBoot:
    pass

@boot_test(ctx=ServerRunnerBoot)
class ModelServerModelTest(unittest.IsolatedAsyncioTestCase):
    ai_suite: AgentConfigProps
    server: DeepCodeOrchestrator
    model: ModelServerModel
    memory: MemorySaver
    model_provider: ModelProvider


    @test_inject(profile='test')
    @autowire_fn(profile='test')
    def construct(self,
                  ai_suite: AgentConfigProps,
                  server: DeepCodeOrchestrator,
                  model: ModelServerModel,
                  memory_saver: MemorySaver,
                  model_provider: ModelProvider):
        ModelServerModelTest.memory = memory_saver
        ModelServerModelTest.ai_suite = ai_suite
        ModelServerModelTest.server = server
        ModelServerModelTest.model = model
        ModelServerModelTest.model_provider = model_provider


    # def test_git_status(self):
        # invoked = self.server.invoke(TaskManager.get_user_query_message('Please retrieve the git status of the repository in the directory /Users/hayde/IdeaProjects/drools',
        #                                                       'test'),
        #                              self.server._create_orchestration_config('test'))
        # assert invoked
        # assert isinstance(invoked.content, ResponseFormat)
        # assert any([isinstance(t, ToolMessage) and t.status == 'success' and t.name == 'git_status' for t in invoked.content.history])
