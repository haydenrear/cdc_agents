import unittest

from cdc_agents.agent.agent_server import AgentServerRunner
from cdc_agents.config.agent_config import AgentConfig
from cdc_agents.config.agent_config_props import AgentConfigProps
from python_di.configs.bean import test_inject
from python_di.configs.test import test_booter, boot_test
from python_di.inject.profile_composite_injector.inject_context_di import autowire_fn

@test_booter(scan_root_module=AgentConfig)
class ServerRunnerBoot:
    pass

@boot_test(ctx=ServerRunnerBoot)
class AgentConfigPropsTest(unittest.TestCase):

    ai_suite: AgentConfigProps
    server: AgentServerRunner

    @test_inject()
    @autowire_fn()
    def construct(self,
                  ai_suite: AgentConfigProps,
                  server: AgentServerRunner):
        AgentConfigPropsTest.ai_suite = ai_suite
        AgentConfigPropsTest.server = server

    def test_agent_config_props(self):
        assert self.ai_suite
        assert self.server
        assert self.server.agent_config_props


