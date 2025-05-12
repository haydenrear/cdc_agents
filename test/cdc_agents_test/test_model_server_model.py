import logging
import typing
import unittest
import unittest.mock
from typing import Any
from langchain_core.tools import tool

from langchain.agents import create_react_agent
from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import BaseMessage
from langchain_core.prompt_values import PromptValue, ChatPromptValue
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import BaseTool

from aisuite.framework import ChatCompletionResponse
from cdc_agents.config.agent_config import AgentConfig
from cdc_agents.config.agent_config_props import AgentConfigProps
from cdc_agents.config.model_server_config_props import ModelServerConfigProps
from cdc_agents.model_server.model_server_model import ModelServerModel, LoggingModelServerExecutor, \
    ModelServerExecutor, ModelServerInput
from python_di.configs.bean import test_inject
from python_di.configs.test import test_booter, boot_test
from python_di.inject.profile_composite_injector.inject_context_di import autowire_fn
from python_util.logger.log_level import LogLevel


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
        ModelServerModelTest.ai_suite = ai_suite
        ModelServerModelTest.server = server

    def test_model_server_model(self):
        assert self.server is not None
        assert self.server.executor is not None
        assert isinstance(self.server.executor, LoggingModelServerExecutor)
        assert self.server.executor.config_props is not None
        assert self.server.config_props is not None
        assert self.server.config_props.host is not None
        assert self.server.config_props.port is not None

        test_ = {'configurable': {'thread_id': 'test'}}
        found = self.server.invoke("hello", test_)
        assert found.content == ["hello"]

        message = BaseMessage(content="whatever", type="chat")
        found = self.server.invoke(ChatPromptValue(messages=[message]), test_)
        assert found.content == ["whatever"]

        message = BaseMessage(content="ok", type="chat")
        found = self.server.invoke([message], test_)
        assert found.content == ["ok"]

        message = BaseMessage(content="ok", type="chat")
        message_w = BaseMessage(content="do", type="chat")
        found = self.server.invoke([message, message_w], test_)
        assert found.content == ["ok", "do"]

    def test_with_react_agent(self):
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

        class Executor:

            def call(self, model_server_input: ModelServerInput, tools: typing.Optional[
                typing.Sequence[typing.Union[typing.Dict[str, Any], type, typing.Callable, BaseTool]]] = None, *args,
                     **kwargs) -> typing.Union[ChatCompletionResponse, str]:
                pass

            def get_config_props(self) -> ModelServerConfigProps:
                pass
        @tool
        def message_human_delegate():
            """
            """
            pass

        self.server.executor = Executor()
        self.server.executor.call = unittest.mock.MagicMock(return_value="""
        Action: message_human_delegate
        Action Input: 
        """)
        agent = create_react_agent(self.server, [message_human_delegate],
                                   prompt=PromptTemplate.from_template(
                                       template,
                                       partial_variables={"tools": [message_human_delegate], "agent_scratchpad": "",
                                                          "input": "???"}))

        test_ = {'configurable': {'thread_id': 'test'}}
        a = agent.invoke({"content": "hello!", "intermediate_steps": []}, test_)
        assert a