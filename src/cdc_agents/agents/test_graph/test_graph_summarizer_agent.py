import typing
import injector
from langchain_core.messages import BaseMessage
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agent.agent import A2AAgent, A2AReactAgent
from cdc_agents.agent.agent_orchestrator import TestGraphOrchestrated
from cdc_agents.agents.summarizer_agent import SummarizerBaseAgent
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
from cdc_agents.model_server.model_provider import ModelProvider
from python_di.configs.autowire import injectable
from python_di.configs.component import component


# @component(bind_to=[A2AAgent, A2AReactAgent, TestGraphOrchestrated])
# @injectable()
class TestGraphSummarizerAgent(SummarizerBaseAgent, TestGraphOrchestrated):
    """
    TestGraph variant of SummarizerAgent specialized for test_graph integration workflows.
    Focuses on summarizing test execution results, build outputs, and service status.
    """

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver, model_provider: ModelProvider):
        SummarizerBaseAgent.__init__(self, agent_config, memory_saver, model_provider, TestGraphOrchestrated)

    def do_collapse(self, message_state: list[BaseMessage], config) -> list[BaseMessage]:
        """
        Override collapse behavior for test_graph context.
        Focus on preserving test results, build status, and error information.
        """
        # Filter messages to preserve test-critical information
        test_critical_keywords = [
            "test", "build", "deploy", "service", "error", "failure", "success",
            "integration", "validation", "health", "status", "result"
        ]

        preserved_messages = []
        for message in message_state:
            content = str(message.content).lower()
            if any(keyword in content for keyword in test_critical_keywords):
                preserved_messages.append(message)

        # If we preserved too few messages, fall back to parent behavior
        if len(preserved_messages) < 2:
            return super().do_collapse(message_state, config)

        # Use parent collapse logic on filtered messages
        return super().do_collapse(preserved_messages, config)
