import abc
import typing
from abc import ABC, abstractmethod
from typing import Union, AsyncIterable, List
from cdc_agents.common.types import Task, Message, Part, TextPart
from cdc_agents.common.types import (
    JSONRPCResponse,
    TaskIdParams,
    TaskQueryParams,
    GetTaskRequest,
    TaskNotFoundError,
    SendTaskRequest,
    CancelTaskRequest,
    TaskNotCancelableError,
    SetTaskPushNotificationRequest,
    GetTaskPushNotificationRequest,
    GetTaskResponse,
    CancelTaskResponse,
    SendTaskResponse,
    SetTaskPushNotificationResponse,
    GetTaskPushNotificationResponse,
    TaskSendParams,
    TaskStatus,
    TaskState,
    TaskResubscriptionRequest,
    SendTaskStreamingRequest,
    SendTaskStreamingResponse,
    Artifact,
    PushNotificationConfig,
    TaskStatusUpdateEvent,
    JSONRPCError,
    TaskPushNotificationConfig,
    InternalError,
)
from cdc_agents.common.server.utils import new_not_implemented_error
import asyncio
import logging

logger = logging.getLogger(__name__)

class TaskManager(ABC):

    @abc.abstractmethod
    def peek_to_process_task(self, session_id) -> typing.Optional[Message]:
        pass

    @abc.abstractmethod
    def pop_to_process_task(self, session_id) -> typing.Optional[Message]:
        pass

    @abstractmethod
    async def on_get_task(self, request: GetTaskRequest) -> GetTaskResponse:
        pass

    @abstractmethod
    async def on_cancel_task(self, request: CancelTaskRequest) -> CancelTaskResponse:
        pass

    @abstractmethod
    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        pass

    @abstractmethod
    async def on_send_task_subscribe(
        self, request: SendTaskStreamingRequest
    ) -> Union[AsyncIterable[SendTaskStreamingResponse], JSONRPCResponse]:
        pass

    @abstractmethod
    async def on_set_task_push_notification(
        self, request: SetTaskPushNotificationRequest
    ) -> SetTaskPushNotificationResponse:
        pass

    @abstractmethod
    async def on_get_task_push_notification(
        self, request: GetTaskPushNotificationRequest
    ) -> GetTaskPushNotificationResponse:
        pass

    @abstractmethod
    async def on_resubscribe_to_task(
        self, request: TaskResubscriptionRequest
    ) -> Union[AsyncIterable[SendTaskResponse], JSONRPCResponse]:
        pass

    @abstractmethod
    def task(self, session_id) -> typing.Optional[Task]:
        pass

    def on_complete_task(self, session_id):
        raise NotImplementedError

    @classmethod
    def get_user_query(cls, task_send_params: TaskSendParams) -> str:
        return cls.get_user_query_message(task_send_params.message)

    @classmethod
    def get_user_query_message(cls, task_send_params: Message) -> str:
        return '\n'.join([cls.get_user_query_part(p) for p in task_send_params.parts])

    @classmethod
    def get_user_query_part(cls, part: Part) -> str:
        if not isinstance(part, TextPart):
            raise ValueError("Only text parts are supported")
        return part.text

