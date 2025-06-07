import abc
import enum
import os.path

from langchain_core.runnables import AddableDict
import typing
from typing import Union, Any, Literal

from langchain_core.messages import ToolCall
from pydantic import BaseModel, Field, TypeAdapter
from typing import Literal, List, Annotated, Optional
from datetime import datetime
from pydantic import model_validator, ConfigDict, field_serializer, field_validator
from uuid import uuid4
from enum import Enum
from typing_extensions import Self

from langchain_core.messages import BaseMessage
from langgraph.types import Interrupt

from python_util.io_utils.file_dirs import get_dir


class TaskState(str, Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    CANCELED = "canceled"
    FAILED = "failed"
    UNKNOWN = "unknown"


class TextPart(BaseModel):
    type: Literal["text"] = "text"
    text: str
    metadata: dict[str, Any] | None = None

class TaskHookMessage(BaseMessage):
    agent_name: str
    interrupt: Interrupt
    session_id: str

class FileContent(BaseModel):
    name: str | None = None
    mimeType: str | None = None
    bytes: str | None = None
    uri: str | None = None

    @model_validator(mode="after")
    def check_content(self) -> Self:
        if not (self.bytes or self.uri):
            raise ValueError("Either 'bytes' or 'uri' must be present in the file data")
        if self.bytes and self.uri:
            raise ValueError(
                "Only one of 'bytes' or 'uri' can be present in the file data"
            )
        return self


class FilePart(BaseModel):
    type: Literal["file"] = "file"
    file: FileContent
    metadata: dict[str, Any] | None = None


class DataPart(BaseModel):
    type: Literal["data"] = "data"
    data: dict[str, Any]
    metadata: dict[str, Any] | None = None

Part = Annotated[Union[TextPart, FilePart, DataPart], Field(discriminator="type")]

class Message(BaseModel):
    role: Literal["user", "agent"]
    parts: List[Part]
    metadata: dict[str, Any] | None = None
    agent_route: typing.Optional[str] = None

class TaskStatus(BaseModel):
    state: TaskState
    message: Message | None = None
    timestamp: datetime = Field(default_factory=datetime.now)

    @field_serializer("timestamp")
    def serialize_dt(self, dt: datetime, _info):
        return dt.isoformat()

class Artifact(BaseModel):
    name: str | None = None
    description: str | None = None
    parts: List[Part]
    metadata: dict[str, Any] | None = None
    index: int = 0
    append: bool | None = None
    lastChunk: bool | None = None


class Task(BaseModel):
    id: str
    sessionId: str | None = None
    status: TaskStatus
    artifacts: List[Artifact] | None = None
    history: List[Message] | None = None
    metadata: dict[str, Any] | None = None
    to_process: List[Message] | None = None

class AgentPosted(BaseModel):
    success: bool
    endpoint: str

class TaskStatusUpdateEvent(BaseModel):
    id: str
    status: TaskStatus
    final: bool = False
    metadata: dict[str, Any] | None = None


class TaskArtifactUpdateEvent(BaseModel):
    id: str
    artifact: Artifact
    metadata: dict[str, Any] | None = None


class AuthenticationInfo(BaseModel):
    model_config = ConfigDict(extra="allow")

    schemes: List[str]
    credentials: str | None = None


class PushNotificationConfig(BaseModel):
    url: str
    token: str | None = None
    authentication: AuthenticationInfo | None = None


class TaskIdParams(BaseModel):
    id: str
    metadata: dict[str, Any] | None = None

class TaskQueryParams(TaskIdParams):
    historyLength: int | None = None

class TaskSendParams(BaseModel):
    id: str
    sessionId: str = Field(default_factory=lambda: uuid4().hex)
    message: Message
    acceptedOutputModes: Optional[List[str]] = None
    pushNotification: PushNotificationConfig | None = None
    historyLength: int | None = None
    metadata: dict[str, Any] | None = None

class TaskPushNotificationConfig(BaseModel):
    id: str
    pushNotificationConfig: PushNotificationConfig

class JSONRPCMessage(BaseModel):
    jsonrpc: Literal["2.0"] = "2.0"
    id: int | str | None = Field(default_factory=lambda: uuid4().hex)

class JSONRPCRequest(JSONRPCMessage):
    method: str
    params: dict[str, Any] | None = None

class JSONRPCError(BaseModel):
    code: int
    message: str
    data: Any | None = None

class JSONRPCResponse(JSONRPCMessage):
    result: Any | None = None
    error: JSONRPCError | None = None

class SendTaskRequest(JSONRPCRequest):
    method: Literal["tasks/send"] = "tasks/send"
    params: TaskSendParams

class SendTaskResponse(JSONRPCResponse):
    result: Task | None = None

class SendTaskStreamingRequest(JSONRPCRequest):
    method: Literal["tasks/sendSubscribe"] = "tasks/sendSubscribe"
    params: TaskSendParams

class SendTaskStreamingResponse(JSONRPCResponse):
    result: TaskStatusUpdateEvent | TaskArtifactUpdateEvent | None = None

class GetTaskRequest(JSONRPCRequest):
    method: Literal["tasks/get"] = "tasks/get"
    params: TaskQueryParams

class GetTaskResponse(JSONRPCResponse):
    result: Task | None = None

class PostAgentResponse(JSONRPCResponse):
    result: AgentPosted | None = None

class CancelTaskRequest(JSONRPCRequest):
    method: Literal["tasks/cancel",] = "tasks/cancel"
    params: TaskIdParams

class CancelTaskResponse(JSONRPCResponse):
    result: Task | None = None

class SetTaskPushNotificationRequest(JSONRPCRequest):
    method: Literal["tasks/pushNotification/set",] = "tasks/pushNotification/set"
    params: TaskPushNotificationConfig

class SetTaskPushNotificationResponse(JSONRPCResponse):
    result: TaskPushNotificationConfig | None = None


class GetTaskPushNotificationRequest(JSONRPCRequest):
    method: Literal["tasks/pushNotification/get",] = "tasks/pushNotification/get"
    params: TaskIdParams

class GetTaskPushNotificationResponse(JSONRPCResponse):
    result: TaskPushNotificationConfig | None = None

class TaskResubscriptionRequest(JSONRPCRequest):
    method: Literal["tasks/resubscribe",] = "tasks/resubscribe"
    params: TaskIdParams

class ToolCallAdapter(BaseModel, abc.ABC):
    @abc.abstractmethod
    def to_tool_call(self) -> ToolCall:
        pass

class ToolCallJson(ToolCallAdapter):

    tool: str
    tool_input: typing.Dict[str, Any]

    def to_tool_call(self) -> ToolCall:
        return ToolCall(name=self.tool, args=self.tool_input, id=str(uuid4()))

A2ARequest = TypeAdapter(
    Annotated[
        Union[
            SendTaskRequest,
            GetTaskRequest,
            CancelTaskRequest,
            SetTaskPushNotificationRequest,
            GetTaskPushNotificationRequest,
            TaskResubscriptionRequest,
            SendTaskStreamingRequest,
        ],
        Field(discriminator="method"),
    ]
)

## Error types


class JSONParseError(JSONRPCError):
    code: int = -32700
    message: str = "Invalid JSON payload"
    data: Any | None = None


class InvalidRequestError(JSONRPCError):
    code: int = -32600
    message: str = "Request payload validation error"
    data: Any | None = None


class MethodNotFoundError(JSONRPCError):
    code: int = -32601
    message: str = "Method not found"
    data: None = None


class InvalidParamsError(JSONRPCError):
    code: int = -32602
    message: str = "Invalid parameters"
    data: Any | None = None


class InternalError(JSONRPCError):
    code: int = -32603
    message: str = "Internal error"
    data: Any | None = None


class TaskNotFoundError(JSONRPCError):
    code: int = -32001
    message: str = "Task not found"
    data: None = None


class TaskNotCancelableError(JSONRPCError):
    code: int = -32002
    message: str = "Task cannot be canceled"
    data: None = None


class PushNotificationNotSupportedError(JSONRPCError):
    code: int = -32003
    message: str = "Push Notification is not supported"
    data: None = None


class UnsupportedOperationError(JSONRPCError):
    code: int = -32004
    message: str = "This operation is not supported"
    data: None = None


class ContentTypeNotSupportedError(JSONRPCError):
    code: int = -32005
    message: str = "Incompatible content types"
    data: None = None

class AgentProvider(BaseModel):
    organization: str
    url: str | None = None

class AgentCapabilities(BaseModel):
    streaming: bool = False
    pushNotifications: bool = False
    receiveEvents: bool = False
    stateTransitionHistory: bool = False

class AgentAuthentication(BaseModel):
    schemes: List[str]
    credentials: str | None = None

class AgentSkill(BaseModel):
    id: str
    name: str
    description: str | None = None
    tags: List[str] | None = None
    examples: List[str] | None = None
    inputModes: List[str] | None = None
    outputModes: List[str] | None = None

class AgentCode(BaseModel):
    code: str
    py_file: str

class ModelDescriptor(BaseModel):
    model_name: str
    model_endpoint: str
    api_key: typing.Optional[str] = None
    headers: dict[str, str] = None

def read_from_file_if(name: str):
    if name.startswith('file://'):
        name = name.replace('file://', '')
        if not os.path.exists(name):
            name = os.path.join(os.environ['PROJ_HOME'], name)
        if not os.path.exists(name):
            raise ValueError(f"Could not find {name}")

        if not os.path.exists(name):
            name = get_dir(__file__, name)
        with open(name, 'r') as f:
            lines = f.readlines()
            out_lines = []
            found_start_prompt = False
            for line in lines:
                if line.strip() == '```prompt_markdown':
                    found_start_prompt = True
                elif found_start_prompt and line.strip() == '```':
                    break
                elif found_start_prompt:
                    out_lines.append(line)

            return '\n'.join(out_lines).strip()

    return name


class AgentDescriptor(BaseModel):
    model: typing.Union[str, ModelDescriptor]
    agent_name: str
    system_prompts: str = None
    tools: typing.List[str] = None
    orchestrated_prompts: str = None
    orchestrator_system_prompt: str = None
    completion_definition: str = None
    orchestrator_graph_agent_completion_prompt: str = None
    orchestrator_graph_agent_tool_completion_prompt: str = None
    orchestrator_propagator_prompt: str = None

    @field_validator('orchestrator_propagator_prompt')
    @classmethod
    def serialize_orchestrator_propagator_prompt(cls, v: typing.Any):
        return read_from_file_if(v)

    @field_validator('orchestrator_graph_agent_completion_prompt')
    @classmethod
    def serialize_orchestrator_graph_agent_completion_prompt(cls, v: typing.Any):
        return read_from_file_if(v)

    @field_validator('orchestrator_graph_agent_tool_completion_prompt')
    @classmethod
    def serialize_orchestrator_graph_agent_tool_completion_prompt(cls, v: typing.Any):
        return read_from_file_if(v)

    @field_validator('orchestrated_prompts')
    @classmethod
    def serialize_orchestrated_prompts(cls, v: typing.Any):
        return read_from_file_if(v)

    @field_validator('orchestrator_system_prompt')
    @classmethod
    def serialize_orchestrator_message(cls, v: typing.Any):
        return read_from_file_if(v)

    @field_validator('system_prompts')
    @classmethod
    def serialize_system_prompts(cls, v: typing.Any):
        return read_from_file_if(v)

    @field_validator('completion_definition')
    @classmethod
    def serialize_completion_definition(cls, v: typing.Any):
        return read_from_file_if(v)

AgentCardForward = typing.ForwardRef("AgentCard")

class AgentType(enum.Enum):
    LangChainReact = 0
    SmolAgents = 1

class AgentCard(BaseModel):
    name: str
    description: str | None = None
    path: str
    provider: AgentProvider | None = None
    version: str
    documentationUrl: str | None = None
    capabilities: AgentCapabilities | None = None
    authentication: AgentAuthentication | None = None
    defaultInputModes: List[str] = ["text"]
    defaultOutputModes: List[str] = ["text"]
    skills: List[AgentSkill] = []
    names_of_managed_agents: typing.List[str] = []
    managed_agents: typing.List[AgentCardForward] = []

class DiscoverAgents(BaseModel):
    agent_cards: typing.List[AgentCard] = []

class A2AClientError(Exception):
    pass

class A2AClientHTTPError(A2AClientError):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTP Error {status_code}: {message}")


class A2AClientJSONError(A2AClientError):
    def __init__(self, message: str):
        self.message = message
        super().__init__(f"JSON Error: {message}")


class MissingAPIKeyError(Exception):
    """Exception for missing API key."""

    pass


def aggregate_errs(res, results):
    errs = [r.error for r in results if r.error is not None]
    if len(errs) != 0:
        res['error'] = JSONRPCError(**{"code": 500, "message": ', '.join([e.message for e in errs]), "data": errs})


class ResponseFormat(BaseModel):
    """Respond to the user in this format."""
    status: Literal["input_required", "completed", "error", "goto_agent"] = "input_required"
    message: typing.Union[str, typing.List[BaseMessage], dict[str, typing.Any], typing.List[str], typing.Any] = None
    route_to: typing.Optional[str] = None
    history: typing.List[BaseMessage] = None

class AgentGraphResponse(BaseModel):
    is_task_complete: bool
    require_user_input: bool
    content: typing.Union[ResponseFormat, str, list[BaseMessage]]

class AgentGraphResult(BaseModel):
    is_task_complete: bool
    require_user_input: bool
    content: list[BaseMessage]
    last_message: typing.Optional[BaseMessage] = None
    agent_route: typing.Optional[str] = None

    def add_last_message(self, message: BaseMessage):
        self.content.append(message)

    def add_to_last_message(self, message: str):
        if not self.last_message.content:
            self.last_message.content = message
        elif isinstance(self.last_message.content, str):
            self.last_message.content = f'{message}\n{self.last_message.content}'
        elif isinstance(self.last_message.content, list):
            if len(self.last_message.content)  == 0:
                self.last_message.content.append(message)
            else:
                curr_last = self.last_message.content[0]
                if isinstance(curr_last, str):
                    self.last_message.content.append(message)
                else:
                    self.last_message.content.append({'added_message': message})

class WaitStatusMessage(BaseModel):
    agent_route: str
