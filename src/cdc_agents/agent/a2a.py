import abc
import re
import time
import typing

from langgraph.graph.state import CompiledStateGraph
from langchain_core.messages import BaseMessage
from langchain_core.runnables import AddableDict
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agent.response_format_parser import (
    ResponseFormatParser, ResponseFormatBuilder, MessageTypeResponseFormatParser,
    StatusResponseFormatParser, NextAgentResponseFormatParser,
    AdditionalContextResponseFormatParser, StatusValidationResponseFormatParser
)
from cdc_agents.common.server import TaskManager
from cdc_agents.common.types import Message, ResponseFormat, AgentGraphResponse, AgentGraphResult, WaitStatusMessage
from cdc_agents.config.agent_config_props import AgentMcpTool
from python_di.inject.profile_composite_injector.inject_context_di import InjectionDescriptor, InjectionType, \
    autowire_fn
from python_util.logger.logger import LoggerFacade

class BaseAgent(abc.ABC):

    @abc.abstractmethod
    def invoke(self, query, sessionId) -> typing.Union[AddableDict, ResponseFormat, AgentGraphResponse]:
        pass

    @property
    @abc.abstractmethod
    def agent_name(self) -> str:
        pass

    @property
    def terminal_string(self) -> str:
        return "completed"

    @property
    def completed(self) -> str:
        return "completed"

    @property
    def next_agent(self) -> str:
        return "goto_agent"

    @property
    def needs_input_string(self) -> str:
        return "input_required"

    @property
    def has_error_string(self) -> str:
        return "error"

    def is_terminate_node(self, last_message: AgentGraphResult, state) -> bool:
        return last_message.is_task_complete

    def message_contains(self, last_message, answer) -> bool:
        return answer in last_message.content or any([answer in c for c in last_message.content])