class InMemoryTaskManager(TaskManager):
    def __init__(self):
        self.tasks: dict[str, Task] = {}
        self.push_notification_infos: dict[str, PushNotificationConfig] = {}
        self.lock = asyncio.Lock()
        self.task_locks: dict[str, asyncio.Lock] = {}
        self.task_sse_subscribers: dict[str, List[asyncio.Queue]] = {}
        self.subscriber_lock = asyncio.Lock()

    async def peek_to_process_task(self, session_id) -> typing.Optional[Message]:
        async with self.lock:
            t = self.task(session_id)
            if t and len(t.to_process) != 0:
                return t.to_process[0]

            return None

    async def pop_to_process_task(self, session_id) -> typing.Optional[Message]:
        async with self.lock:
            t = self.task(session_id)
            if t and len(t.to_process) != 0:
                return t.to_process.pop(0)

            return None

    def task(self, session_id) -> typing.Optional[Task]:
        return self.tasks.get(session_id)

    async def on_get_task(self, request: GetTaskRequest) -> GetTaskResponse:
        logger.info(f"Getting task {request.params.id}")
        task_query_params: TaskQueryParams = request.params

        async with self.lock:
            task = self.tasks.get(task_query_params.id)
            if task is None:
                return GetTaskResponse(id=request.id, error=TaskNotFoundError())

            task_result = self.append_task_history(
                task, task_query_params.historyLength)

        return GetTaskResponse(id=request.id, result=task_result)

    async def on_cancel_task(self, request: CancelTaskRequest) -> CancelTaskResponse:
        logger.info(f"Cancelling task {request.params.id}")
        task_id_params: TaskIdParams = request.params

        async with self.lock:
            task = self.tasks.get(task_id_params.id)
            if task is None:
                return CancelTaskResponse(id=request.id, error=TaskNotFoundError())

        return CancelTaskResponse(id=request.id, error=TaskNotCancelableError())

    @abstractmethod
    async def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        pass

    @abstractmethod
    async def on_send_task_subscribe(
        self, request: SendTaskStreamingRequest
    ) -> Union[AsyncIterable[SendTaskStreamingResponse], JSONRPCResponse]:
        pass

    async def set_push_notification_info(self, task_id: str, notification_config: PushNotificationConfig):
        async with self.lock:
            task = self.tasks.get(task_id)
            if task is None:
                raise ValueError(f"Task not found for {task_id}")

            self.push_notification_infos[task_id] = notification_config

        return
    
    async def get_push_notification_info(self, task_id: str) -> PushNotificationConfig:
        async with self.lock:
            task = self.tasks.get(task_id)
            if task is None:
                raise ValueError(f"Task not found for {task_id}")

            return self.push_notification_infos[task_id]
            
        return
    
    async def has_push_notification_info(self, task_id: str) -> bool:
        async with self.lock:
            return task_id in self.push_notification_infos
            

    async def on_set_task_push_notification(
        self, request: SetTaskPushNotificationRequest
    ) -> SetTaskPushNotificationResponse:
        logger.info(f"Setting task push notification {request.params.id}")
        task_notification_params: TaskPushNotificationConfig = request.params

        try:
            await self.set_push_notification_info(task_notification_params.id, task_notification_params.pushNotificationConfig)
        except Exception as e:
            logger.error(f"Error while setting push notification info: {e}")
            return JSONRPCResponse(
                id=request.id,
                error=InternalError(
                    message="An error occurred while setting push notification info"
                ),
            )
            
        return SetTaskPushNotificationResponse(id=request.id, result=task_notification_params)

    async def on_get_task_push_notification(
        self, request: GetTaskPushNotificationRequest
    ) -> GetTaskPushNotificationResponse:
        logger.info(f"Getting task push notification {request.params.id}")
        task_params: TaskIdParams = request.params

        try:
            notification_info = await self.get_push_notification_info(task_params.id)
        except Exception as e:
            logger.error(f"Error while getting push notification info: {e}")
            return GetTaskPushNotificationResponse(
                id=request.id,
                error=InternalError(
                    message="An error occurred while getting push notification info"
                ),
            )
        
        return GetTaskPushNotificationResponse(id=request.id, result=TaskPushNotificationConfig(id=task_params.id, pushNotificationConfig=notification_info))

    async def upsert_task(self, task_send_params: TaskSendParams) -> Task:
        logger.info(f"Upserting task {task_send_params.id}")
        async with self.lock:
            if task_send_params.id not in self.task_locks.keys():
                self.task_locks[task_send_params.id] = asyncio.Lock()
        async with self.task_locks[task_send_params.id]:
            task = self.tasks.get(task_send_params.id)

            if task is None:
                task = Task(
                    id=task_send_params.id,
                    sessionId = task_send_params.sessionId,
                    messages=[task_send_params.message],
                    status=TaskStatus(state=TaskState.SUBMITTED),
                    history=[task_send_params.message],
                    to_process=[task_send_params.message]
                )
                self.tasks[task_send_params.id] = task
            else:
                task.history.append(task_send_params.message)
                task.to_process.append(task_send_params.message)

            return task

    async def on_resubscribe_to_task(
        self, request: TaskResubscriptionRequest
    ) -> Union[AsyncIterable[SendTaskStreamingResponse], JSONRPCResponse]:
        return new_not_implemented_error(request.id)

    async def update_store(
        self, task_id: str, status: TaskStatus, artifacts: list[Artifact]
    ) -> Task:
        async with self.lock:
            if task_id not in self.tasks.keys():
                logger.error(f"Task {task_id} not found for updating the task")
                raise ValueError(f"Task {task_id} not found")

            if task_id not in self.task_locks.keys():
                self.task_locks[task_id] = asyncio.Lock()
        async with self.task_locks[task_id]:
            task = self.tasks.get(task_id)
            task.status = status

            if status.message is not None:
                task.history.append(status.message)
                task.to_process.append(status.message)

            if artifacts is not None:
                if task.artifacts is None:
                    task.artifacts = []
                task.artifacts.extend(artifacts)

            return task

    def append_task_history(self, task: Task, historyLength: int | None):
        new_task = task.model_copy()
        if historyLength is not None and historyLength > 0:
            new_task.history = new_task.history[-historyLength:]
        else:
            new_task.history = []

        return new_task        

    async def setup_sse_consumer(self, task_id: str, is_resubscribe: bool = False):
        async with self.subscriber_lock:
            if task_id not in self.task_sse_subscribers:
                if is_resubscribe:
                    raise ValueError("Task not found for resubscription")
                else:
                    self.task_sse_subscribers[task_id] = []

            sse_event_queue = asyncio.Queue(maxsize=0) # <=0 is unlimited
            self.task_sse_subscribers[task_id].append(sse_event_queue)
            return sse_event_queue

    async def enqueue_events_for_sse(self, task_id, task_update_event):
        async with self.subscriber_lock:
            if task_id not in self.task_sse_subscribers:
                return

            current_subscribers = self.task_sse_subscribers[task_id]
            for subscriber in current_subscribers:
                await subscriber.put(task_update_event)

    async def dequeue_events_for_sse(
        self, request_id, task_id, sse_event_queue: asyncio.Queue
    ) -> AsyncIterable[SendTaskStreamingResponse] | JSONRPCResponse:
        try:
            while True:                
                event = await sse_event_queue.get()
                if isinstance(event, JSONRPCError):
                    yield SendTaskStreamingResponse(id=request_id, error=event)
                    break
                                                
                yield SendTaskStreamingResponse(id=request_id, result=event)
                if isinstance(event, TaskStatusUpdateEvent) and event.final:
                    break
        finally:
            async with self.subscriber_lock:
                if task_id in self.task_sse_subscribers:
                    self.task_sse_subscribers[task_id].remove(sse_event_queue)

