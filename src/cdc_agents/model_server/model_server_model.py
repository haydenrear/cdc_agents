import abc
import dataclasses
import json
import threading
import typing
from typing import Optional, Any

import injector
from langchain.agents.output_parsers import ReActSingleInputOutputParser, JSONAgentOutputParser
from langchain_core.agents import AgentAction
from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import LanguageModelInput, LanguageModelOutput, BaseChatModel
from langchain_core.language_models.base import LanguageModelOutputVar
from langchain_core.messages import BaseMessage, MessageLikeRepresentation, AIMessage, ToolCall
from langchain_core.outputs import ChatGenerationChunk, ChatResult
from langchain_core.prompt_values import PromptValue
from langchain_core.runnables import Runnable, RunnableConfig, RunnableSerializable
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from aisuite.framework import ChatCompletionResponse
from aisuite.framework.choice import Choice
from cdc_agents.common.types import ToolCallJson, ToolCallAdapter
from cdc_agents.config.agent_config_props import AgentCardItem
from cdc_agents.config.model_server_config_props import ModelServerConfigProps, ModelServerModelProps
from cdc_agents.model_server.language_model_input_parser import LanguageModelOutputParser
from python_di.configs.autowire import injectable
from python_di.configs.component import component
from python_di.configs.prototype import prototype_scope_bean, prototype_factory
from python_di.inject.profile_composite_injector.composite_injector import profile_scope
from python_util.logger.logger import LoggerFacade


class ModelServerInput(BaseModel, abc.ABC):
    pass

class Message(BaseModel):
    content: str
    role: str = "system"

class RerankDocument(BaseModel):
    text: str
    metadata: typing.Dict[str, Any]

class RerankBody(BaseModel):
    query: str
    docs: typing.List[RerankDocument]

class ModelServerRerankInput(ModelServerInput):
    rerank_body: typing.List[Message]

class ModelServerChatInput(ModelServerInput):
    messages: typing.List[Message]

class ModelServerEmbedInput(ModelServerInput):
    to_embed: str
    model: str

class ModelServerValidationEndpoint(ModelServerInput):
    to_embed: str
    model: str

class ModelServerExecutor(BaseModel, abc.ABC):

    @abc.abstractmethod
    def call(self, model_server_input: ModelServerInput,
                 tools: typing.Optional[typing.Sequence[typing.Union[typing.Dict[str, Any], type, typing.Callable, BaseTool]]] = None,
                 *args, **kwargs) -> typing.Union[ChatCompletionResponse, str]:
        pass

    @abc.abstractmethod
    def get_config_props(self) -> ModelServerConfigProps:
        pass

@component(bind_to=[ModelServerExecutor], profile='test', scope=profile_scope)
@injectable()
class LoggingModelServerExecutor(ModelServerExecutor):

    config_props: ModelServerConfigProps

    @property
    def get_config_props(self) -> ModelServerConfigProps:
        return self.config_props

    @injector.inject
    def __init__(self, model_props: ModelServerConfigProps):
        BaseModel.__init__(self, config_props=model_props)

    def call(self, model_server_input: ModelServerInput,
                 tools: typing.Optional[typing.Sequence[typing.Union[typing.Dict[str, Any], type, typing.Callable, BaseTool]]] = None,
                 *args, **kwargs) -> typing.Union[ChatCompletionResponse, str]:
        LoggerFacade.info("Called model server executor")
        if isinstance(model_server_input, ModelServerChatInput):
            return ChatCompletionResponse.create_completion_response([
                Choice.create_choice(Message(content=c.content.replace("Action", "")))
                for c in model_server_input.messages])
        else:
            return "hello!"

