import logging
import typing
import unittest
import unittest.mock
from typing import Any, AsyncIterable, Dict

from langchain.agents import create_react_agent
from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import BaseMessage, ToolMessage, HumanMessage
from langchain_core.prompt_values import PromptValue, ChatPromptValue
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import BaseTool, tool
from langgraph.graph.state import CompiledStateGraph

from aisuite.framework import ChatCompletionResponse
from cdc_agents.agent.agent import A2AAgent, OrchestratedAgent, A2AOrchestratorAgent
from cdc_agents.agents.deep_code_research_agent import call_a_friend, DeepCodeOrchestrator
from cdc_agents.config.agent_config import AgentConfig
from cdc_agents.config.agent_config_props import AgentConfigProps
from cdc_agents.config.model_server_config_props import ModelServerConfigProps
from cdc_agents.model_server.model_server_model import ModelServerModel, LoggingModelServerExecutor, \
    ModelServerExecutor, ModelServerInput
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
    server: DeepCodeOrchestrator
    model: ModelServerModel


    @test_inject(profile='test')
    @autowire_fn(profile='test')
    def construct(self,
                  ai_suite: AgentConfigProps,
                  server: DeepCodeOrchestrator,
                  model: ModelServerModel):
        ModelServerModelTest.ai_suite = ai_suite
        ModelServerModelTest.server = server
        ModelServerModelTest.model = model


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

        self._mock_executor_call()

        class TestAgent(A2AAgent) :
            async def stream(self, query, sessionId, graph=None) -> AsyncIterable[Dict[str, Any]]:
                pass

            def get_agent_response(self, config, graph):
                pass

            def invoke(self, query, sessionId) -> str:
                found = self.graph.invoke(query)
                return found

        class TestOrchestratorAgent(A2AOrchestratorAgent) :
            async def stream(self, query, sessionId, graph=None) -> AsyncIterable[Dict[str, Any]]:
                pass

            def get_agent_response(self, config, graph):
                pass

            def invoke(self, query, sessionId) -> str:

                i = self.graph.invoke(query)
                return i


        k = next(iter(self.server.agents))[0]
        self.server.get_agent_response = self._agent_response
        self.server.agents.clear()
        self.server.orchestrator_agent = TestOrchestratorAgent(self.model, [call_a_friend_in], "test")
        self.server.agents[k] = OrchestratedAgent(TestAgent(self.model, [call_a_friend_in], "test"))
        invoked = self.server.invoke("hello", "test")

        assert len(invoked) != 0
        assert any([isinstance(i, ToolMessage) for i in invoked])
        assert any([i.content[-1] == 'okay' for i in invoked if isinstance(i, HumanMessage)])
        assert any([i.content == 'hello...' for i in invoked if isinstance(i, ToolMessage)])
        assert any([i.content[-1] == 'FINAL ANSWER: hello!' for i in invoked if isinstance(i, HumanMessage)])

        assert invoked[-1].content[-1] == 'FINAL ANSWER: hello!'

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
            "okay",
            "FINAL ANSWER: hello!"
        ]
        self.model.executor = Executor()
        self.model.executor.call = mock

    def _agent_response(self, *args, **kwargs):
        c: CompiledStateGraph = args[1]
        state = c.get_state(args[0])
        return state.values.get('messages')
