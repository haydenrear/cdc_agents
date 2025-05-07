import logging
import os.path
import sys
import unittest
from unittest.mock import patch

from cdc_agents.agent.agent_server import AgentServerRunner
from cdc_agents.agents.cdc_server_agent import CdcCodegenAgent
from cdc_agents.common.types import TaskEventBody
from cdc_agents.config.agent_config import AgentConfig
from cdc_agents.config.agent_config_props import AgentConfigProps
from python_di.configs.bean import test_inject
from python_di.configs.test import test_booter, boot_test
from python_di.inject.profile_composite_injector.inject_context_di import autowire_fn
from python_util.logger.log_level import LogLevel

LogLevel.set_log_level(logging.DEBUG)

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
        self.ai_suite = ai_suite
        self.server = server

    def test_agent_config_props(self):
        assert self.ai_suite
        assert self.server
        assert self.server.agent_config_props


    def test_model_event_body(self):
        evt = TaskEventBody(**{"body_value":{"hello": "goodbye", "what": {"okay": "goodbye"}, "okay": ["what!"]}, "session_id": "whatever_sess"})
        assert evt.body_value["hello"] == "goodbye"
        assert evt.body_value["okay"] == ["what!"]
        assert evt.body_value["what"]["okay"] == "goodbye"
        evt = TaskEventBody(**{"body_value": "whatev", "session_id": "whatever_sess"})
        assert evt.body_value == "whatev"
