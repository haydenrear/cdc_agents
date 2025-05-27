import unittest.mock
import uuid

from langchain_core.messages import ToolMessage
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agents.deep_code_research_agent import DeepCodeOrchestrator
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


@test_booter(scan_root_module=AgentConfig)
class ServerRunnerBoot:
    pass

@boot_test(ctx=ServerRunnerBoot)
class ModelServerModelTest(unittest.IsolatedAsyncioTestCase):
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
        ModelServerModelTest.memory = memory_saver
        ModelServerModelTest.ai_suite = ai_suite
        ModelServerModelTest.server = server
        ModelServerModelTest.model = model
        ModelServerModelTest.model_provider = model_provider

    async def test_model_server_model(self):

        orchestrator_responses = [
            "STATUS: goto_agent\nNEXT AGENT: TestA2AAgent\nADDITIONAL CONTEXT: hello!!!\n\nokay!!!",
            """
            Action: test_tool
            Action Input: 
            """,
            "STATUS: goto_agent\nNEXT AGENT: TestA2AAgent\nADDITIONAL CONTEXT: hello!!!\n\nokay!!!",
            # """
            # Action: test_tool
            # Action Input:
            # """,
            """
            Action: query
            Action Input: { "sql": "SELECT * FROM commit_diff" }
            """,
            "STATUS: completed\nokay",
            "STATUS: goto_agent\nNEXT AGENT: TestA2AAgent\nADDITIONAL CONTEXT: hello!!!\n\nokay!!!",
            """
            Action: test_tool
            Action Input: 
            """,
            "STATUS: goto_agent\nNEXT AGENT: TestA2AAgent\nADDITIONAL CONTEXT: hello!!!\n\nokay!!!",
            "STATUS: completed\nhello!",
            "status: goto_agent\nTestA2AAgent",
            "okay",
            "status: goto_agent\nTestA2AAgent",
            """
            Action: test_tool
            Action Input: 
            """,
            "status: completed\nhello!"
        ]


        # Create a test orchestrator setup with our fixtures
        orchestrator, task_manager = create_test_orchestrator(
            self.ai_suite,
            self.memory,
            self.model_provider,
            self.model,
            orchestrator_responses,
            self.server
        )


        test = str(uuid.uuid4())
        # Invoke the orchestrator
        graph_response = orchestrator.invoke({"messages": ("user", "hello")}, test)
        
        # Check the results
        invoked = graph_response.content.history
        
        assert len(invoked) != 0
        assert any([isinstance(i, ToolMessage) and i.status == 'success' for i in invoked])
        assert any([i.content[-1].endswith('okay') for i in invoked])
        assert any([i.content == 'hello...' for i in invoked if isinstance(i, ToolMessage)])
        assert any([i.content[-1] == 'STATUS: completed\nokay' for i in invoked])

        assert not any([i.status != 'success' for i in invoked if isinstance(i, ToolMessage)])

        assert graph_response.is_task_complete
        
        assert invoked[-1].content[-1] == 'STATUS: completed\nokay'
        
        assert TestOrchestratorAgent.did_call
        assert TestA2AAgent.did_call
        
        TestOrchestratorAgent.reset_tracking()
        TestA2AAgent.reset_tracking()
        
        invoked_second = orchestrator.invoke("hello", test).content.history
        assert TestOrchestratorAgent.did_call
        assert TestA2AAgent.did_call
        assert len(invoked_second) > len(invoked)
        
        TestOrchestratorAgent.reset_tracking()
        TestA2AAgent.reset_tracking()
        
        invoked_third = orchestrator.invoke("hello", str(uuid.uuid4())).content.history
        assert TestOrchestratorAgent.did_call
        assert len(invoked_third) <= len(invoked)


