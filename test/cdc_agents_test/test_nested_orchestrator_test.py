import unittest.mock
import uuid
from typing import List, Optional, Dict, Any

from langchain_core.messages import ToolMessage, AIMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agent.agent import A2AAgent
from cdc_agents.agent.agent_orchestrator import DeepResearchOrchestrated, OrchestratedAgent
from cdc_agents.agents.deep_code_research_agent import DeepCodeOrchestrator
from cdc_agents.agents.test_graph.test_graph_agent_orchestrator import TestGraphAgent, TestGraphOrchestrator
from cdc_agents.common.types import ResponseFormat, AgentGraphResponse
from cdc_agents.config.agent_config import AgentConfig
from cdc_agents.config.agent_config_props import AgentConfigProps
from cdc_agents.model_server.model_provider import ModelProvider
from cdc_agents.model_server.model_server_model import ModelServerModel
from cdc_agents_test.fixtures.agent_fixtures import (
    create_test_orchestrator, TestA2AAgent, TestOrchestratorAgent
)
from python_di.configs.bean import test_inject
from python_di.configs.test import test_booter, boot_test
from python_di.inject.profile_composite_injector.inject_context_di import autowire_fn


# Create test agents that support test_graph
class TestGraphSupportAgent(TestA2AAgent):
    """Test agent that supports test_graph operations"""

    @property
    def supports_test_graph(self) -> bool:
        return True

    def invoke(self, query, sessionId) -> AgentGraphResponse:
        response = super().invoke(query, sessionId)
        # Simulate test graph specific operations
        if isinstance(response.content, ResponseFormat):
            response.content.message = f"Test graph operation: {response.content.message}"
        return response


class MockTestGraphAgent(TestGraphAgent):
    """Mock version of TestGraphAgent for testing"""

    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver,
                 agents: List[DeepResearchOrchestrated], model_provider: ModelProvider):
        # Use minimal initialization for testing
        self.agent_config = agent_config
        self.memory = memory_saver
        self.model_provider = model_provider
        self._agent_name = self.__class__.__name__
        self.agents = {a.agent_name: a for a in agents if hasattr(a, 'supports_test_graph') and a.supports_test_graph}
        self.did_call = False
        self.call_count = 0

    def invoke(self, query, sessionId) -> AgentGraphResponse:
        self.did_call = True
        self.call_count += 1

        # Simulate test graph workflow
        content = ResponseFormat(
            message="Executing test graph workflow",
            status="goto_agent" if self.call_count < 3 else "completed",
            route_to="TestGraphSupportAgent" if self.call_count < 3 else None,
            history=[
                AIMessage(content=f"Test graph step {self.call_count}", name=self.agent_name)
            ]
        )

        # Add test graph metadata
        content.test_graph_metadata = {
            "orchestrator": self.agent_name,
            "supports_propagation": True,
            "is_sub_graph": True
        }

        # Update execution state
        content.test_graph_execution_state = {
            "code_generated": self.call_count >= 1,
            "dependencies_built": self.call_count >= 2,
            "services_running": self.call_count >= 2,
            "tests_executed": self.call_count >= 3,
            "results_validated": self.call_count >= 3
        }

        is_complete = self.call_count >= 3

        return AgentGraphResponse(
            is_task_complete=is_complete,
            require_user_input=False,
            content=content
        )


class MockTestGraphOrchestrator(TestGraphOrchestrator):
    """Mock version of TestGraphOrchestrator for testing"""

    def __init__(self, agents: List[DeepResearchOrchestrated], orchestrator_agent: TestGraphAgent,
                 props: AgentConfigProps, memory_saver: MemorySaver, model_provider: ModelProvider):
        # Use minimal initialization
        self.agents = {a.agent_name: OrchestratedAgent(a) for a in agents if hasattr(a, 'supports_test_graph')}
        self.orchestrator_agent = orchestrator_agent
        self.memory = memory_saver
        self._agent_name = self.__class__.__name__
        self.props = props
        self.model_provider = model_provider
        self._test_execution_state = {
            "code_generated": False,
            "dependencies_built": False,
            "services_running": False,
            "tests_executed": False,
            "results_validated": False
        }
        self.invocation_count = 0

    def invoke(self, query, sessionId) -> AgentGraphResponse:
        self.invocation_count += 1

        # Simulate orchestration of test graph workflow
        if self.invocation_count <= 3:
            # Delegate to test graph agent
            result = self.orchestrator_agent.invoke(query, sessionId)

            # Update execution state based on agent response
            if hasattr(result.content, 'test_graph_execution_state'):
                self._test_execution_state.update(result.content.test_graph_execution_state)

            return result
        else:
            # Complete and return to parent
            content = ResponseFormat(
                message="Test graph orchestration complete",
                status="completed",
                route_to=None,
                history=[
                    AIMessage(content="All test phases completed successfully", name=self.agent_name)
                ]
            )

            # Add propagation information
            content.propagation_prompt = self.orchestrator_propagator_prompt()
            content.from_sub_orchestrator = self.agent_name
            content.test_graph_execution_state = self._test_execution_state

            return AgentGraphResponse(
                is_task_complete=True,
                require_user_input=False,
                content=content
            )


