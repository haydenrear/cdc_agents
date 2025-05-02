import logging
import unittest

from cdc_agents.config.agent_config import AgentConfig
from cdc_agents.config.agent_config_props import AgentConfigProps
from cdc_agents.model_server.model_server_model import ModelServerModel, LoggingModelServerExecutor
from python_di.configs.bean import test_inject
from python_di.configs.test import test_booter, boot_test
from python_di.inject.profile_composite_injector.inject_context_di import autowire_fn
from python_util.logger.log_level import LogLevel

LogLevel.set_log_level(logging.DEBUG)

@test_booter(scan_root_module=AgentConfig)
class ServerRunnerBoot:
    pass

@boot_test(ctx=ServerRunnerBoot)
class ModelServerModelTest(unittest.TestCase):
    ai_suite: AgentConfigProps
    server: ModelServerModel

    @test_inject(profile='test')
    @autowire_fn(profile='test')
    def construct(self,
                  ai_suite: AgentConfigProps,
                  server: ModelServerModel):
        self.ai_suite = ai_suite
        self.server = server

    def test_model_server_model(self):
        assert self.server is not None
        assert self.server.executor is not None
        assert isinstance(self.server.executor, LoggingModelServerExecutor)
        assert self.server.executor.config_props is not None
        assert self.server.model_server_config_props is not None
        assert self.server.model_server_config_props.host is not None
        assert self.server.model_server_config_props.port is not None

        found = self.server.invoke("hello")
        assert found == "hello!"


