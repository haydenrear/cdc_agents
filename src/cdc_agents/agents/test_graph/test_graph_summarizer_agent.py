import typing
import injector
from langchain_core.messages import BaseMessage
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agent.agent import A2AAgent, A2AReactAgent
from cdc_agents.agent.agent_orchestrator import TestGraphOrchestrated
from cdc_agents.agents.summarizer_agent import SummarizerAgent
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
from cdc_agents.model_server.model_provider import ModelProvider
from python_di.configs.autowire import injectable
from python_di.configs.component import component


@component(bind_to=[A2AAgent, A2AReactAgent, TestGraphOrchestrated])
@injectable()
class TestGraphSummarizerAgent(SummarizerAgent, TestGraphOrchestrated):
    """
    TestGraph variant of SummarizerAgent specialized for test_graph integration workflows.
    Focuses on summarizing test execution results, build outputs, and service status.
    """

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver, model_provider: ModelProvider):
        # Get configuration for this specific TestGraph agent
        self_card: AgentCardItem = agent_config.agents[self.__class__.__name__]

        # Initialize TestGraphOrchestrated interface
        TestGraphOrchestrated.__init__(self, self_card)

        # Initialize base SummarizerAgent with TestGraph-specific configuration
        A2AReactAgent.__init__(self, agent_config, [],
                              self_card.agent_descriptor.system_prompts,
                              memory_saver, model_provider)

    @property
    def agent_name(self) -> str:
        return self.__class__.__name__

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

    def orchestrator_prompt(self) -> str:
        """
        Override to provide test_graph specific orchestration prompt.
        """
        return """
TestGraphSummarizerAgent specializes in summarizing test_graph workflow outputs including:

**Core Capabilities:**
- Test execution result summarization
- Build and deployment status consolidation
- Service health and error analysis
- Integration test outcome reporting
- Validation result compilation

**Test Context Focus:**
- Preserves critical test execution data
- Highlights build failures and successes
- Tracks service dependency status
- Maintains error context for debugging

**Usage in TestGraph:**
- Call after test execution phases
- Use for consolidating build outputs
- Employ for service status reporting
- Utilize for final workflow summaries

The agent optimizes for test-relevant information retention and provides concise summaries
that maintain essential debugging and validation context for test_graph workflows.
"""

    def completion_definition(self) -> str:
        """
        Define completion criteria for test_graph summarization tasks.
        """
        return """
TestGraphSummarizerAgent completes when:
1. All requested test-related content has been summarized
2. Key test results, errors, and status information are preserved
3. Summary maintains essential context for test workflow decisions
4. Output is formatted for consumption by other test_graph agents
"""
