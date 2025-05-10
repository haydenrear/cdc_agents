import unittest

from starlette.applications import Starlette

import asyncio
import copy
import json
import logging
import typing
import unittest
import unittest.mock
import unittest.mock
import uuid
from typing import Any

from langchain_core.callbacks import Callbacks
from langchain_core.messages import ToolMessage, HumanMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import BaseTool, tool
from langchain_core.tools import StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

from aisuite.framework import ChatCompletionResponse
from cdc_agents.agent.agent import A2AReactAgent
from cdc_agents.agent.agent_orchestrator import OrchestratorAgent, OrchestratedAgent
from cdc_agents.agent.agent_server import AgentServerRunner
from cdc_agents.agent.task_manager import AgentTaskManager
from cdc_agents.agents.deep_code_research_agent import DeepCodeOrchestrator
from cdc_agents.config.agent_config import AgentConfig
from cdc_agents.config.agent_config_props import AgentConfigProps
from cdc_agents.config.model_server_config_props import ModelServerConfigProps
from cdc_agents.model_server.model_provider import ModelProvider
from cdc_agents.model_server.model_server_model import ModelServerModel, ModelServerInput
from drools_py.configs.config import ConfigType
from python_di.configs.bean import test_inject
from python_di.configs.test import test_booter, boot_test
from python_di.inject.profile_composite_injector.composite_injector import profile_scope
from python_di.inject.profile_composite_injector.inject_context_di import autowire_fn
from python_util.logger.log_level import LogLevel
from python_util.logger.logger import LoggerFacade

LogLevel.set_log_level(logging.DEBUG)

@test_booter(scan_root_module=AgentConfig)
class ServerRunnerBoot:
    pass

@boot_test(ctx=ServerRunnerBoot)
class A2AServerTest(unittest.TestCase):
    ai_suite: AgentConfigProps
    server: DeepCodeOrchestrator
    model: ModelServerModel
    memory: MemorySaver
    model_provider: ModelProvider
    server_runner: AgentServerRunner
    starlette: Starlette

    @test_inject(profile='test', scope=profile_scope)
    @autowire_fn(profile='test', scope_decorator=profile_scope)
    def construct(self,
                  ai_suite: AgentConfigProps,
                  server: DeepCodeOrchestrator,
                  model: ModelServerModel,
                  memory_saver: MemorySaver,
                  model_provider: ModelProvider,
                  server_runner: AgentServerRunner,
                  starlette: Starlette):
        A2AServerTest.starlette = starlette
        A2AServerTest.server_runner = server_runner
        A2AServerTest.memory = memory_saver
        A2AServerTest.ai_suite = ai_suite
        A2AServerTest.server = server
        A2AServerTest.model = model
        A2AServerTest.model_provider = model_provider

    def test_inject(self):
        assert self.starlette
        assert self.server_runner
        assert self.memory
        assert self.ai_suite
        assert self.server
        assert self.model
        assert self.model_provider
        assert isinstance(self.server_runner.starlette, unittest.mock.MagicMock)

    def test_receive_a2a_invoke(self):
        pass

    def test_receive_a2a_invoke_orchestrator_needs_input_invoke_again(self):
        pass

    def test_receive_a2a_invoke_inner_agent_needs_input_invoke_again(self):
        pass

    def test_concurrent_execution_add_history_invoke(self):
        pass

    def test_stream_video_file(self):
        pass

    def test_invalid_session_id(self):
        pass

    def test_push_notification(self):
        pass

    def test_stream_agent(self):
        pass

    def test_stream_agent_deny_concurrent_execution(self):
        pass

    def test_stream_agent_add_history(self):
        pass

    def test_postgres_checkpointer_concurrent_execution(self):
        """
        The TaskManager must be made to be a postgres repository in this case, and need distributed lock stripes.
        :return:
        """
        pass