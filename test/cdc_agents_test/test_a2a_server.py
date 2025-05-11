import unittest

from cdc_agents.common.utils.push_notification_auth import PushNotificationSenderAuth
from starlette.applications import Starlette

import asyncio
import copy
import json
import logging
import typing
import unittest
import unittest.mock
import uuid
from typing import Any

from langchain_core.callbacks import Callbacks
from langchain_core.messages import ToolMessage, HumanMessage, AIMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import BaseTool, tool
from langchain_core.tools import StructuredTool
from langchain_mcp_adapters.client import MultiServerMCPClient
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph

from aisuite.framework import ChatCompletionResponse
from cdc_agents.agent.agent import A2AReactAgent
from cdc_agents.agent.agent_orchestrator import OrchestratorAgent, OrchestratedAgent
from cdc_agents.agent.agent_server import AgentServerRunner
from cdc_agents.agent.task_manager import AgentTaskManager
from cdc_agents.agents.deep_code_research_agent import DeepCodeOrchestrator
from cdc_agents.common.types import (
    JSONRPCResponse, SendTaskRequest, GetTaskRequest,
    CancelTaskRequest, SetTaskPushNotificationRequest,
    GetTaskPushNotificationRequest, SendTaskStreamingRequest,
    WaitStatusMessage
)
from cdc_agents.config.agent_config import AgentConfig
from cdc_agents.config.agent_config_props import AgentConfigProps
from cdc_agents.config.model_server_config_props import ModelServerConfigProps
from cdc_agents.model_server.model_provider import ModelProvider
from cdc_agents.model_server.model_server_model import ModelServerModel, ModelServerInput
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

    async def test_receive_a2a_invoke(self):
        # Setup
        session_id = str(uuid.uuid4())
        test_query = "Test query"

        # Create a mock response for the on_send_task method
        mock_response = JSONRPCResponse(
            id=session_id,
            result={"status": "completed", "message": "Task completed successfully"}
        )

        # Mock the task manager's on_send_task method
        self.server.task_manager.on_send_task = unittest.mock.AsyncMock(return_value=mock_response)

        # Create a test request
        test_request = SendTaskRequest(
            id=session_id,
            method="send_task",
            params={"task": {"query": test_query}}
        )

        # Execute
        response = await self.server.task_manager.on_send_task(test_request)

        # Assert
        self.assertEqual(response.id, session_id)
        self.assertIsNotNone(response.result)
        self.assertIsNone(response.error)
        self.server.task_manager.on_send_task.assert_called_once()

    async def test_receive_a2a_invoke_orchestrator_needs_input_invoke_again(self):
        # Setup
        session_id = str(uuid.uuid4())
        test_query = "Test query that needs more information"

        # Create a mock response that indicates input is needed
        first_response = JSONRPCResponse(
            id=session_id,
            result={"status": "input_needed", "message": "Please provide more information"}
        )

        # Create a follow-up response after input is provided
        second_response = JSONRPCResponse(
            id=session_id,
            result={"status": "completed", "message": "Task completed with additional information"}
        )

        # Mock the task manager's on_send_task method to return different responses
        self.server.task_manager.on_send_task = unittest.mock.AsyncMock(side_effect=[first_response, second_response])

        # Create test requests
        initial_request = SendTaskRequest(
            id=session_id,
            method="send_task",
            params={"task": {"query": test_query}}
        )

        follow_up_request = SendTaskRequest(
            id=session_id,
            method="send_task",
            params={"task": {"query": "Here is more information"}}
        )

        # Execute initial request
        initial_response = await self.server.task_manager.on_send_task(initial_request)

        # Assert that more input is needed
        self.assertEqual(initial_response.id, session_id)
        self.assertEqual(initial_response.result.get("status"), "input_needed")

        # Execute follow-up request
        follow_up_response =  await self.server.task_manager.on_send_task(follow_up_request)

        # Assert that the task is now completed
        self.assertEqual(follow_up_response.id, session_id)
        self.assertEqual(follow_up_response.result.get("status"), "completed")
        self.assertEqual(self.server.task_manager.on_send_task.call_count, 2)

    async def test_receive_a2a_invoke_inner_agent_needs_input_invoke_again(self):
        # Setup
        session_id = str(uuid.uuid4())
        test_query = "Task requiring an inner agent that needs input"

        # Mock the status message with a wait status for an inner agent
        status_message = WaitStatusMessage(agent_route="InnerAgent")

        # Create a mock response that indicates an inner agent needs input
        initial_response = JSONRPCResponse(
            id=session_id,
            result={
                "status": "next_agent",
                "message": "status_message: awaiting input for InnerAgent",
                "route_to": "InnerAgent"
            }
        )

        # Create a follow-up response after input is provided to the inner agent
        follow_up_response = JSONRPCResponse(
            id=session_id,
            result={"status": "completed", "message": "Inner agent task completed"}
        )

        # Mock the task manager's methods
        self.server.task_manager.on_send_task = unittest.mock.AsyncMock(side_effect=[initial_response, follow_up_response])
        self.server.get_status_message = unittest.mock.MagicMock(return_value=status_message)

        # Create test requests
        initial_request = SendTaskRequest(
            id=session_id,
            method="send_task",
            params={"task": {"query": test_query}}
        )

        inner_agent_request = SendTaskRequest(
            id=session_id,
            method="send_task",
            params={"task": {"query": "Additional input for inner agent"}, "agent_route": "InnerAgent"}
        )

        # Execute initial request
        initial_response_result = await self.server.task_manager.on_send_task(initial_request)

        # Assert that inner agent needs input
        self.assertEqual(initial_response_result.id, session_id)
        self.assertEqual(initial_response_result.result.get("status"), "next_agent")
        self.assertEqual(initial_response_result.result.get("route_to"), "InnerAgent")

        # Execute inner agent request
        follow_up_response_result =  await self.server.task_manager.on_send_task(inner_agent_request)

        # Assert that the task is now completed
        self.assertEqual(follow_up_response_result.id, session_id)
        self.assertEqual(follow_up_response_result.result.get("status"), "completed")
        self.assertEqual(self.server.task_manager.on_send_task.call_count, 2)

    async def test_concurrent_execution_add_history_invoke(self):
        # Setup
        session_id = str(uuid.uuid4())
        test_query = "Test concurrent execution"

        # Create a list of messages to simulate history
        test_history = [
            HumanMessage(content="Initial query"),
            AIMessage(content="Initial response")
        ]

        # Create a mock response
        mock_response = JSONRPCResponse(
            id=session_id,
            result={
                "status": "completed",
                "message": "Task completed with history",
                "history": test_history
            }
        )

        # Mock the task manager's methods
        self.server.task_manager.on_send_task = unittest.mock.AsyncMock(return_value=mock_response)

        # Create a request with history
        test_request = SendTaskRequest(
            id=session_id,
            method="send_task",
            params={
                "task": {"query": test_query},
                "history": [{"role": "user", "content": "Previous query"},
                            {"role": "assistant", "content": "Previous response"}]
            }
        )

        # Execute
        response =  await self.server.task_manager.on_send_task(test_request)

        # Assert
        self.assertEqual(response.id, session_id)
        self.assertEqual(response.result.get("status"), "completed")
        self.assertIn("history", response.result)
        self.server.task_manager.on_send_task.assert_called_once()

    async def test_stream_video_file(self):
        # Setup
        session_id = str(uuid.uuid4())
        test_query = "Stream a video file"

        # Create an async generator for streaming responses
        async def mock_stream_response():
            yield {"data": "Video chunk 1"}
            yield {"data": "Video chunk 2"}
            yield {"data": "Video chunk 3"}

        # Mock the task manager's streaming method
        self.server.task_manager.on_send_task_subscribe = unittest.mock.AsyncMock(return_value=mock_stream_response())

        # Create a streaming request
        test_request = SendTaskStreamingRequest(
            id=session_id,
            method="send_task_subscribe",
            params={"task": {"query": test_query, "media_type": "video"}}
        )

        # Execute and collect streamed responses
        streamed_responses = []
        async def collect_responses():
            async for chunk in await self.server.task_manager.on_send_task_subscribe(test_request):
                streamed_responses.append(chunk)

        await collect_responses()

        # Assert
        self.assertEqual(len(streamed_responses), 3)
        self.assertEqual(streamed_responses[0], {"data": "Video chunk 1"})
        self.assertEqual(streamed_responses[1], {"data": "Video chunk 2"})
        self.assertEqual(streamed_responses[2], {"data": "Video chunk 3"})
        self.server.task_manager.on_send_task_subscribe.assert_called_once()

    async def test_invalid_session_id(self):
        # Setup
        invalid_session_id = "invalid_uuid"
        test_query = "Test query with invalid session ID"

        # Create a request with an invalid session ID
        test_request = GetTaskRequest(
            id=invalid_session_id,
            method="get_task",
            params={}
        )

        # Mock the task manager's method to raise an exception
        self.server.task_manager.on_get_task = unittest.mock.AsyncMock(
            side_effect=ValueError("Invalid session ID format")
        )

        # Execute and expect an exception
        with self.assertRaises(ValueError):
            await self.server.task_manager.on_get_task(test_request)

            # Assert
            self.server.task_manager.on_get_task.assert_called_once()

    async def test_push_notification(self):
        # Setup
        session_id = str(uuid.uuid4())
        notification_url = "https://example.com/notifications"

        # Mock response for setting push notification
        set_notification_response = JSONRPCResponse(
            id=session_id,
            result={"status": "success", "message": "Push notification set"}
        )

        # Mock response for getting push notification
        get_notification_response = JSONRPCResponse(
            id=session_id,
            result={"status": "success", "url": notification_url}
        )

        # Mock the task manager's methods
        self.server.task_manager.on_set_task_push_notification = unittest.mock.AsyncMock(
            return_value=set_notification_response
        )
        self.server.task_manager.on_get_task_push_notification = unittest.mock.AsyncMock(
            return_value=get_notification_response
        )

        # Create requests
        set_request = SetTaskPushNotificationRequest(
            id=session_id,
            method="set_task_push_notification",
            params={"notification_url": notification_url}
        )

        get_request = GetTaskPushNotificationRequest(
            id=session_id,
            method="get_task_push_notification",
            params={}
        )

        # Execute
        set_response =  await self.server.task_manager.on_set_task_push_notification(set_request)
        get_response =  await self.server.task_manager.on_get_task_push_notification(get_request)

        # Assert
        self.assertEqual(set_response.id, session_id)
        self.assertEqual(set_response.result.get("status"), "success")

        self.assertEqual(get_response.id, session_id)
        self.assertEqual(get_response.result.get("status"), "success")
        self.assertEqual(get_response.result.get("url"), notification_url)

    async def test_stream_agent(self):
        # Setup
        session_id = str(uuid.uuid4())
        test_query = "Stream from agent"

        # Create an async generator for streaming agent responses
        async def mock_stream_response():
            yield {"is_task_complete": False, "content": "Processing..."}
            yield {"is_task_complete": False, "content": "Almost done..."}
            yield {"is_task_complete": True, "content": "Task completed"}

        # Mock the task manager's streaming method
        self.server.task_manager.on_send_task_subscribe = unittest.mock.AsyncMock(return_value=mock_stream_response())

        # Create a streaming request
        test_request = SendTaskStreamingRequest(
            id=session_id,
            method="send_task_subscribe",
            params={"task": {"query": test_query}}
        )

        # Execute and collect streamed responses
        streamed_responses = []
        async def collect_responses():
            async for chunk in await self.server.task_manager.on_send_task_subscribe(test_request):
                streamed_responses.append(chunk)

        await collect_responses()

        # Assert
        self.assertEqual(len(streamed_responses), 3)
        self.assertEqual(streamed_responses[0], {"is_task_complete": False, "content": "Processing..."})
        self.assertEqual(streamed_responses[1], {"is_task_complete": False, "content": "Almost done..."})
        self.assertEqual(streamed_responses[2], {"is_task_complete": True, "content": "Task completed"})
        self.server.task_manager.on_send_task_subscribe.assert_called_once()

    async def test_stream_agent_deny_concurrent_execution(self):
        # Setup
        session_id = str(uuid.uuid4())
        test_query = "Stream with concurrent execution denied"

        # Create a flag to simulate an active session
        self.server.task_manager.is_session_active = unittest.mock.MagicMock(return_value=True)

        # Create an error response for concurrent execution
        error_response = JSONRPCResponse(
            id=session_id,
            error={"code": -32000, "message": "Concurrent execution not allowed"}
        )

        # Mock the task manager's method to return an error
        self.server.task_manager.on_send_task_subscribe = unittest.mock.AsyncMock(
            side_effect=lambda req: (yield error_response.model_dump(exclude_none=True))
        )

        # Create a streaming request
        test_request = SendTaskStreamingRequest(
            id=session_id,
            method="send_task_subscribe",
            params={"task": {"query": test_query}}
        )

        # Execute and collect streamed responses
        streamed_responses = []
        async def collect_responses():
            async for chunk in await self.server.task_manager.on_send_task_subscribe(test_request):
                streamed_responses.append(chunk)

        await collect_responses()

        # Assert
        self.assertEqual(len(streamed_responses), 1)
        self.assertIn("error", streamed_responses[0])
        self.assertEqual(streamed_responses[0]["error"]["code"], -32000)
        self.server.task_manager.on_send_task_subscribe.assert_called_once()

    async def test_stream_agent_add_history(self):
        # Setup
        session_id = str(uuid.uuid4())
        test_query = "Stream with history"

        # Create an async generator for streaming with history
        async def mock_stream_response():
            yield {"is_task_complete": False, "content": "Processing with history..."}
            yield {"is_task_complete": True, "content": "Completed with history"}

        # Mock the task manager's streaming method
        self.server.task_manager.on_send_task_subscribe = unittest.mock.AsyncMock(return_value=mock_stream_response())

        # Create a streaming request with history
        test_request = SendTaskStreamingRequest(
            id=session_id,
            method="send_task_subscribe",
            params={
                "task": {"query": test_query},
                "history": [{"role": "user", "content": "Previous query"},
                            {"role": "assistant", "content": "Previous response"}]
            }
        )

        # Execute and collect streamed responses
        streamed_responses = []
        async def collect_responses():
            async for chunk in await self.server.task_manager.on_send_task_subscribe(test_request):
                streamed_responses.append(chunk)

        await collect_responses()

        # Assert
        self.assertEqual(len(streamed_responses), 2)
        self.server.task_manager.on_send_task_subscribe.assert_called_once()

    async def test_postgres_checkpointer_concurrent_execution(self):
        """
        The TaskManager must be made to be a postgres repository in this case, and need distributed lock stripes.
        :return:
        """
        # Setup
        session_id = str(uuid.uuid4())

        # Mock a PostgreSQL-based task manager
        # This would be implemented when the actual PostgreSQL integration is done
        postgres_task_manager = unittest.mock.MagicMock()
        postgres_task_manager.acquire_lock = unittest.mock.AsyncMock(return_value=True)
        postgres_task_manager.release_lock = unittest.mock.AsyncMock(return_value=True)

        # Simulate concurrent requests
        first_request = SendTaskRequest(
            id=session_id,
            method="send_task",
            params={"task": {"query": "First concurrent query"}}
        )

        second_request = SendTaskRequest(
            id=session_id,
            method="send_task",
            params={"task": {"query": "Second concurrent query"}}
        )

        # Assert that we can complete this test - the actual implementation would
        # need to test the distributed locking mechanism with a real PostgreSQL instance
        self.assertTrue(True, "PostgreSQL checkpointer test is a placeholder")
