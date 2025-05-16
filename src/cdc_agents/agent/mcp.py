import abc
import typing
from pydantic import BaseModel

McpSchemaT = typing.TypeVar("McpSchemaT", bound=BaseModel, covariant=True)

class McpAgent(abc.ABC, typing.Generic[McpSchemaT]):

    @property
    @abc.abstractmethod
    def mcp_agent_schema(self) -> typing.Type[McpSchemaT]:
        pass

    def to_mcp_schema(self) -> dict[str, typing.Any]:
        return self.mcp_agent_schema.model_json_schema()