@test_booter(scan_root_module=AgentConfig)
class NestedOrchestratorTestBoot:
    pass


@boot_test(ctx=NestedOrchestratorTestBoot)
class NestedOrchestratorTest(unittest.IsolatedAsyncioTestCase):
    ai_suite: AgentConfigProps
    server: DeepCodeOrchestrator
    model: ModelServerModel
    memory: MemorySaver
    model_provider: ModelProvider

    @test_inject(profile='test')
    @autowire_fn(profile='test')
    def construct(self,
                  ai_suite: AgentConfigProps,
                  server: DeepCodeOrchestrator,
                  model: ModelServerModel,
                  memory_saver: MemorySaver,
                  model_provider: ModelProvider):
        NestedOrchestratorTest.memory = memory_saver
        NestedOrchestratorTest.ai_suite = ai_suite
        NestedOrchestratorTest.server = server
        NestedOrchestratorTest.model = model
        NestedOrchestratorTest.model_provider = model_provider

    # async def test_nested_orchestrator_with_propagation(self):
    #     """Test that nested orchestrators properly propagate results to parent"""
    #
    #     # Create test agents
    #     test_graph_support_agent = TestGraphSupportAgent(self.ai_suite, self.memory, self.model_provider, self.model)
    #     test_graph_agent = MockTestGraphAgent(self.ai_suite, self.memory, [test_graph_support_agent], self.model_provider)
    #     test_graph_orchestrator = MockTestGraphOrchestrator(
    #         [test_graph_support_agent], test_graph_agent, self.ai_suite, self.memory, self.model_provider
    #     )
    #
    #     # Orchestrator responses that include routing to test graph orchestrator
    #     orchestrator_responses = [
    #         "STATUS: goto_agent\nNEXT AGENT: TestA2AAgent\nADDITIONAL CONTEXT: Starting workflow",
    #         "STATUS: goto_agent\nNEXT AGENT: MockTestGraphOrchestrator\nADDITIONAL CONTEXT: Running test graph validation",
    #         """
    #         Action: review_business_requirement
    #         Action Input:
    #         """,
    #         "STATUS: completed\nTest graph validation complete, all tests passed",
    #     ]
    #
    #     # Create test orchestrator with test graph orchestrator included
    #     orchestrator, task_manager = create_test_orchestrator(
    #         self.ai_suite,
    #         self.memory,
    #         self.model_provider,
    #         self.model,
    #         orchestrator_responses,
    #         self.server,
    #         additional_agents=[test_graph_orchestrator]
    #     )
    #
    #     test_session = str(uuid.uuid4())
    #
    #     # Invoke the orchestrator
    #     graph_response = orchestrator.invoke({"messages": ("user", "validate system with test graph")}, test_session)
    #
    #     # Verify results
    #     assert graph_response.is_task_complete
    #
    #     invoked = graph_response.content.history
    #
    #     # Check that test graph orchestrator was called
    #     assert any([msg.name == 'MockTestGraphOrchestrator' for msg in invoked if hasattr(msg, 'name')])
    #
    #     # Check for propagation messages
    #     assert any(['Sub-orchestrator' in msg.content for msg in invoked if isinstance(msg, SystemMessage)])
    #     assert any(['TestGraphOrchestrator has completed' in msg.content for msg in invoked if hasattr(msg, 'content')])
    #
    #     # Verify execution state was tracked
    #     assert test_graph_orchestrator._test_execution_state['tests_executed']
    #     assert test_graph_orchestrator._test_execution_state['results_validated']
    #
    # async def test_sub_orchestrator_response_handling(self):
    #     """Test that _do_get_res properly handles sub-orchestrator responses"""
    #
    #     # Create a mock sub-orchestrator response
    #     sub_response = ResponseFormat(
    #         message="Sub-orchestrator task complete",
    #         status="completed",
    #         history=[AIMessage(content="Test completed", name="TestGraphOrchestrator")]
    #     )
    #
    #     # Add sub-orchestrator metadata
    #     sub_response.test_graph_execution_state = {
    #         "code_generated": True,
    #         "dependencies_built": True,
    #         "services_running": True,
    #         "tests_executed": True,
    #         "results_validated": True
    #     }
    #     sub_response.from_sub_orchestrator = "TestGraphOrchestrator"
    #     sub_response.propagation_prompt = "Test execution complete, all validations passed"
    #
    #     # Create test agent
    #     test_agent = TestA2AAgent(self.ai_suite, self.memory, self.model_provider, self.model)
    #
    #     # Create mock values for _do_get_res
    #     values = {
    #         'messages': [
    #             HumanMessage(content="Start test"),
    #             AIMessage(content=sub_response, name="TestGraphOrchestrator",
    #                      additional_kwargs={'is_sub_orchestrator': True})
    #         ]
    #     }
    #
    #     # Process response
    #     result = test_agent._do_get_res(values)
    #
    #     # Verify sub-orchestrator response was handled correctly
    #     assert result.is_task_complete  # Should be complete based on execution state
    #     assert hasattr(result.content, 'sub_orchestrator_metadata')
    #
    # async def test_nested_orchestrator_error_handling(self):
    #     """Test error handling in nested orchestrator scenarios"""
    #
    #     # Create test graph agent that simulates failure
    #     class FailingTestGraphAgent(MockTestGraphAgent):
    #         def invoke(self, query, sessionId) -> AgentGraphResponse:
    #             content = ResponseFormat(
    #                 message="Critical failure in test execution",
    #                 status="error",
    #                 route_to=None,
    #                 history=[AIMessage(content="Test execution failed", name=self.agent_name)]
    #             )
    #
    #             return AgentGraphResponse(
    #                 is_task_complete=False,
    #                 require_user_input=True,
    #                 content=content
    #             )
    #
    #     failing_agent = FailingTestGraphAgent(self.ai_suite, self.memory, [], self.model_provider)
    #     test_graph_orchestrator = MockTestGraphOrchestrator(
    #         [], failing_agent, self.ai_suite, self.memory, self.model_provider
    #     )
    #
    #     # Override to return error immediately
    #     test_graph_orchestrator.invocation_count = 4  # Force error state
    #
    #     orchestrator_responses = [
    #         "STATUS: goto_agent\nNEXT AGENT: MockTestGraphOrchestrator\nADDITIONAL CONTEXT: Running test validation",
    #         "STATUS: error\nTest graph validation failed, manual intervention required",
    #     ]
    #
    #     orchestrator, _ = create_test_orchestrator(
    #         self.ai_suite,
    #         self.memory,
    #         self.model_provider,
    #         self.model,
    #         orchestrator_responses,
    #         self.server,
    #         additional_agents=[test_graph_orchestrator]
    #     )
    #
    #     test_session = str(uuid.uuid4())
    #
    #     # Invoke orchestrator
    #     graph_response = orchestrator.invoke("run tests", test_session)
    #
    #     # Verify error was handled
    #     assert graph_response.require_user_input
    #     assert not graph_response.is_task_complete
    #
    # async def test_multiple_nested_orchestrators(self):
    #     """Test handling of multiple nested orchestrators in the same workflow"""
    #
    #     # Create two different test graph orchestrators
    #     test_agent1 = MockTestGraphAgent(self.ai_suite, self.memory, [], self.model_provider)
    #     test_orchestrator1 = MockTestGraphOrchestrator(
    #         [], test_agent1, self.ai_suite, self.memory, self.model_provider
    #     )
    #     test_orchestrator1._agent_name = "TestGraphOrchestrator1"
    #
    #     test_agent2 = MockTestGraphAgent(self.ai_suite, self.memory, [], self.model_provider)
    #     test_orchestrator2 = MockTestGraphOrchestrator(
    #         [], test_agent2, self.ai_suite, self.memory, self.model_provider
    #     )
    #     test_orchestrator2._agent_name = "TestGraphOrchestrator2"
    #
    #     orchestrator_responses = [
    #         "STATUS: goto_agent\nNEXT AGENT: TestGraphOrchestrator1\nADDITIONAL CONTEXT: First validation",
    #         "STATUS: goto_agent\nNEXT AGENT: TestGraphOrchestrator2\nADDITIONAL CONTEXT: Second validation",
    #         "STATUS: completed\nBoth validations complete",
    #     ]
    #
    #     orchestrator, _ = create_test_orchestrator(
    #         self.ai_suite,
    #         self.memory,
    #         self.model_provider,
    #         self.model,
    #         orchestrator_responses,
    #         self.server,
    #         additional_agents=[test_orchestrator1, test_orchestrator2]
    #     )
    #
    #     test_session = str(uuid.uuid4())
    #
    #     # Invoke orchestrator
    #     graph_response = orchestrator.invoke("run all validations", test_session)
    #
    #     # Verify both orchestrators were called
    #     assert graph_response.is_task_complete
    #     assert test_orchestrator1.invocation_count > 0
    #     assert test_orchestrator2.invocation_count > 0
