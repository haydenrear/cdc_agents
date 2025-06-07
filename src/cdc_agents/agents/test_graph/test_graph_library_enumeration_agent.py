import typing
import injector
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agent.agent import A2AAgent, A2AReactAgent
from cdc_agents.agent.agent_orchestrator import TestGraphOrchestrated
from cdc_agents.agents.library_enumeration_agent import LibraryEnumerationAgent
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
from cdc_agents.model_server.model_provider import ModelProvider
from python_di.configs.autowire import injectable
from python_di.configs.component import component


@component(bind_to=[A2AAgent, A2AReactAgent, TestGraphOrchestrated])
@injectable()
class TestGraphLibraryEnumerationAgent(LibraryEnumerationAgent, TestGraphOrchestrated):
    """
    TestGraph variant of LibraryEnumerationAgent specialized for test_graph integration workflows.
    Focuses on discovering and enumerating test libraries, testing frameworks, and test dependencies.
    """

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver, model_provider: ModelProvider):
        self_card: AgentCardItem = agent_config.agents[self.__class__.__name__]
        LibraryEnumerationAgent.__init__(self, agent_config, memory_saver, model_provider)
        TestGraphOrchestrated.__init__(self, self_card)


    @property
    def agent_name(self) -> str:
        return self.__class__.__name__

    def orchestrator_prompt(self) -> str:
        """
        Override to provide test_graph specific orchestration prompt.
        """
        return """
TestGraphLibraryEnumerationAgent specializes in discovering and managing test-related libraries including:

**Core Capabilities:**
- Test framework enumeration (JUnit, TestNG, Spock, etc.)
- Testing library discovery (Mockito, AssertJ, Testcontainers, etc.)
- Test dependency analysis and resolution
- Test utility library identification
- Integration testing framework detection

**Test Context Focus:**
- Identifies testing dependencies for test_graph projects
- Discovers integration testing frameworks
- Enumerates mock and stub libraries
- Finds test data generation tools
- Locates performance testing libraries

**Usage in TestGraph:**
- Call before test dependency setup
- Use for test environment preparation
- Employ for test library compatibility checks
- Utilize for test framework selection

**Test-Specific Library Categories:**
- Unit testing frameworks
- Integration testing tools
- Mocking and stubbing libraries
- Test data generators
- Performance and load testing tools
- API testing frameworks
- Database testing utilities

The agent prioritizes test-related libraries and provides comprehensive enumeration
of testing dependencies required for robust test_graph integration workflows.
"""

    def completion_definition(self) -> str:
        """
        Define completion criteria for test_graph library enumeration tasks.
        """
        return """
TestGraphLibraryEnumerationAgent completes when:
1. All relevant test libraries and frameworks have been discovered
2. Test dependencies are properly catalogued and categorized
3. Library compatibility for test_graph workflows is verified
4. Test framework requirements are documented for downstream agents
5. Integration testing library availability is confirmed
"""