@component(bind_to=[ModelServerExecutor], profile='main_profile', scope=profile_scope)
@injectable()
class RestModelServerExecutor(ModelServerExecutor):

    config_props: ModelServerConfigProps

    @injector.inject
    def __init__(self, model_props: ModelServerConfigProps):
        BaseModel.__init__(self, config_props=model_props)

    def call(self, model_server_input: ModelServerInput,
                 tools: typing.Optional[typing.Sequence[typing.Union[typing.Dict[str, Any], type, typing.Callable, BaseTool]]] = None,
                 *args, **kwargs) -> typing.Union[ChatCompletionResponse, str]:
        pass

    @property
    def get_config_props(self) -> ModelServerConfigProps:
        return self.config_props

def parse_role(in_value: typing.Union[PromptValue, str, dict[str, Any], BaseMessage, MessageLikeRepresentation]) -> str:
    if isinstance(in_value, str):
        return "system"
    if isinstance(in_value, dict) and "role" in in_value.keys() and in_value["role"] and len(in_value["role"]) != 0:
        return in_value["role"]

    return "system"

def parse_content(in_value: typing.Union[PromptValue, str, dict[str, Any], BaseMessage, MessageLikeRepresentation]) -> str:
    if hasattr(in_value, 'content'):
        return getattr(in_value, 'content')
    if isinstance(in_value, dict) and "content" in in_value.keys() and in_value["content"] and len(in_value["content"]) != 0:
        return in_value["content"]

    return in_value

def parse_to_message(in_value: typing.Union[PromptValue, str, dict[str, Any], BaseMessage, MessageLikeRepresentation]) -> typing.Optional[typing.List[Message]]:
    if isinstance(in_value, str):
        return [Message(content=in_value)]
    elif isinstance(in_value, typing.Dict):
        return _to_messages(parse_content(in_value), parse_role(in_value))
    elif isinstance(in_value, PromptValue):
        return [m for f in in_value.to_messages() for m in parse_to_message(f)]
    elif isinstance(in_value, BaseMessage):
        return _to_messages(parse_content(in_value), parse_role(in_value))
    elif isinstance(in_value, MessageLikeRepresentation):
        return _to_messages(parse_content(in_value), parse_role(in_value))
    elif isinstance(in_value, list | tuple):
        return [m for f in in_value for m in parse_to_message(f)]

def _to_messages(content, role2):
    if isinstance(content, list):
        return [Message(content=m, role=role2) for m in content]
    return [Message(content=content, role=role2)]

bind_tools_lock = threading.RLock()

