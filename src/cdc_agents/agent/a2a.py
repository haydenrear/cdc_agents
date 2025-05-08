import abc
import typing
from typing import AsyncIterable, Dict, Any

import asyncio
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.common.server import TaskManager
from cdc_agents.common.types import Message
from cdc_agents.config.agent_config_props import AgentMcpTool


class BaseAgent(abc.ABC):

    @abc.abstractmethod
    def invoke(self, query, sessionId):
        pass

    @property
    @abc.abstractmethod
    def agent_name(self) -> str:
        pass

    @property
    def terminal_string(self) -> str:
        return "FINAL ANSWER"

    @property
    def completed(self) -> str:
        return "completed"

    @property
    def needs_input_string(self) -> str:
        return "input_needed"

    @property
    def has_error_string(self) -> str:
        return "error"

    def is_terminate_node(self, last_message, state) -> bool:
        return self.message_contains(last_message, self.terminal_string)

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

    def get_agent_response_graph(self, config, graph):
        current_state = graph.get_state(config)
        structured_response = current_state.values.get('messages')
        from cdc_agents.agent.agent import ResponseFormat
        if structured_response and isinstance(structured_response, ResponseFormat):
            if structured_response.status == self.needs_input_string:
                return {
                    "is_task_complete": False,
                    "require_user_input": True,
                    "content": structured_response.message
                }
            elif structured_response.status == self.has_error_string:
                return {
                    "is_task_complete": False,
                    "require_user_input": True,
                    "content": structured_response.message
                }
            elif structured_response.status == self.completed:
                return {
                    "is_task_complete": True,
                    "require_user_input": False,
                    "content": structured_response.message
                }

        return {
            "is_task_complete": False,
            "require_user_input": True,
            "content": "We are unable to process your request at the moment. Please try again.",
        }

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