class A2AAgent(BaseAgent, abc.ABC):
    def __init__(self, model=None, tools=None, system_instruction=None,
                 memory: MemorySaver = MemorySaver(), content_types = None,
                 response_parsers: typing.Optional[typing.List[ResponseFormatParser]] = None):
        self._content_types = content_types if content_types is not None else ['text', 'text/plain']
        self.task_manager: typing.Optional[TaskManager] = None
        self.model = model
        self.tools = tools
        self.system_instruction = system_instruction
        self.memory = memory
        self._agent_name = self.__class__.__name__
        self.AWAITING_RX = re.compile(
            r"""^.*?                          # any leading junk (non-greedy)
        status_message\s*:\s*        # literal key (flexible spacing)
        awaiting\s+input\s+for\s+    # fixed phrase
        (?P<agent>[^\r\n]+?)         # capture agent name (greedy to EOL)
        \s*$                         # allow trailing spaces
        """,
            re.IGNORECASE | re.VERBOSE | re.MULTILINE,
            )

        # Initialize response format parsers - use injected parsers if available, otherwise default ones
        self._response_parsers = response_parsers or [
            MessageTypeResponseFormatParser(),
            StatusResponseFormatParser(),
            NextAgentResponseFormatParser(),
            AdditionalContextResponseFormatParser(),
            StatusValidationResponseFormatParser()
        ]

    def peek_to_process_task(self, session_id) -> typing.Optional[Message]:
        if not self.task_manager:
            return None
        return self.task_manager.peek_to_process_task(session_id)

    def pop_to_process_task(self, session_id) -> typing.Optional[Message]:
        if not self.task_manager:
            return None
        return self.task_manager.pop_to_process_task(session_id)

    def set_task_manager(self, task_manager: TaskManager):
        self.task_manager = task_manager

    @property
    def supported_content_types(self) -> list[str]:
        return self._content_types

    @property
    def agent_name(self) -> str:
        return self._agent_name

    @abc.abstractmethod
    def stream(self, query, sessionId, graph=None):
        pass

    @abc.abstractmethod
    def get_agent_response(self, config, graph):
        pass

    def add_mcp_tools(self, props, additional_tools: typing.Optional[typing.Dict[str, AgentMcpTool]] = None, loop = None):
        """
        MCP tools are descriptors of external tools for a particular agent to use.
        Append these tools to the list of tools available for this particular agent.
        :param additional_tools: tools to be appended
        :param loop: used mostly for testing ???
        :return:
        """
        pass

    async def add_mcp_tools_async(self, props, additional_tools: typing.Optional[typing.Dict[str, AgentMcpTool]] = None, loop = None):
        """
        MCP tools are descriptors of external tools for a particular agent to use.
        Append these tools to the list of tools available for this particular agent.
        :param additional_tools: tools to be appended
        :param loop: used mostly for testing ???
        :return:
        """
        pass

    def get_status_message(self, message: BaseMessage) -> typing.Optional[WaitStatusMessage]:
        content = message.content
        if isinstance(content, list):
            for next_message_content in reversed(content):
                f = self._get_status_message(next_message_content)
                if f:
                    return f
        elif isinstance(content, str):
            return self._get_status_message(content)

        return None

    def _get_status_message(self, raw):
        try:
            matches = list(self.AWAITING_RX.finditer(raw))
            if not matches or len(matches) == 0:
                return None

            return WaitStatusMessage(agent_route=matches[-1].group("agent").strip())
        except Exception as e:
            LoggerFacade.error(f"Found error with status message: {e}")


    def get_agent_response_graph(self, config, graph) -> AgentGraphResponse:
        current_state = graph.get_state(config)
        return self._do_get_res(current_state.values)

    @autowire_fn(descr={
        'parsers': InjectionDescriptor(injection_ty=InjectionType.Dependency),
        'values': InjectionDescriptor(injection_ty=InjectionType.Provided),
        'is_completed': InjectionDescriptor(injection_ty=InjectionType.Provided)
    })
    def _do_get_res(self, values, is_completed = None,
                    parsers: typing.List[ResponseFormatParser] = None):
        messages = values.get('messages')
        last_message: BaseMessage = messages[-1]

        # Use injected parsers if available, otherwise use instance parsers
        active_parsers = parsers if parsers is not None else self._response_parsers

        # Sort parsers by ordering
        sorted_parsers = sorted(active_parsers, key=lambda p: p.ordering())

        # Initialize builder
        builder = ResponseFormatBuilder()

        # Apply all parsers in order
        for parser in sorted_parsers:
            builder = parser.parse(builder, last_message, values)

        # Build the final response format
        structured_response = builder.build()

        # Determine task completion status
        is_task_completed = structured_response.status == self.completed
        if is_completed is not None:
            is_task_completed = is_completed
        elif builder.is_tool_message:
            is_task_completed = True

        if structured_response and isinstance(structured_response, ResponseFormat):
            if structured_response.status == self.needs_input_string:
                return AgentGraphResponse(**{
                    "is_task_complete": is_task_completed,
                    "require_user_input": True,
                    "content": structured_response
                })
            elif structured_response.status == self.has_error_string:
                return AgentGraphResponse(**{
                    "is_task_complete": is_task_completed,
                    "require_user_input": True,
                    "content": structured_response
                })
            elif structured_response.status == self.completed:
                return AgentGraphResponse(**{
                    "is_task_complete": is_task_completed,
                    "require_user_input": False,
                    "content": structured_response
                })
            elif structured_response.status == self.next_agent:
                return AgentGraphResponse(**{
                    "is_task_complete": is_task_completed,
                    "require_user_input": False,
                    "content": structured_response
                })

        return AgentGraphResponse(**{
            "is_task_complete": is_task_completed,
            "require_user_input": True,
            "content": "We are unable to process your request at the moment. Please try again.",
        })

    def stream_agent_response_graph(self, query, sessionId, graph: CompiledStateGraph):
        inputs = TaskManager.get_user_query_message(query, sessionId)
        config = {"configurable": {"thread_id": sessionId, 'checkpoint_time': time.time_ns()}}

        for item in graph.stream(inputs, config, stream_mode="values"):
            config['configurable']['checkpoint_time'] = time.time_ns()
            if 'messages' in item.keys() and len(item['messages']) == 1 and item['messages'][0].content == query:
                found =  self._do_get_res(item, False)
                yield found
            else:
                res =  self._do_get_res(item)
                yield res
