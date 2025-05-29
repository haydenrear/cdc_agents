from langgraph.graph import MessagesState
import uuid
import warnings
from collections.abc import Sequence
from functools import partial
from typing import (
    Annotated,
    Any,
    Callable,
    Literal,
    Optional,
    Union,
    cast,
)

from langgraph.graph.message import add_messages

from langchain_core.messages import (
    AnyMessage,
    BaseMessage,
    BaseMessageChunk,
    MessageLikeRepresentation,
    RemoveMessage,
    convert_to_messages,
    message_chunk_to_message,

)
from typing_extensions import TypedDict

from langgraph.graph.state import StateGraph

class AgentState(MessagesState):
    messages: Annotated[list[AnyMessage], add_messages]
    session_id: str
