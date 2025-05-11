import unittest

from cdc_agents.common.utils.push_notification_auth import PushNotificationSenderAuth
from starlette.applications import Starlette

import asyncio
import copy
import json
import logging
import typing
import unittest
import uuid
from typing import Any
from unittest.mock import patch

from langchain_core.callbacks import Callbacks
from langchain_core.messages import ToolMessage, HumanMessage, AIMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import BaseTool, tool
from langchain_core.tools import StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

from aisuite.framework import ChatCompletionResponse
from cdc_agents.agent.a2a import A2AAgent
from cdc_agents.agent.agent_orchestrator import OrchestratorAgent, OrchestratedAgent
from cdc_agents.agent.agent_server import AgentServerRunner
from cdc_agents.agent.task_manager import AgentTaskManager
from cdc_agents.agents.deep_code_research_agent import DeepCodeOrchestrator
from cdc_agents.common.types import (
    JSONRPCResponse, SendTaskRequest, GetTaskRequest,
    CancelTaskRequest, SetTaskPushNotificationRequest,
    GetTaskPushNotificationRequest, SendTaskStreamingRequest,
    WaitStatusMessage, Message, TextPart, TaskState
)
from cdc_agents.config.agent_config import AgentConfig
from cdc_agents.config.agent_config_props import AgentConfigProps
from cdc_agents.config.model_server_config_props import ModelServerConfigProps
from cdc_agents.model_server.model_provider import ModelProvider
from cdc_agents.model_server.model_server_model import ModelServerModel, ModelServerInput
from cdc_agents_test.fixtures.agent_fixtures import (
    create_test_agent_task_manager, create_test_streaming_task_manager,
    create_video_streaming_task_manager, create_test_orchestrator,
    mock_push_notification_auth, create_text_message,
    TestA2AAgent, TestOrchestratorAgent, TestStreamingAgent, VideoStreamingAgent, create_mock_model
)
from drools_py.configs.config import ConfigType
from python_di.configs.bean import test_inject
from python_di.configs.test import test_booter, boot_test
from python_di.inject.profile_composite_injector.composite_injector import profile_scope
from python_di.inject.profile_composite_injector.inject_context_di import autowire_fn
from python_util.logger.log_level import LogLevel
from python_util.logger.logger import LoggerFacade

LogLevel.set_log_level(logging.DEBUG)

@test_booter(scan_root_module=AgentConfig)
class ServerRunnerBoot:
    pass

