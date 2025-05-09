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
from cdc_agents.agent.task_manager import AgentTaskManager
from cdc_agents.agents.deep_code_research_agent import DeepCodeOrchestrator
from cdc_agents.config.agent_config import AgentConfig
from cdc_agents.config.agent_config_props import AgentConfigProps
from cdc_agents.config.model_server_config_props import ModelServerConfigProps
from cdc_agents.model_server.model_provider import ModelProvider
from cdc_agents.model_server.model_server_model import ModelServerModel, ModelServerInput
from python_di.configs.bean import test_inject
from python_di.configs.test import test_booter, boot_test
from python_di.inject.profile_composite_injector.inject_context_di import autowire_fn
from python_util.logger.log_level import LogLevel
from python_util.logger.logger import LoggerFacade

LogLevel.set_log_level(logging.DEBUG)

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

    def test_model_server_model(self):

        # TODO: could potentially bootstrap smaller agents with thoughts of larger agents using multishot
        #  Question, Thought, Question, Thought
        template = '''Answer the following questions as best you can
            Use the following format:

            Question: the input question you must answer
            Thought: you should always think about what to do
            Action: the action to take, should be one of [{tool_names}]
            Action Input: the input to the action
            Observation: the result of the action
            ... (this Thought/Action/Action Input/Observation can repeat N times)
            Thought: I now know the final answer
            Final Answer: the final answer to the original input question

            Begin!

            Question: {input}
            Thought:{agent_scratchpad}'''


        @tool
        def call_a_friend_in() -> str:
            """Call a human in the loop to validate we're moving the correct direction.

            Args:

            Returns:
                 str: called friend

            """
            return "hello..."

        model = self._mock_executor_call()

        class TestAgent(A2AReactAgent) :

            did_call = False

            def invoke(self, query, sessionId) -> str:
                TestAgent.did_call = True
                return A2AReactAgent.invoke(self, query, sessionId)

        class TestOrchestratorAgent(OrchestratorAgent):

            did_call = False

            def invoke(self, query, sessionId) -> str:
                TestOrchestratorAgent.did_call = True
                invoked_value =  A2AReactAgent.invoke(self, query, sessionId)
                return invoked_value


        server = copy.copy(self.server)
        server.agents = copy.copy(server.agents)
        # server.get_agent_response = self._agent_response
        server.agents.clear()

        in_ = [call_a_friend_in]
        server.orchestrator_agent = TestOrchestratorAgent(self.ai_suite, in_, "test", self.memory, self.model_provider, model)
        server.orchestrator_agent.add_mcp_tools(self.ai_suite.agents['CdcCodegenAgent'].mcp_tools, asyncio.get_event_loop())
        task_manager = AgentTaskManager(server.orchestrator_agent, None)
        server.orchestrator_agent.set_task_manager(task_manager)

        server.agents['TestAgent'] = OrchestratedAgent(TestAgent(self.ai_suite, in_, "test", self.memory, self.model_provider, model))
        server.agents['TestAgent'].agent.add_mcp_tools(self.ai_suite.agents['CdcCodegenAgent'].mcp_tools, asyncio.get_event_loop())
        task_manager = AgentTaskManager(server.agents['TestAgent'].agent, None)
        server.agents['TestAgent'].agent.set_task_manager(task_manager)

        server.graph = server._build_graph()

        task_manager = AgentTaskManager(server, None)
        server.set_task_manager(task_manager)

        graph_response = server.invoke("hello", "test")

        invoked = graph_response.content.history

        assert len(invoked) != 0
        assert any([isinstance(i, ToolMessage) and i.status == 'success' for i in invoked])
        assert any([i.content[-1] == 'okay' for i in invoked if isinstance(i, HumanMessage)])
        assert any([i.content == 'hello...' for i in invoked if isinstance(i, ToolMessage)])
        assert any([i.content[-1] == 'status: completed\nhello!' for i in invoked if isinstance(i, HumanMessage)])
        assert graph_response.is_task_complete

        assert invoked[-1].content[-1] == 'status: completed\nhello!'

        assert TestOrchestratorAgent.did_call
        assert TestAgent.did_call

        TestOrchestratorAgent.did_call = False
        TestAgent.did_call = False

        invoked_second = server.invoke("hello", "test").content.history
        assert TestOrchestratorAgent.did_call
        assert TestAgent.did_call
        assert len(invoked_second) > len(invoked)
        TestOrchestratorAgent.did_call = False
        TestAgent.did_call = False
        invoked_third = server.invoke("hello", "whatever").content.history
        assert TestOrchestratorAgent.did_call
        assert TestAgent.did_call
        assert len(invoked_third) <= len(invoked)

    def _mock_executor_call(self):
        class Executor:
            def call(self, model_server_input: ModelServerInput, tools: typing.Optional[
                typing.Sequence[typing.Union[typing.Dict[str, Any], type, typing.Callable, BaseTool]]] = None, *args,
                     **kwargs) -> typing.Union[ChatCompletionResponse, str]:
                pass

            def get_config_props(self) -> ModelServerConfigProps:
                pass

        mock = unittest.mock.MagicMock()
        mock.side_effect = [
            """
            Action: call_a_friend_in
            Action Input: 
            """,
            """
            Action: query
            Action Input: { "sql": "SELECT * FROM commit_diff" }
            """,
            "status: next_agent\nTestAgent",
            "okay",
            "status: completed\nhello!",
            """
            Action: call_a_friend_in
            Action Input: 
            """,
            "status: next_agent\nTestAgent",
            "okay",
            "status: completed\nhello!",
            """
            Action: call_a_friend_in
            Action Input: 
            """,
            "status: next_agent\nTestAgent",
            "okay",
            "status: completed\nhello!"
        ]
        model = copy.copy(self.model)
        model.executor = Executor()
        model.executor.call = mock
        return model

    # def _agent_response(self, *args, **kwargs):
    #     c: CompiledStateGraph = args[1]
    #     state = c.get_state(args[0])
    #     return state.values.get('messages')
