import unittest
import unittest.mock
import asyncio
import copy
import typing
import uuid
from typing import Any, List, Dict, Optional, AsyncIterable, Union, Callable

from aisuite.framework import ChatCompletionResponse
from langchain_core.callbacks import Callbacks
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, BaseMessage
from langchain_core.runnables.config import RunnableConfig
from langchain_core.tools import BaseTool, StructuredTool, tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent

from cdc_agents.agent.a2a import A2AAgent
from cdc_agents.agent.agent import A2AReactAgent
from cdc_agents.agent.agent_orchestrator import OrchestratorAgent, OrchestratedAgent
from cdc_agents.agent.task_manager import AgentTaskManager
from cdc_agents.common.types import Message, TextPart, AgentGraphResponse, JSONRPCResponse
from cdc_agents.common.utils.push_notification_auth import PushNotificationSenderAuth
from cdc_agents.config.agent_config_props import AgentConfigProps
from cdc_agents.config.model_server_config_props import ModelServerConfigProps
from cdc_agents.model_server.model_provider import ModelProvider
from cdc_agents.model_server.model_server_model import ModelServerModel, ModelServerInput

# Tool for testing
@tool
def test_tool() -> str:
    """Test tool that returns a simple message"""
    return "hello..."

class MockExecutor:
    """Mock executor for model server"""
    def __init__(self, responses: List[str]):
        self.iter_res = iter(responses)

    def call(self, *args, **kwargs):
        next_res = next(self.iter_res)
        return next_res

        
    def get_config_props(self) -> ModelServerConfigProps:
        return ModelServerConfigProps()

def create_mock_model(model: ModelServerModel, responses: List[str]) -> ModelServerModel:
    """Create a mock model with controlled responses"""
    mock_model = copy.copy(model)
    mock_executor = MockExecutor(responses)
    mock_model.executor = mock_executor
    return mock_model

def get_query(query) :
    if isinstance(query, str):
        query = {"messages": [("user", query)]}
    return query

class TestStreamingAgent(A2AReactAgent):
    """Agent for testing streaming responses"""
    SUPPORTED_CONTENT_TYPES = ["text"]
    _agent_name = "TestStreamingAgent"
    
    @property
    def supported_content_types(self) -> list[str]:
        return self.SUPPORTED_CONTENT_TYPES
    
    @staticmethod
    def get_mock_responses():
        """Default mock responses for streaming"""
        return [
            "I'm processing your request...",
            "Still working on it...",
            "status: completed\nTask completed successfully"
        ]

class VideoStreamingAgent(A2AReactAgent):
    """Agent for testing video streaming responses"""
    SUPPORTED_CONTENT_TYPES = ["text", "video"]
    _agent_name = "VideoStreamingAgent"
    
    @property
    def supported_content_types(self) -> list[str]:
        return self.SUPPORTED_CONTENT_TYPES
    
    @staticmethod
    def get_mock_responses():
        """Default mock responses for video streaming"""
        return [
            "Starting video stream...",
            "Processing video data...",
            "Video chunk processed",
            "status: completed\nVideo streaming complete"
        ]

class TestA2AAgent(A2AReactAgent):
    """Test React Agent with tracking of invocations"""
    did_call = False
    _agent_name = "TestA2AAgent"
    SUPPORTED_CONTENT_TYPES = ["text"]
    
    @property
    def supported_content_types(self) -> list[str]:
        return self.SUPPORTED_CONTENT_TYPES
    
    def invoke(self, query, sessionId) -> Dict[str, Any]:
        TestA2AAgent.did_call = True
        return super().invoke(get_query(query), sessionId)
    
    @staticmethod
    def reset_tracking():
        """Reset the tracking flag"""
        TestA2AAgent.did_call = False

class TestOrchestratorAgent(A2AReactAgent, OrchestratorAgent):
    """Test Orchestrator Agent with tracking of invocations"""
    did_call = False
    _agent_name = "TestOrchestratorAgent"
    SUPPORTED_CONTENT_TYPES = ["text"]

    @property
    def orchestration_prompt(self):
        return ""

    @property
    def orchestrator_system_prompts(self):
        return ""

    @property
    def supported_content_types(self) -> list[str]:
        return self.SUPPORTED_CONTENT_TYPES
    
    def invoke(self, query, sessionId) -> Dict[str, Any]:
        TestOrchestratorAgent.did_call = True
        invoked_value = super().invoke(query, sessionId)
        return invoked_value
    
    @staticmethod
    def reset_tracking():
        """Reset the tracking flag"""
        TestOrchestratorAgent.did_call = False

