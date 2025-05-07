import abc
import typing
from typing import AsyncIterable, Dict, Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Interrupt

from cdc_agents.common.server import TaskManager
from cdc_agents.common.types import  Message
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

    def pop_task_history(self, session_id) -> typing.Optional[Message]:
        t = self.task_manager.task(session_id)
        if t and len(t.history) != 0:
            return t.history.pop(0)

        return None

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
