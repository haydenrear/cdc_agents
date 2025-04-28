import abc
from typing import Any, Dict, AsyncIterable, Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel

memory = MemorySaver()

class ResponseFormat(BaseModel):
    """Respond to the user in this format."""
    status: Literal["input_required", "completed", "error"] = "input_required"
    message: str

class A2AAgent(abc.ABC):

    def __init__(self, model, tools, system_instruction):
        self.model = model
        self.tools = tools
        self.system_instruction = system_instruction
        self.graph = create_react_agent(
            self.model, tools=self.tools, checkpointer=memory, prompt = self.system_instruction, response_format=ResponseFormat
        )
        self.agent_name = str(self.__class__)

    @abc.abstractmethod
    def invoke(self, query, sessionId) -> str:
        pass

    @abc.abstractmethod
    async def stream(self, query, sessionId) -> AsyncIterable[Dict[str, Any]]:
        pass

    @abc.abstractmethod
    def get_agent_response(self, config):
        pass

