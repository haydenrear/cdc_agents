import abc
import json
import typing

import injector
from langchain.agents.output_parsers import ReActSingleInputOutputParser, JSONAgentOutputParser
from langchain_core.agents import AgentAction
from langchain_core.language_models import LanguageModelOutput
from langchain_core.messages import ToolCall, AIMessage

from aisuite.framework import ChatCompletionResponse
from python_di.configs.autowire import injectable
from python_di.configs.component import component

LlmOutput = typing.Optional[typing.List[typing.Union[ToolCall, str]]]

class LanguageModelOutputParser(abc.ABC):
    """
    There will be different parsers for different models, for instance...
    """

    def convert_llm_output(self, llm_output_to_parse) -> typing.Optional[LanguageModelOutput]:
        return self.parse_for_ai_message(llm_output_to_parse, self.do_convert(llm_output_to_parse))

    def ordering(self) -> int:
        return 0

    @abc.abstractmethod
    def do_convert(self, llm_output_to_parse: typing.Union[str]) -> LlmOutput:
        pass

    @classmethod
    def convert_to_ai_response(cls, content, tools=None) -> typing.Optional[LanguageModelOutput]:
        m = AIMessage(content=content)
        m.tool_calls = tools
        return m

    @classmethod
    def convert_to_ai_response_from(cls, content, tools=None) -> typing.Optional[LanguageModelOutput]:
        m = AIMessage(content=content)
        m.tool_calls = tools
        return m

    @classmethod
    def parse_for_ai_message(cls, original, converted: LlmOutput) -> typing.Optional[LanguageModelOutput]:
        if not converted:
            return cls.convert_to_ai_response(original)

        tools, content = cls.deconstruct_ai_messages(original, converted)
        return cls.convert_to_ai_response(content, tools)

    @classmethod
    def deconstruct_ai_messages(cls, original, converted: LlmOutput) -> typing.Tuple[typing.List[ToolCall], typing.List[typing.Any]]:
        tools = []
        content = []

        if isinstance(converted, list):
            for converted_item in converted:
                if cls.is_tool_response(converted_item):
                    tools.append(converted_item)
                elif converted_item is not None:
                    content.append(converted_item)

        return tools, content

    @classmethod
    def is_tool_response(cls, converted):
        return isinstance(converted, dict) and 'name' in converted.keys() and 'args' in converted.keys()

    @classmethod
    def parse_agent_action(cls, value: AgentAction) -> ToolCall:
        return ToolCall(name=value.tool, args={} if not value.tool_input or len(value.tool_input) == 0 else value.tool_input, id=''.join(value.lc_id()))


@component(bind_to=[LanguageModelOutputParser])
@injectable()
class JsonToolModelOutputParser(LanguageModelOutputParser):

    @injector.inject
    def __init__(self, json_parser: JSONAgentOutputParser):
        self.json_parser = json_parser

    def do_convert(self, llm_output_to_parse: typing.Union[str]) -> LlmOutput:
        if isinstance(llm_output_to_parse, str):
            try:
                return [self.parse_agent_action(self.json_parser.invoke(llm_output_to_parse))]
            except:
                pass


@component(bind_to=[LanguageModelOutputParser])
@injectable()
class ActionActionInputLanguageModelParser(LanguageModelOutputParser):

    @injector.inject
    def __init__(self, input_output_parser: ReActSingleInputOutputParser):
        self.input_output_parser = input_output_parser

    def do_convert(self, llm_output_to_parse: typing.Union[str]) -> LlmOutput:
        if isinstance(llm_output_to_parse, str):
            try:
                return [self.parse_agent_action(self.input_output_parser.invoke(llm_output_to_parse))]
            except:
                pass

@component(bind_to=[LanguageModelOutputParser])
@injectable()
class SimpleLanguageModelOutputModelParser(LanguageModelOutputParser):

    def do_convert(self, llm_output_to_parse: typing.Union[str]) -> LlmOutput:
        if isinstance(llm_output_to_parse, str):
            return [llm_output_to_parse]

    def ordering(self) -> int:
        return 100000

class ToolCallSchemaProvider(abc.ABC):

    @abc.abstractmethod
    def try_parse_from_tool_call_schema(self, value: dict) -> typing.Optional:
        pass

@component(bind_to=[ToolCallSchemaProvider])
@injectable()
class DefaultToolCallSchemaProvider(ToolCallSchemaProvider):

    def try_parse_from_tool_call_schema(self, value: dict) -> typing.Optional:
        return None


@component(bind_to=[LanguageModelOutputParser])
@injectable()
class ToolCallSchemaModelParser(LanguageModelOutputParser):

    @injector.inject
    def __init__(self, schema_provider: typing.List[ToolCallSchemaProvider] = None):
        self.schema_provider = schema_provider

    def do_convert(self, llm_output_to_parse: typing.Union[str]) -> LlmOutput:
        if isinstance(llm_output_to_parse, dict):
            for s in self.schema_provider:
                try:
                    s.try_parse_from_tool_call_schema(llm_output_to_parse)
                except:
                    continue
        try:
            loaded = json.loads(llm_output_to_parse)
            return self.do_convert(loaded)
        except:
            pass
