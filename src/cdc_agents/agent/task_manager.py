import logging
import typing

from cdc_agents.common.types import Message, ResponseFormat, AgentGraphResponse, AgentGraphResult, WaitStatusMessage
import threading
import traceback
from typing import AsyncIterable
from typing import Union

import asyncio

import cdc_agents.common.server.utils as utils
from cdc_agents.agent.a2a import A2AAgent
from cdc_agents.common.server.task_manager import InMemoryTaskManager
from cdc_agents.common.types import (
    SendTaskRequest,
    TaskSendParams,
    Message,
    TaskStatus,
    Artifact,
    TextPart,
    TaskState,
    SendTaskResponse,
    InternalError,
    JSONRPCResponse,
    SendTaskStreamingRequest,
    SendTaskStreamingResponse,
    TaskArtifactUpdateEvent,
    TaskStatusUpdateEvent,
    Task,
    TaskIdParams,
    PushNotificationConfig,
    InvalidParamsError, Part, InvalidRequestError,
    # PushTaskEvent,
)
from cdc_agents.common.utils.push_notification_auth import PushNotificationSenderAuth
from python_util.logger.logger import LoggerFacade

logger = logging.getLogger(__name__)

class AgentTaskManager(InMemoryTaskManager):

    def __init__(self,
                 agent: A2AAgent,
                 notification_sender_auth: PushNotificationSenderAuth):
        super().__init__()
        self.agent = agent
        self.notification_sender_auth = notification_sender_auth

    def _run_streaming_agent(self, request: SendTaskStreamingRequest):
        self.insert_lock(request.params.id)

        task_send_params: TaskSendParams = request.params
        query = self.get_user_query(task_send_params)

        try:
            threading.Thread(target=lambda: self._do_agent_stream(query, task_send_params.sessionId)).start()
        except Exception as e:
            logger.error(f"An error occurred while streaming the response: {e}")
            self.enqueue_events_for_sse(
                task_send_params.id,
                InternalError(message=f"An error occurred while streaming the response: {e}"))

    def _do_agent_stream(self, query, session_id):
        for item in self.agent.stream(query, session_id):
            item: AgentGraphResponse = item
            is_task_complete = item.is_task_complete
            require_user_input = item.require_user_input
            artifact = None
            message = None
            parts = [{"type": "text", "text": item.content.message}]
            do_end_stream = False
            do_restart_stream = False

            if not is_task_complete and not require_user_input:
                with self.task_locks[session_id]:
                    task_state = TaskState.WORKING
                    message = Message(role="agent", parts=parts)
                    self._apply_task_enqueue(artifact, do_end_stream, message, session_id, task_state)
            elif require_user_input:
                with self.task_locks[session_id]:
                    task_state = TaskState.INPUT_REQUIRED
                    message = Message(role="agent", parts=parts)
                    do_end_stream = True
                    self._apply_task_enqueue(artifact, do_end_stream, message, session_id, task_state)
            else:
                with self.task_locks[session_id]:
                    task = self.task(session_id)
                    if self._no_more_to_process(task):
                        task_state = TaskState.COMPLETED
                        artifact = Artifact(parts=parts, index=0, append=False)
                        do_end_stream = True
                        self._apply_task_enqueue(artifact, do_end_stream, message, session_id, task_state)
                    else:
                        # If message was added after stream finished, then run stream until finished processing.
                        query = self.get_user_query_message(next(iter(task.to_process)))
                        do_restart_stream = True

                if do_restart_stream:
                    LoggerFacade.info("Found task query added with send task after finished stream. "
                                      "Starting another agent stream.")
                    try:
                        self._do_agent_stream(query, session_id)
                    except Exception as e:
                        LoggerFacade.error(f"Error performing agent stream - could not load history concurrently: {e}. "
                                           f"Will not try again. {query} was missing message.")
            if do_end_stream:
                return

    def _no_more_to_process(self, task):
        return not task.to_process or (task.to_process is not None and len(task.to_process) == 0)

    def _apply_task_enqueue(self, artifact, end_stream, message, session_id, task_state):
        task_status = TaskStatus(state=task_state, message=message)
        latest_task = self.update_store(
            session_id,
            task_status,
            None if artifact is None else [artifact],
            append_process=False)
        self.send_task_notification(latest_task)
        if artifact:
            task_artifact_update_event = TaskArtifactUpdateEvent(
                id=session_id, artifact=artifact
            )
            self.enqueue_events_for_sse(
                session_id, task_artifact_update_event
            )
        task_update_event = TaskStatusUpdateEvent(
            id=session_id, status=task_status, final=end_stream
        )
        self.enqueue_events_for_sse(
            session_id, task_update_event)

    def _validate_request(
        self, request: Union[SendTaskRequest, SendTaskStreamingRequest]
    ) -> JSONRPCResponse | None:
        task_send_params: TaskSendParams = request.params
        if not utils.are_modalities_compatible(
            task_send_params.acceptedOutputModes, self.agent.supported_content_types
        ):
            logger.warning(
                "Unsupported output mode. Received %s, Support %s",
                task_send_params.acceptedOutputModes,
                self.agent.supported_content_types,
            )
            return utils.new_incompatible_types_error(request.id)
        
        if task_send_params.pushNotification and not task_send_params.pushNotification.url:
            logger.warning("Push notification URL is missing")
            return JSONRPCResponse(id=request.id, error=InvalidParamsError(message="Push notification URL is missing"))
        
        return None
        
    def on_send_task(self, request: SendTaskRequest) -> SendTaskResponse:
        """Handles the 'send task' request."""
        validation_error = self._validate_request(request)
        if validation_error:
            return SendTaskResponse(id=request.id, error=validation_error.error)
        
        if request.params.pushNotification:
            if not self.set_push_notification_info(request.params.id, request.params.pushNotification):
                return SendTaskResponse(id=request.id, error=InvalidParamsError(message="Push notification URL is invalid"))

        self.insert_lock(request.params.id)

        task_send_params: TaskSendParams = request.params
        request_id = request.id

        with self.task_locks[task_send_params.id]:
            prev_task = self.upsert_task(task_send_params)
            if prev_task.status == TaskState.WORKING:
                # Task already working - will catch the messages below
                return SendTaskResponse(id=request_id, result=prev_task)

            # must update the store in the same lock here - otherwise it fails.
            task = self.update_store(task_send_params.id, TaskStatus(state=TaskState.WORKING), None)

        self.send_task_notification(task)
        return self._do_on_send_task(self.get_user_query(task_send_params), request_id, task_send_params)

    def _do_on_send_task(self, query, request_id, task_send_params: TaskSendParams):
        self.insert_lock(request_id)
        try:
            agent_response = self.agent.invoke(query, task_send_params.sessionId)
        except Exception as e:
            LoggerFacade.error(f"Error invoking agent: {e}.")
            raise ValueError(f"Error invoking agent: {e}.")
        try:
            # loop until stop receiving messages for this agent.
            has_more_work = False
            with self.task_locks[request_id]:
                task = self.task(request_id)
                if task and len(task.to_process)  != 0:
                    query = self.get_user_query_message(next(iter(task.to_process)))
                    has_more_work = True

            #  Perform this out of lock.
            if has_more_work:
                return self._do_on_send_task(query, request_id, task_send_params)

            return self._process_agent_response(request_id, task_send_params, agent_response)
        except Exception as e:
            if has_more_work:
                LoggerFacade.error(f"Error processing additional query added concurrently: {e}. "
                                   f"Returning without last query: {query}")
                return self._process_agent_response(request_id, task_send_params, agent_response)
            raise ValueError(f"Error processing agent query: {e}")


    def on_send_task_subscribe(
        self, request: SendTaskStreamingRequest
    ) -> typing.Generator[SendTaskStreamingResponse, None, None] | JSONRPCResponse:
        try:
            error = self._validate_request(request)
            if error:
                return error

            self.insert_lock(request.params.id)

            with self.task_locks[request.params.id]:
                prev_task = self.upsert_task(request.params)
                if prev_task is not None and prev_task.status.state == TaskState.WORKING:
                    return JSONRPCResponse(
                        id=request.id,
                        error=InvalidRequestError(
                            message="Cannot stream task that has already started. "
                                    "Must send a task message or wait until task is completed."))
                # must update the store in the same lock here - otherwise it fails.
                prev_task = self.update_store(
                    request.params.id, TaskStatus(state=TaskState.WORKING),None)


            if request.params.pushNotification:
                if not self.set_push_notification_info(request.params.id, request.params.pushNotification):
                    return JSONRPCResponse(id=request.id, error=InvalidParamsError(message="Push notification URL is invalid"))

            task_send_params: TaskSendParams = request.params

            sse_event_queue = self.setup_sse_consumer(task_send_params.id, False)

            self._run_streaming_agent(request)

            return self.dequeue_events_for_sse(
                request.id, task_send_params.id, sse_event_queue)
        except Exception as e:
            logger.error(f"Error in SSE stream: {e}")
            print(traceback.format_exc())
            return JSONRPCResponse(
                id=request.id,
                error=InternalError(
                    message="An error occurred while streaming the response"
                ))

    def _process_agent_response(
        self, request_id, request_params: TaskSendParams, agent_response: AgentGraphResponse
    ) -> SendTaskResponse:
        """Processes the agent's response and updates the task store."""
        task_send_params: TaskSendParams = request_params
        task_id = task_send_params.id
        history_length = task_send_params.historyLength
        task_status = None

        parts = [{"type": "text", "text": agent_response.content.message}]
        artifact = None
        if agent_response.require_user_input:
            task_status = TaskStatus(
                state=TaskState.INPUT_REQUIRED,
                message=Message(role="agent", parts=parts),
            )
        else:
            task_status = TaskStatus(state=TaskState.COMPLETED, message=Message(role="agent", parts=parts))
            artifact = Artifact(parts=parts)
        task = self.update_store(
            task_id, task_status, None if artifact is None else [artifact]
        )
        task_result = self.append_task_history(task, history_length)
        self.send_task_notification(task)
        return SendTaskResponse(id=request_id, result=task_result)

    def send_task_notification(self, task: Task):
        if not self.has_push_notification_info(task.id):
            logger.info(f"No push notification info found for task {task.id}")
            return
        push_info = self.get_push_notification_info(task.id)

        logger.info(f"Notifying for task {task.id} => {task.status.state}")
        self.notification_sender_auth.send_push_notification(
            push_info.url,
            data=task.model_dump(exclude_none=True)
        )

    def on_resubscribe_to_task(
        self, request
    ) -> AsyncIterable[SendTaskStreamingResponse] | JSONRPCResponse:
        task_id_params: TaskIdParams = request.params
        try:
            sse_event_queue = self.setup_sse_consumer(task_id_params.id, True)
            return self.dequeue_events_for_sse(request.id, task_id_params.id, sse_event_queue)
        except Exception as e:
            logger.error(f"Error while reconnecting to SSE stream: {e}")
            return JSONRPCResponse(
                id=request.id,
                error=InternalError(
                    message=f"An error occurred while reconnecting to stream: {e}"
                ),
            )
    
    def set_push_notification_info(self, task_id: str, push_notification_config: PushNotificationConfig):
        # Verify the ownership of notification URL by issuing a challenge request.
        is_verified = self.notification_sender_auth.verify_push_notification_url(push_notification_config.url)
        if not is_verified:
            return False
        
        super().set_push_notification_info(task_id, push_notification_config)
        return True
