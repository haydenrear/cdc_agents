import unittest

from cdc_agents.agent.agent_server import AgentServerRunner
from cdc_agents.agents.deep_code_research_agent import DeepCodeOrchestrator
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
    code: DeepCodeOrchestrator

    @test_inject()
    @autowire_fn()
    def construct(self,
                  ai_suite: AgentConfigProps,
                  deep_code_orchestrator: DeepCodeOrchestrator):
        AgentConfigPropsTest.ai_suite = ai_suite
        AgentConfigPropsTest.code = deep_code_orchestrator

    def test_deep_code_injection(self):
        assert self.ai_suite
        assert self.code
        assert self.code.agents
        assert len(self.code.agents) != 0


