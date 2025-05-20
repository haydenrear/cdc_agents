import abc
import dataclasses
import enum

import pydantic
from langgraph.graph.state import CompiledStateGraph
import json
import re
import typing
from typing import AsyncIterable, Dict, Any

import regex
from langchain_core.messages import BaseMessage

import asyncio
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage
from langchain_core.runnables import AddableDict
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.common.server import TaskManager
from cdc_agents.common.types import Message, ResponseFormat, AgentGraphResponse, AgentGraphResult, WaitStatusMessage
from cdc_agents.config.agent_config_props import AgentMcpTool
from python_util.logger.logger import LoggerFacade
from pydantic import BaseModel

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
                 memory: MemorySaver = MemorySaver(), content_types = None):
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

        self.STATUS_RX = re.compile(
            r"""^.*?
            STATUS\s*:\s*
            (?P<state>[A-Za-z_]+)
            \s*$
            """,
            re.IGNORECASE | re.VERBOSE | re.MULTILINE)

        self.NEXT_AGENT_RX = re.compile(r"NEXT AGENT\s*:\s*(?P<state>[A-Za-z0-9_]+)", re.IGNORECASE)

        self.ADDITIONAL_CTX_RX = re.compile(r"ADDITIONAL CONTEXT\s*:\s*(?P<state>.*)", re.IGNORECASE)

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
        return self._do_get_res(current_state.values)

    def _do_get_res(self, values, is_completed = None):
        messages = values.get('messages')
        last_message: BaseMessage = messages[-1]
        content = ''.join([c for c in last_message.content])

        content = content.replace('**', '')

        match = self.STATUS_RX.search(content)

        if match:
            status_token = self._do_get_match_group(match)
            if status_token == 'skip':
                status_token = self.completed
            if status_token == 'input_needed':
                status_token = self.needs_input_string
            header_end = content.find("\n", match.end())  # first newline after the header we matched
            content = content[header_end + 1:] if header_end != -1 else ""
            agent = None
            additional_ctx = None
            match_agent = None
            match_ctx = None
            for c in content.splitlines():
                if match_agent is None:
                    match_agent = self.NEXT_AGENT_RX.search(c)
                    if match_agent is not None:
                        agent = self._do_get_match_group(match_agent)
                        if agent == 'skip':
                            agent = None
                if match_ctx is None:
                    match_ctx = self.ADDITIONAL_CTX_RX.search(c)
                    if match_ctx is not None:
                        additional_ctx = self._do_get_match_group(match_ctx)
                else:
                    additional_ctx += '\n'
                    additional_ctx += c

            content = additional_ctx
            structured_response = ResponseFormat(status=status_token, message=content, history=messages,
                                                 route_to=agent)
        else:
            try:
                if isinstance(content, dict):
                    content = json.dumps(content)
                    structured_response = ResponseFormat(message=content, history=messages, status=self.completed)
                else:
                    structured_response = ResponseFormat(status=self.completed, message=str(content), history=messages)
            except Exception as e:
                structured_response = ResponseFormat(status=self.completed, message=str(content), history=messages)

        is_task_completed = structured_response.status == self.completed

        if is_completed is not None:
            is_task_completed = is_completed

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

    def _do_get_match_group(self, match):
        status_token = match.group("state")
        if status_token is not None:
            status_token = status_token.strip()
        return status_token

    def stream_agent_response_graph(self, query, sessionId, graph: CompiledStateGraph):
        inputs = TaskManager.get_user_query_message(query, sessionId)
        config = {"configurable": {"thread_id": sessionId}}

        for item in graph.stream(inputs, config, stream_mode="values"):
            if 'messages' in item.keys() and len(item['messages']) == 1 and item['messages'][0].content == query:
                found =  self._do_get_res(item, False)
                yield found
            else:
                res =  self._do_get_res(item)
                yield res