@prototype_scope_bean()
class ModelServerModel(BaseChatModel, Runnable[LanguageModelInput, LanguageModelOutputVar]):

    config_props: ModelServerConfigProps
    executor: ModelServerExecutor
    model_props: typing.Optional[ModelServerModelProps] = None
    bound_tools: typing.Optional[typing.Sequence[typing.Union[typing.Dict[str, Any], type, BaseTool]]] = None
    tool_choice: typing.Optional[str] = None
    tool_call_schema: typing.Any = None

    __parsers__: typing.List[LanguageModelOutputParser]

    @prototype_factory()
    def __init__(self,
                 model_server_config_props: ModelServerConfigProps,
                 executor: ModelServerExecutor,
                 model_props: ModelServerModelProps,
                 parsers: typing.List[LanguageModelOutputParser],
                 tools: typing.Optional[typing.Sequence[typing.Union[typing.Dict[str, Any], type, BaseTool]]] = None,
                 tool_choice: typing.Optional[str] = None,
                 tool_call_schema: typing.Optional[typing.Any] = ToolCallJson):
        BaseChatModel.__init__(self, config_props=model_server_config_props, executor=executor, model_props=model_props,
                               bound_tools=tools, tool_choice=tool_choice)
        self.__parsers__ = sorted(parsers, key=lambda p: p.ordering())
        self.tool_call_schema = tool_call_schema
        self.executor = executor
        self.model_props = model_props
        self.config_props = model_server_config_props
        self.bound_tools = tools
        self.tool_choice = tool_choice
        self.__agent_card__ = None

    def initialize(self, agent_card: AgentCardItem):
        self.__agent_card__ = agent_card

    @injector.synchronized(bind_tools_lock)
    def invoke(self, model_input: LanguageModelInput,
               config: Optional[RunnableConfig] = None, **kwargs: Any) -> LanguageModelOutput:
        executed_on_model_server = self.executor.call(self.convert_to_model_server(model_input, config))
        out = self.convert_to_language_model_output(executed_on_model_server, config)
        return out

    @injector.synchronized(bind_tools_lock)
    def bind_tools(
            self,
            tools: typing.Sequence[typing.Union[typing.Dict[str, Any], type, BaseTool]],
            *,
            tool_choice: Optional[typing.Union[str]] = None,
            **kwargs: Any,
    ) -> Runnable[LanguageModelInput, BaseMessage]:
        """Bind tools to the model.

        Args:
            tools: Sequence of tools to bind to the model.
            tool_choice: The tool to use. If "any" then any tool can be used.

        Returns:
            A Runnable that returns a message.
        """
        if self.bound_tools is not None:
            if tools != self.bound_tools:
                LoggerFacade.debug(f"Attempted to rebind tools for {self}")

        self.bound_tools = tools
        self.tool_choice = tool_choice

        assert not self.tool_choice or self.tool_choice.lower() == "any", \
            ("tool choice should be either Any or None at this point. "
             "Future state is return immutable new ModelServerModel each time if this changes.")

        return self

    @injector.synchronized(bind_tools_lock)
    def _stream(
            self,
            messages: list[BaseMessage],
            stop: Optional[list[str]] = None,
            run_manager: Optional[CallbackManagerForLLMRun] = None,
            **kwargs: Any,
    ) -> typing.Iterator[ChatGenerationChunk]:
        raise NotImplementedError

    @property
    def _llm_type(self) -> str:
        raise NotImplementedError

    def _generate(self, messages: list[BaseMessage], stop: Optional[list[str]] = None,
                  run_manager: Optional[CallbackManagerForLLMRun] = None, **kwargs: Any) -> ChatResult:
        raise NotImplementedError

    @classmethod
    def convert_to_model_server(cls,
                                model_input: LanguageModelInput,
                                config: Optional[RunnableConfig], **kwargs: Any) -> typing.Optional[ModelServerInput]:
        if isinstance(model_input, str):
            return ModelServerChatInput(messages=parse_to_message(model_input))
        elif isinstance(model_input, PromptValue):
            return ModelServerChatInput(messages = [m for f in model_input.to_messages() for m in parse_to_message(f)])
        elif isinstance(model_input, typing.Sequence):
            return ModelServerChatInput(messages = [m for f in model_input for m in parse_to_message(f)])

    def convert_to_language_model_output(self,
                                         model_input: typing.Union[ChatCompletionResponse, str],
                                         config: Optional[RunnableConfig], **kwargs: Any) -> typing.Optional[LanguageModelOutput]:
        tools_list = []
        content_list = []
        for i, m in enumerate(self.__parsers__):
            if isinstance(model_input, ChatCompletionResponse):
                choices_values = [s.message.content for s in model_input.choices]
                self._deconstruct_add_ai_values(choices_values, content_list, m, model_input, tools_list)
            elif isinstance(model_input, typing.List):
                self._deconstruct_add_ai_values(model_input, content_list, m, model_input, tools_list)
            else:
                llm_out = m.do_convert(model_input)
                if not llm_out:
                    continue
                tools, content = m.deconstruct_ai_messages(model_input, llm_out)
                if tools:
                    tools_list.extend(tools)
                if content:
                    content_list.extend(content)

        return LanguageModelOutputParser.convert_to_ai_response(content_list, tools_list, config)


    def _deconstruct_add_ai_values(self, choices_values, content_list, m, model_input, tools_list):
        for s in choices_values:
            llm_out = m.do_convert(s)
            if not llm_out:
                continue

            tools, content = m.deconstruct_ai_messages(model_input, llm_out)
            if tools:
                tools_list.extend(tools)
            if content:
                content_list.extend(content)