@boot_test(ctx=ServerRunnerBoot)
class A2AServerTest(unittest.IsolatedAsyncioTestCase):
    ai_suite: AgentConfigProps
    server: DeepCodeOrchestrator
    model: ModelServerModel
    memory: MemorySaver
    model_provider: ModelProvider
    server_runner: AgentServerRunner
    starlette: Starlette

    @test_inject(profile='test', scope=profile_scope)
    @autowire_fn(profile='test', scope_decorator=profile_scope)
    def construct(self,
                  ai_suite: AgentConfigProps,
                  server: DeepCodeOrchestrator,
                  model: ModelServerModel,
                  memory_saver: MemorySaver,
                  model_provider: ModelProvider,
                  server_runner: AgentServerRunner,
                  starlette: Starlette):
        A2AServerTest.starlette = starlette
        A2AServerTest.server_runner = server_runner
        A2AServerTest.memory = memory_saver
        A2AServerTest.ai_suite = ai_suite
        A2AServerTest.server = server
        A2AServerTest.model = model
        A2AServerTest.model_provider = model_provider
        manager = AgentTaskManager(A2AServerTest.server, PushNotificationSenderAuth())
        A2AServerTest.server.set_task_manager(manager)

    def test_inject(self):
        assert self.starlette
        assert self.server_runner
        assert self.memory
        assert self.ai_suite
        assert self.server
        assert self.model
        assert self.model_provider
        assert isinstance(self.server_runner.starlette, unittest.mock.MagicMock)

    def test_receive_a2a_invoke(self):
        # Setup
        session_id = str(uuid.uuid4())
        test_query = "Test query"
        
        # Set up responses and create agent with task manager
        responses = ["status: completed\nTask completed successfully"]
        test_agent, task_manager = create_test_agent_task_manager(
            self.ai_suite, self.memory, self.model_provider, self.model, responses
        )
        
        # Create a test request
        test_request = SendTaskRequest(
            id=session_id,
            params={
                "id": session_id,
                "sessionId": session_id,
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": test_query}]
                },
                "acceptedOutputModes": ["text"]
            }
        )
        
        # Execute the actual method
        response = task_manager.on_send_task(test_request)
        
        # Assert on the actual response
        self.assertEqual(response.id, session_id)
        self.assertIsNotNone(response.result)
        self.assertIsNone(response.error)
        self.assertEqual(response.result.status.state, TaskState.COMPLETED)
        self.assertEqual("Task completed successfully",
                     response.result.status.message.parts[0].text)

    def test_stream_agent(self):
        # Setup
        session_id = str(uuid.uuid4())
        test_query = "Stream from agent"
        
        # Set up responses and create streaming agent with task manager
        streaming_responses = [
            "status: completed\nTask completed!"
        ]
        
        test_agent, task_manager = create_test_streaming_task_manager(
            self.ai_suite, self.memory, self.model_provider, self.model, self.server, streaming_responses
        )
        
        # Create a streaming request
        test_request = SendTaskStreamingRequest(
            id=session_id,
            params={
                "id": session_id,
                "sessionId": session_id,
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": test_query}]
                },
                "acceptedOutputModes": ["text"]
            }
        )
        
        # Execute and collect streamed responses
        streamed_responses = []
        response_stream = task_manager.on_send_task_subscribe(test_request)
        
        # Collect all events from the stream
        for event in response_stream:
            streamed_responses.append(event)
        
        # Assert on the content of the events
        self.assertTrue(len(streamed_responses) >= 2)  # Should get status updates and artifacts
        
        # Check for status updates with the appropriate content
        status_updates = [r for r in streamed_responses if hasattr(r, 'result') and 'status' in r.result.__dict__.keys()]
        self.assertGreaterEqual(len(status_updates), 1)
        
        # Check that the final event is a completion event
        final_events = [r for r in streamed_responses if hasattr(r, 'result') and 'final' in r.result.__dict__.keys() and r.result.__dict__['final']]
        self.assertGreaterEqual(len(final_events), 1)

    # def test_stream_agent_deny_concurrent_execution(self):
    #     # Setup
    #     session_id = str(uuid.uuid4())
    #     test_query = "Stream with concurrent execution denied"
    #
    #     # Set up responses and create agent with task manager
    #     responses = ["status: working\nProcessing task..."]
    #     test_agent, task_manager = create_test_agent_task_manager(
    #         self.ai_suite, self.memory, self.model_provider, self.model, responses
    #     )
    #
    #     # Create a first request to start the task
    #     first_request = SendTaskRequest(
    #         id=session_id,
    #         params={
    #             "id": session_id,
    #             "sessionId": session_id,
    #             "message": {
    #                 "role": "user",
    #                 "parts": [{"type": "text", "text": "First request"}]
    #             },
    #             "acceptedOutputModes": ["text"]
    #         }
    #     )
    #
    #     # This should succeed and set the task state to WORKING
    #     task_manager.on_send_task(first_request)
    #
    #     # Now try to make a streaming request for the same session
    #     stream_request = SendTaskStreamingRequest(
    #         id=session_id,
    #         params={
    #             "id": session_id,
    #             "sessionId": session_id,
    #             "message": {
    #                 "role": "user",
    #                 "parts": [{"type": "text", "text": test_query}]
    #             },
    #             "acceptedOutputModes": ["text"]
    #         }
    #     )
    #
    #     # The streaming request should be rejected because the task is already active
    #     response = task_manager.on_send_task_subscribe(stream_request)
    #
    #     # Assert that we got an error response, not a streaming response
    #     self.assertIsInstance(response, JSONRPCResponse)
    #     self.assertIsNotNone(response.error)
    #     self.assertIn("Cannot stream task that has already started", response.error.message)
    #
    # def test_stream_agent_add_history(self):
    #     # Setup
    #     session_id = str(uuid.uuid4())
    #     test_query = "Stream with history"
    #
    #     # Set up history-aware streaming responses
    #     streaming_responses = [
    #         "Processing with history...",
    #         "Looking at previous messages...",
    #         "status: completed\nCompleted with history"
    #     ]
    #
    #     # Create streaming agent with task manager
    #     test_agent, task_manager = create_test_streaming_task_manager(
    #         self.ai_suite, self.memory, self.model_provider, self.model, streaming_responses
    #     )
    #
    #     # Create a streaming request with history
    #     test_request = SendTaskStreamingRequest(
    #         id=session_id,
    #         params={
    #             "id": session_id,
    #             "sessionId": session_id,
    #             "message": {
    #                 "role": "user",
    #                 "parts": [{"type": "text", "text": test_query}]
    #             },
    #             "historyLength": 2,
    #             "metadata": {
    #                 "history": [{"role": "user", "content": "Previous query"},
    #                             {"role": "assistant", "content": "Previous response"}]
    #             },
    #             "acceptedOutputModes": ["text"]
    #         }
    #     )
    #
    #     # Execute and collect streamed responses
    #     streamed_responses = []
    #     response_stream = task_manager.on_send_task_subscribe(test_request)
    #
    #     # We expect to get an SSE stream back
    #     self.assertIsInstance(response_stream, typing.AsyncIterable)
    #
    #     # Collect all events from the stream
    #     # async for event in response_stream:
    #     #     streamed_responses.append(event)
    #
    #     # Assert on the content of the events
    #     self.assertTrue(len(streamed_responses) >= 2)  # Should get status updates and artifacts
    #
    #     # Check for completed status
    #     final_events = [r for r in streamed_responses if hasattr(r, 'data') and 'final' in json.loads(r.data) and json.loads(r.data)['final']]
    #     self.assertGreaterEqual(len(final_events), 1)
    #
    # def test_postgres_checkpointer_concurrent_execution(self):
    #     """
    #     The TaskManager must be made to be a postgres repository in this case, and need distributed lock stripes.
    #     This test simulates concurrent access patterns to verify locking behavior.
    #     """
    #     # Setup
    #     session_id = str(uuid.uuid4())
    #
    #     test_agent, task_manager = create_test_agent_task_manager(
    #         self.ai_suite, self.memory, self.model_provider, self.model, [
    #         "status: working\nProcessing first query...",
    #         "status: completed\nCompleted first query",
    #         "status: working\nProcessing second query...",
    #         "status: completed\nCompleted second query"
    #     ]
    #     )
    #
    #     # Create a real task manager with our test agent
    #     from cdc_agents.common.utils.push_notification_auth import PushNotificationSenderAuth
    #     notification_auth = PushNotificationSenderAuth()
    #     notification_auth.generate_jwk()
    #     task_manager = AgentTaskManager(test_agent, notification_auth)
    #     test_agent.set_task_manager(task_manager)
    #
    #     # Create first request
    #     first_request = SendTaskRequest(
    #         id=session_id,
    #         params={
    #             "id": session_id,
    #             "sessionId": session_id,
    #             "message": {
    #                 "role": "user",
    #                 "parts": [{"type": "text", "text": "First concurrent query"}]
    #             },
    #             "acceptedOutputModes": ["text"]
    #         }
    #     )
    #
    #     # Create second request with the same session ID
    #     second_request = SendTaskRequest(
    #         id=f"{session_id}-2",
    #         params={
    #             "id": session_id,
    #             "sessionId": session_id,
    #             "message": {
    #                 "role": "user",
    #                 "parts": [{"type": "text", "text": "Second concurrent query"}]
    #             },
    #             "acceptedOutputModes": ["text"]
    #         }
    #     )
    #
    #     # Execute tasks "concurrently"
    #     task1 = task_manager.on_send_task(first_request)
    #     task2 = task_manager.on_send_task(second_request)
    #
    #     # Wait for both to complete
    #     response1, response2 = asyncio.gather(task1, task2)
    #
    #     # Verify that the first task was processed
    #     self.assertEqual(response1.id, session_id)
    #     self.assertIsNotNone(response1.result)
    #     self.assertIsNone(response1.error)
    #
    #     # Verify that the second task was also processed
    #     # The actual implementation should ensure proper locking/queueing
    #     self.assertEqual(response2.id, f"{session_id}-2")
    #     self.assertIsNotNone(response2.result)
    #     self.assertIsNone(response2.error)
        
        # In a PostgreSQL implementation, we'd test that task ordering and task state
        # are properly maintained across distributed locks

    # def test_concurrent_execution_add_history_invoke(self):
    #     # Setup
    #     session_id = str(uuid.uuid4())
    #     test_query = "Test concurrent execution with history"
    #
    #     # Set up a mock agent with controlled responses
    #     # Create a test agent
    #     test_agent, task_manager = create_test_agent_task_manager(self.ai_suite, self.memory, self.model_provider, self.model, [
    #         "status: working\nWorking with history...",
    #         "status: completed\nTask completed with history",
    #         "status: working\nWorking on follow-up...",
    #         "status: completed\nFollow-up task completed"
    #     ])
    #
    #     # Create initial request with history
    #     initial_request = SendTaskRequest(
    #         id=session_id,
    #         params={
    #             "id": session_id,
    #             "sessionId": session_id,
    #             "message": {
    #                 "role": "user",
    #                 "parts": [{"type": "text", "text": test_query}]
    #             },
    #             "historyLength": 2,
    #             "metadata": {
    #                 "history": [{"role": "user", "content": "Previous query"},
    #                             {"role": "assistant", "content": "Previous response"}]
    #             },
    #             "acceptedOutputModes": ["text"]
    #         }
    #     )
    #
    #     # Execute the first request
    #     initial_response = task_manager.on_send_task(initial_request)
    #
    #     # Verify initial response
    #     self.assertEqual(initial_response.id, session_id)
    #     self.assertIsNotNone(initial_response.result)
    #     self.assertIsNone(initial_response.error)
    #
    #     # Create a follow-up request (simulating concurrent execution attempt)
    #     follow_up_request = SendTaskRequest(
    #         id=f"{session_id}-followup",
    #         params={
    #             "id": session_id,  # Same session ID
    #             "sessionId": session_id,
    #             "message": {
    #                 "role": "user",
    #                 "parts": [{"type": "text", "text": "Follow-up query"}]
    #             }
    #         }
    #     )
    #
    #     # Execute the follow-up request - this should also work since previous task completed
    #     follow_up_response = task_manager.on_send_task(follow_up_request)
    #
    #     # Verify follow-up response
    #     self.assertEqual(follow_up_response.id, f"{session_id}-followup")
    #     self.assertIsNotNone(follow_up_response.result)
    #     self.assertIsNone(follow_up_response.error)
    #
    #     # Now get the task to verify history was preserved
    #     get_request = GetTaskRequest(
    #         id=session_id,
    #         params={"id": session_id}
    #     )
    #
    #     get_response = task_manager.on_get_task(get_request)
    #
    #     # Verify the task has both interactions in its history
    #     self.assertEqual(get_response.id, session_id)
    #     self.assertIsNotNone(get_response.result)
    #     self.assertIsNone(get_response.error)
    #
    #     # The history should include both interactions
    #     artifacts = get_response.result.artifacts
    #     self.assertGreaterEqual(len(artifacts), 1)
    #
    # def test_stream_video_file(self):
    #     # Setup - create a video streaming agent
    #     session_id = str(uuid.uuid4())
    #     test_query = "Stream a video file"
    #
    #     # Set up video streaming responses
    #     video_responses = [
    #         "Starting video stream...",
    #         "Video chunk 1",
    #         "Video chunk 2",
    #         "status: completed\nVideo streaming complete"
    #     ]
    #
    #     # Create video streaming agent with task manager
    #     test_agent, task_manager = create_video_streaming_task_manager(
    #         self.ai_suite, self.memory, self.model_provider, self.model, video_responses
    #     )
    #
    #     # Create a streaming request with video metadata
    #     test_request = SendTaskStreamingRequest(
    #         id=session_id,
    #         params={
    #             "id": session_id,
    #             "sessionId": session_id,
    #             "message": {
    #                 "role": "user",
    #                 "parts": [{"type": "text", "text": test_query, "metadata": {"media_type": "video"}}]
    #             },
    #             "acceptedOutputModes": ["text", "video"]
    #         }
    #     )
    #
    #     # Execute and collect streamed responses
    #     streamed_responses = []
    #     response_stream = task_manager.on_send_task_subscribe(test_request)
    #
    #     # We expect to get an SSE stream back
    #     self.assertIsInstance(response_stream, typing.AsyncIterable)
    #
    #     # Collect all events from the stream
    #     async for event in response_stream:
    #         streamed_responses.append(event)
    #
    #     # Assert that we got streaming events
    #     self.assertTrue(len(streamed_responses) >= 4)  # At least 4 status updates for video chunks
    #
    #     # Verify the final event is a completion
    #     final_events = [r for r in streamed_responses if hasattr(r, 'data') and 'final' in json.loads(r.data) and json.loads(r.data)['final']]
    #     self.assertGreaterEqual(len(final_events), 1)
    #
    # def test_invalid_session_id(self):
    #     # Setup - create an invalid UUID format
    #     invalid_session_id = "not-a-valid-uuid"
    #
    #     # Create a test agent
    #
    #     test_agent, task_manager = create_test_streaming_task_manager(
    #         self.ai_suite, self.memory, self.model_provider, self.model, self.server, [
    #             "status: completed\nResponse shouldn't matter, we expect validation error"
    #         ])
    #
    #     # Create task manager
    #     from cdc_agents.common.utils.push_notification_auth import PushNotificationSenderAuth
    #     notification_auth = PushNotificationSenderAuth()
    #     notification_auth.generate_jwk()
    #     task_manager = AgentTaskManager(test_agent, notification_auth)
    #     test_agent.set_task_manager(task_manager)
    #
    #     # Create a request with an invalid ID format
    #     test_request = SendTaskRequest(
    #         id=invalid_session_id,
    #         params={
    #             "id": invalid_session_id,
    #             "sessionId": invalid_session_id,  # This should cause validation to fail
    #             "message": {
    #                 "role": "user",
    #                 "parts": [{"type": "text", "text": "Test with invalid session ID"}]
    #             },
    #             "acceptedOutputModes": ["text"]
    #         }
    #     )
    #
    #     # Execute the request and expect an error response with validation failure
    #     response = task_manager.on_send_task(test_request)
    #
    #     # When a UUIDv4 validation failure occurs, we'd expect an error response
    #     self.assertEqual(response.id, invalid_session_id)
    #     self.assertIsNotNone(response.error)
    #
    #     # Get request with invalid ID
    #     get_request = GetTaskRequest(
    #         id=invalid_session_id,
    #         params={"id": invalid_session_id}
    #     )
    #
    #     # Execute the get request for a non-existent task
    #     get_response = task_manager.on_get_task(get_request)
    #
    #     # Should get a "task not found" type of error
    #     self.assertEqual(get_response.id, invalid_session_id)
    #     self.assertIsNotNone(get_response.error)
    #
    # def test_push_notification(self):
    #     # Setup
    #     session_id = str(uuid.uuid4())
    #     notification_url = "https://example.com/notifications"
    #
    #     # We'll patch the verify_push_notification_url method to avoid actual HTTP requests
    #     from cdc_agents.common.types import PushNotificationConfig
    #     from cdc_agents.common.utils.push_notification_auth import PushNotificationSenderAuth
    #     from unittest.mock import patch
    #
    #     test_agent, task_manager = create_test_streaming_task_manager(
    #         self.ai_suite, self.memory, self.model_provider, self.model, self.server, [
    #             "status: completed\nTask with push notification"
    #         ])
    #
    #     # Create notification auth with mocked verification
    #     notification_auth = PushNotificationSenderAuth()
    #     notification_auth.generate_jwk()
    #
    #     # Create task manager
    #     task_manager = AgentTaskManager(test_agent, notification_auth)
    #     test_agent.set_task_manager(task_manager)
    #
    #     # Create test requests
    #     with patch.object(PushNotificationSenderAuth, 'verify_push_notification_url',
    #                       return_value=True) as mock_verify:
    #         # Set the future result to True to simulate successful verification
    #
    #         # Create and execute set request
    #         set_request = SetTaskPushNotificationRequest(
    #             id=session_id,
    #             params={
    #                 "id": session_id,
    #                 "pushNotificationConfig": {"url": notification_url}
    #             }
    #         )
    #
    #         # Create and execute get request
    #         get_request = GetTaskPushNotificationRequest(
    #             id=session_id,
    #             params={"id": session_id}
    #         )
    #
    #         # Execute the actual methods
    #         set_response = task_manager.on_set_task_push_notification(set_request)
    #         get_response = task_manager.on_get_task_push_notification(get_request)
    #
    #         # Now send a task with the notification URL set
    #         task_request = SendTaskRequest(
    #             id=session_id,
    #             params={
    #                 "id": session_id,
    #                 "sessionId": session_id,
    #                 "message": {
    #                     "role": "user",
    #                     "parts": [{"type": "text", "text": "Task with notification"}]
    #                 },
    #                 "pushNotification": {"url": notification_url},
    #                 "acceptedOutputModes": ["text"]
    #             }
    #         )
    #
    #         # Mock the send_push_notification method to avoid actual HTTP requests
    #         with patch.object(PushNotificationSenderAuth, 'send_push_notification',
    #                           return_value=True) as mock_send:
    #             # Execute the task
    #             task_response = task_manager.on_send_task(task_request)
    #
    #             # Verify the task response
    #             self.assertEqual(task_response.id, session_id)
    #             self.assertIsNotNone(task_response.result)
    #
    #             # Verify the notification was attempted
    #             mock_send.assert_called()
    #
    #     # Verify the set/get responses
    #     self.assertEqual(set_response.id, session_id)
    #     self.assertEqual(get_response.id, session_id)
    #     self.assertEqual(get_response.result.url, notification_url)
    #
    #
    # def test_receive_a2a_invoke_orchestrator_needs_input_invoke_again(self):
    #     # Setup
    #     session_id = str(uuid.uuid4())
    #     test_query = "Test query that needs more information"
    #     follow_up_query = "Here is more information"
    #
    #     # Set up responses and create agent with task manager
    #     responses = [
    #         "status: input_needed\nPlease provide more information",
    #         "status: completed\nTask completed with additional information"
    #     ]
    #
    #     test_agent, task_manager = create_test_agent_task_manager(
    #         self.ai_suite, self.memory, self.model_provider, self.model, responses
    #     )
    #
    #     # Create test requests
    #     initial_request = SendTaskRequest(
    #         id=session_id,
    #         params={
    #             "id": session_id,
    #             "sessionId": session_id,
    #             "message": {
    #                 "role": "user",
    #                 "parts": [{"type": "text", "text": test_query}]
    #             },
    #             "acceptedOutputModes": ["text"]
    #         }
    #     )
    #
    #     follow_up_request = SendTaskRequest(
    #         id=session_id,
    #         params={
    #             "id": session_id,
    #             "sessionId": session_id,
    #             "message": {
    #                 "role": "user",
    #                 "parts": [{"type": "text", "text": follow_up_query}]
    #             },
    #             "acceptedOutputModes": ["text"]
    #         }
    #     )
    #
    #     # Execute initial request
    #     initial_response = task_manager.on_send_task(initial_request)
    #
    #     # Assert that more input is needed
    #     self.assertEqual(initial_response.id, session_id)
    #     self.assertEqual(initial_response.result.get("status").state, "input_required")
    #     self.assertIn("Please provide more information",
    #                   initial_response.result.get("status").message.parts[0].text)
    #
    #     # Execute follow-up request
    #     follow_up_response = task_manager.on_send_task(follow_up_request)
    #
    #     # Assert that the task is now completed
    #     self.assertEqual(follow_up_response.id, session_id)
    #     self.assertEqual(follow_up_response.result.get("status").state, "completed")
    #     self.assertIn("Task completed with additional information",
    #                   follow_up_response.result.get("artifacts")[0].parts[0].text)
    #
    # def test_receive_a2a_invoke_inner_agent_needs_input_invoke_again(self):
    #     # Setup
    #     session_id = str(uuid.uuid4())
    #     test_query = "Task requiring an inner agent that needs input"
    #
    #     # Create test requests
    #     initial_request = SendTaskRequest(
    #         id=session_id,
    #         params={
    #             "id": session_id,
    #             "message": {
    #                 "role": "user",
    #                 "parts": [{"type": "text", "text": test_query}]
    #             }
    #         }
    #     )
    #
    #     inner_agent_request = SendTaskRequest(
    #         id=session_id,
    #         params={
    #             "id": session_id,
    #             "message": {
    #                 "role": "user",
    #                 "parts": [{"type": "text", "text": "Additional input for inner agent"}],
    #                 "agent_route": "InnerAgent"
    #             }
    #         }
    #     )
    #
    #     # Execute initial request
    #     initial_response_result = self.server.task_manager.on_send_task(initial_request)
    #
    #     # Assert that inner agent needs input
    #     self.assertEqual(initial_response_result.id, session_id)
    #     self.assertEqual(initial_response_result.result.get("status"), "next_agent")
    #     self.assertEqual(initial_response_result.result.get("route_to"), "InnerAgent")
    #
    #     # Execute inner agent request
    #     follow_up_response_result =  self.server.task_manager.on_send_task(inner_agent_request)
    #
    #     # Assert that the task is now completed
    #     self.assertEqual(follow_up_response_result.id, session_id)
    #     self.assertEqual(follow_up_response_result.result.get("status"), "completed")
    #     self.assertEqual(self.server.task_manager.on_send_task.call_count, 2)