def create_test_agent_task_manager(
    ai_suite: AgentConfigProps,
    memory: MemorySaver,
    model_provider: ModelProvider,
    model: ModelServerModel,
    responses: List[str],
    agent_class=TestA2AAgent
) -> tuple[A2AReactAgent, AgentTaskManager]:
    """Create a test agent and task manager with mocked responses"""
    mock_model = create_mock_model(model, responses)
    tools = [test_tool]

    ai_suite.agents[agent_class.__name__] = next(iter(ai_suite.agents.values()))

    test_agent = agent_class(ai_suite, tools, "Test system instruction", 
                            memory, model_provider, mock_model)
    
    # Create notification auth
    # Create a real task manager with our test agent
    notification_auth = PushNotificationSenderAuth()
    notification_auth.generate_jwk()
    mock_push_notification_auth(notification_auth)
    
    # Create task manager
    task_manager = AgentTaskManager(test_agent, notification_auth)
    test_agent.set_task_manager(task_manager)
    
    # Build the agent's graph if needed
    if not hasattr(test_agent, 'graph') or test_agent.graph is None:
        test_agent.graph = create_react_agent(
            test_agent.model, tools=test_agent.tools, checkpointer=memory,
            prompt=test_agent.system_prompts
        )
    
    return test_agent, task_manager

from cdc_agents.agents.deep_code_research_agent import DeepCodeOrchestrator, DeepCodeAgent

def create_test_streaming_task_manager(
    ai_suite: AgentConfigProps,
    memory: MemorySaver,
    model_provider: ModelProvider,
    model: ModelServerModel,
    orchestrator: DeepCodeOrchestrator,
    responses: List[str] = None,
) -> tuple[TestStreamingAgent, AgentTaskManager]:
    """Create a test streaming agent and task manager"""
    if responses is None:
        responses = TestStreamingAgent.get_mock_responses()
    
    # Use the standard test agent creator but with the streaming agent class
    return create_test_agent_task_manager(
        ai_suite, memory, model_provider, model, responses, TestStreamingAgent
    )


def create_test_orchestrator(
    ai_suite: AgentConfigProps,
    memory: MemorySaver,
    model_provider: ModelProvider,
    model: ModelServerModel,
    orchestrator_responses: List[str],
    orchestrator: DeepCodeOrchestrator,
    agent_responses: typing.Optional[List[str]] = None
) -> tuple[DeepCodeOrchestrator, AgentTaskManager]:
    """Create a test orchestrator with inner agents"""

    # Reset the tracking for both agent types
    TestA2AAgent.reset_tracking()
    TestOrchestratorAgent.reset_tracking()
    
    mock_orchestrator_model = create_mock_model(model, orchestrator_responses)

    if agent_responses is not None:
        mock_agent_model = create_mock_model(model, agent_responses)
    else:
        mock_agent_model = mock_orchestrator_model

    tools = [test_tool]
    
    # Create the orchestrator
    ai_suite.agents['TestOrchestratorAgent'] = next(iter(ai_suite.agents.values()))
    orchestrator_agent = TestOrchestratorAgent(
        ai_suite, tools, "Test orchestrator instruction", 
        memory, model_provider, mock_orchestrator_model
    )

    ai_suite.agents['TestA2AAgent'] = next(iter(ai_suite.agents.values()))
    # Create an inner agent
    inner_agent = TestA2AAgent(
        ai_suite, tools, "Test agent instruction", 
        memory, model_provider, mock_agent_model
    )

    # Create notification auth
    notification_auth = PushNotificationSenderAuth()
    notification_auth.generate_jwk()
    mock_push_notification_auth(notification_auth)
    
    # Create task managers for the inner agent
    inner_task_manager = AgentTaskManager(inner_agent, notification_auth)
    inner_agent.set_task_manager(inner_task_manager)


    # Create orchestrated agents dict
    agents = {
        "TestA2AAgent": OrchestratedAgent(inner_agent)
    }
    
    # Modify the orchestrator to use these agents
    orchestrator.orchestrator_agent = orchestrator_agent
    orchestrator.agents = agents
    orchestrator.graph = orchestrator._build_graph()

    orchestrator.orchestrator_agent._create_graph(ai_suite.agents['CdcCodegenAgent'].mcp_tools)
    orchestrator.agents['TestA2AAgent'].agent._create_graph(ai_suite.agents['CdcCodegenAgent'].mcp_tools)

    # Create task manager for the orchestrator
    orchestrator_task_manager = AgentTaskManager(orchestrator, notification_auth)
    orchestrator.set_task_manager(orchestrator_task_manager)
    orchestrator_agent.set_task_manager(orchestrator_task_manager)
    
    return orchestrator, orchestrator_task_manager

def mock_push_notification_auth(auth: PushNotificationSenderAuth):
    """Mock the push notification auth to avoid actual HTTP requests"""
    auth.verify_push_notification_url = unittest.mock.AsyncMock(return_value=True)
    auth.send_push_notification = unittest.mock.AsyncMock(return_value=True)
    return auth

def create_text_message(text: str) -> Message:
    """Create a simple text message for testing"""
    return Message(
        role="user",
        parts=[TextPart(type="text", text=text)]
    )

def create_video_streaming_task_manager(
    ai_suite: AgentConfigProps,
    memory: MemorySaver,
    model_provider: ModelProvider,
    model: ModelServerModel,
    responses: List[str] = None
) -> tuple[VideoStreamingAgent, AgentTaskManager]:
    """Create a test video streaming agent and task manager"""
    if responses is None:
        responses = VideoStreamingAgent.get_mock_responses()
    
    # Use the standard test agent creator but with the video streaming agent class
    return create_test_agent_task_manager(
        ai_suite, memory, model_provider, model, responses, VideoStreamingAgent
    )