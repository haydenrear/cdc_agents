import abc
import dataclasses
import typing
from typing import Optional, Any

import injector
from langchain_core.language_models import LanguageModelInput, LanguageModelOutput
from langchain_core.messages import BaseMessage, MessageLikeRepresentation
from langchain_core.prompt_values import PromptValue
from langchain_core.runnables import Runnable, RunnableConfig
from pydantic import BaseModel

from aisuite.framework import ChatCompletionResponse
from cdc_agents.config.model_server_config_props import ModelServerConfigProps, ModelServerModelProps
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

class ModelServerExecutor(abc.ABC):

    @abc.abstractmethod
    def __call__(self, model_server_input: ModelServerInput, *args, **kwargs) -> typing.Union[ChatCompletionResponse, str]:
        pass

    @property
    @abc.abstractmethod
    def config_props(self) -> ModelServerConfigProps:
        pass

@component(bind_to=[ModelServerExecutor], profile='test', scope=profile_scope)
@injectable()
class LoggingModelServerExecutor(ModelServerExecutor):

    @property
    def config_props(self) -> ModelServerConfigProps:
        return self._model_props

    @injector.inject
    def __init__(self, model_props: ModelServerConfigProps):
        self._model_props = model_props

    def __call__(self, model_server_input: ModelServerInput, *args, **kwargs) -> typing.Union[ChatCompletionResponse, str]:
        LoggerFacade.info("Called model server executor")
        return "hello!"

@component(bind_to=[ModelServerExecutor], profile='main_profile', scope=profile_scope)
@injectable()
class RestModelServerExecutor(ModelServerExecutor):

    @injector.inject
    def __init__(self, model_props: ModelServerConfigProps):
        self._model_props = model_props

    def __call__(self, model_server_input: ModelServerInput, *args, **kwargs) -> typing.Union[ChatCompletionResponse, str]:
        pass

    @property
    def config_props(self) -> ModelServerConfigProps:
        return self._model_props

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
        return [Message(content=parse_content(in_value), role=parse_role(in_value))]
    elif isinstance(in_value, PromptValue):
        return [m for f in in_value.to_messages() for m in parse_to_message(f)]
    elif isinstance(in_value, BaseMessage):
        return [Message(content=parse_content(in_value))]
    elif isinstance(in_value, MessageLikeRepresentation):
        return [Message(content=parse_content(in_value))]
    elif isinstance(in_value, list | tuple):
        return [m for f in in_value for m in parse_to_message(f)]


@prototype_scope_bean()
class ModelServerModel(Runnable[LanguageModelInput, LanguageModelOutput]):

    @prototype_factory()
    def __init__(self,
                 model_server_config_props: ModelServerConfigProps,
                 executor: ModelServerExecutor,
                 model_props: ModelServerModelProps):
        self.executor = executor
        self.model_props = model_props
        self.model_server_config_props = model_server_config_props

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


    @classmethod
    def convert_to_language_model_output(cls,
                                         model_input: typing.Union[ChatCompletionResponse, str],
                                         config: Optional[RunnableConfig], **kwargs: Any) -> typing.Optional[LanguageModelOutput]:
        if isinstance(model_input, str):
            return model_input
        else:
            return BaseMessage(content=[c.message.content for c in model_input.choices])

    def invoke(self, model_input: LanguageModelInput,
               config: Optional[RunnableConfig] = None, **kwargs: Any) -> LanguageModelOutput:
        executed_on_model_server = self.executor(self.convert_to_model_server(model_input, config))
        return self.convert_to_language_model_output(executed_on_model_server, config)