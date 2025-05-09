import abc
import dataclasses
import json
import re
import typing
from typing import AsyncIterable, Dict, Any

import regex
from langchain_core.messages import BaseMessage

import asyncio
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import AddableDict
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.common.server import TaskManager
from cdc_agents.common.types import Message, ResponseFormat, AgentGraphResponse, AgentGraphResult, WaitStatusMessage
from cdc_agents.config.agent_config_props import AgentMcpTool
from python_util.logger.logger import LoggerFacade


class BaseAgent(abc.ABC):

    @abc.abstractmethod
    def invoke(self, query, sessionId) -> typing.Union[AddableDict, ResponseFormat]:
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
        return "next_agent"

    @property
    def needs_input_string(self) -> str:
        return "input_needed"

    @property
    def has_error_string(self) -> str:
        return "error"

    def is_terminate_node(self, last_message: AgentGraphResult, state) -> bool:
        return last_message.is_task_complete

    def message_contains(self, last_message, answer) -> bool:
        return answer in last_message.content or any([answer in c for c in last_message.content])

class A2AAgent(BaseAgent, abc.ABC):
    def __init__(self, model=None, tools=None, system_instruction=None,
                 memory: MemorySaver = MemorySaver()):
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

    def peek_to_process_task(self, session_id) -> typing.Optional[Message]:
        if not self.task_manager:
            return None
        return asyncio.get_event_loop().run_until_complete(self.task_manager.peek_to_process_task(session_id))

    def pop_to_process_task(self, session_id) -> typing.Optional[Message]:
        if not self.task_manager:
            return None
        return asyncio.get_event_loop().run_until_complete(self.task_manager.pop_to_process_task(session_id))

    def set_task_manager(self, task_manager: TaskManager):
        self.task_manager = task_manager

    @property
    def supported_content_types(self) -> list[str]:
        if not hasattr(self, 'SUPPORTED_CONTENT_TYPES'):
            raise NotImplementedError("Could not find supported content.")

        return getattr(self, 'SUPPORTED_CONTENT_TYPES')

    @property
    def agent_name(self) -> str:
        return self._agent_name

    @abc.abstractmethod
    async def stream(self, query, sessionId, graph=None) -> AsyncIterable[Dict[str, Any]]:
        pass

    @abc.abstractmethod
    def get_agent_response(self, config, graph):
        pass

    def add_mcp_tools(self, additional_tools: typing.Dict[str, AgentMcpTool] = None, loop = None):
        """
        MCP tools are descriptors of external tools for a particular agent to use.
        Append these tools to the list of tools available for this particular agent.
        :param additional_tools: tools to be appended
        :param loop: used mostly for testing ???
        :return:
        """
        pass

    async def add_mcp_tools_async(self, additional_tools: typing.Dict[str, AgentMcpTool] = None, loop = None):
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
        messages = current_state.values.get('messages')

        last_message: BaseMessage = messages[-1]
        content = ''.join([c for c in last_message.content])

        STATUS_RX = re.compile(
            r"""^[\ufeff\s]*          # optional BOM + leading whitespace
             status\s*:\s*                   # literal header key (allow extra spaces)
            (?P<state>[A-Za-z_]+)            # capture the value
            \s*$                             # ignore anything after the value on this line
            """,
            re.IGNORECASE | re.VERBOSE | re.MULTILINE,
        )

        match = STATUS_RX.search(content)

        if match:
            status_token = match.group("state")
            header_end = content.find("\n", match.end())  # first newline after the header we matched
            content = content[header_end + 1 :] if header_end != -1 else ""
            structured_response = ResponseFormat(status=status_token, message=content, history=messages, route_to=content if status_token == self.next_agent else None)
        else:
            try:
                if isinstance(content, dict):
                    loaded = content
                else:
                    loaded = json.loads(content)
                structured_response = ResponseFormat(**loaded)
            except:
                structured_response = ResponseFormat(status=self.completed, message=content, history=messages)

        if structured_response and isinstance(structured_response, ResponseFormat):
            if structured_response.status == self.needs_input_string:
                return AgentGraphResponse(**{
                    "is_task_complete": False,
                    "require_user_input": True,
                    "content": structured_response
                })
            elif structured_response.status == self.has_error_string:
                return AgentGraphResponse(**{
                    "is_task_complete": False,
                    "require_user_input": True,
                    "content": structured_response
                })
            elif structured_response.status == self.completed:
                return AgentGraphResponse(**{
                    "is_task_complete": True,
                    "require_user_input": False,
                    "content": structured_response
                })
            elif structured_response.status == self.next_agent:
                return AgentGraphResponse(**{
                    "is_task_complete": False,
                    "require_user_input": False,
                    "content": structured_response
                })

        return AgentGraphResponse(**{
            "is_task_complete": False,
            "require_user_input": True,
            "content": "We are unable to process your request at the moment. Please try again.",
        })

    @staticmethod
    async def stream_agent_response_graph(query, sessionId, graph) -> AsyncIterable[Dict[str, Any]]:
        inputs = {"messages": [("user", query)]}
        config = {"configurable": {"thread_id": sessionId}}

        for item in graph.stream(inputs, config, stream_mode="values"):
            message = item["messages"][-1]
            if (
                    isinstance(message, AIMessage)
                    and message.tool_calls
                    and len(message.tool_calls) > 0
            ):
                yield {
                    "is_task_complete": False,
                    "require_user_input": False,
                    "content": "Looking up the exchange rates...",
                }
            elif isinstance(message, ToolMessage):
                yield {
                    "is_task_complete": False,
                    "require_user_input": False,
                    "content": "Processing the exchange rates..",
                }
