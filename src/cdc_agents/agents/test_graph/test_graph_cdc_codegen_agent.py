import typing
import injector
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agent.agent import A2AAgent, A2AReactAgent
from cdc_agents.agent.agent_orchestrator import TestGraphOrchestrated
from cdc_agents.agents.cdc_server_agent import CdcCodegenAgent, CdcServerAgentToolCallProvider
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
from cdc_agents.config.cdc_server_config_props import CdcServerConfigProps
from cdc_agents.model_server.model_provider import ModelProvider
from python_di.configs.autowire import injectable
from python_di.configs.component import component


@component(bind_to=[A2AAgent, A2AReactAgent, TestGraphOrchestrated])
@injectable()
class TestGraphCdcCodegenAgent(CdcCodegenAgent, TestGraphOrchestrated):
    """
    TestGraph variant of CdcCodegenAgent specialized for test_graph integration workflows.
    Focuses on generating test code, test configurations, and test-specific implementations.
    """

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver,
                 model_provider: ModelProvider, cdc_server: CdcServerConfigProps,
                 tool_call_provider: CdcServerAgentToolCallProvider):
        self_card: AgentCardItem = agent_config.agents[self.__class__.__name__]
        CdcCodegenAgent.__init__(self, agent_config, memory_saver, model_provider, cdc_server, tool_call_provider)
        TestGraphOrchestrated.__init__(self, self_card)

    def orchestrator_prompt(self) -> str:
        """
        Override to provide test_graph specific orchestration prompt.
        """
        return """
TestGraphCdcCodegenAgent specializes in generating test-related code and configurations for test_graph workflows including:

**Core Capabilities:**
- Integration test code generation
- Test configuration and setup code creation
- Test data generation and mock creation
- Test utility and helper method generation
- Test assertion and validation code creation
- Test-specific schema and model generation

**Test Context Focus:**
- Generates comprehensive integration test suites
- Creates test-specific data models and fixtures
- Produces test configuration files and setup scripts
- Generates mock services and stub implementations
- Creates test validation and assertion utilities
- Produces test documentation and specifications

**Usage in TestGraph:**
- Call for test code generation phases
- Use for test configuration creation
- Employ for test data and mock generation
- Utilize for test utility development

**Test Code Generation Categories:**
- Unit test generation with proper assertions
- Integration test suite creation
- End-to-end test scenario generation
- Performance and load test code creation
- Security and compliance test generation
- API contract test implementation

**Test Configuration Generation:**
- Test environment configuration files
- Test database setup and migration scripts
- Test service configuration and properties
- Test data seeding and fixture creation
- Test container and orchestration configs
- Test CI/CD pipeline configurations

**Test Data and Mocks:**
- Test data fixture generation
- Mock service implementation creation
- Stub and fake object generation
- Test database schema and seed data
- Test API response mocking
- Test event and message simulation

**Code Quality and Standards:**
- Test code follows best practices and patterns
- Proper test isolation and cleanup
- Comprehensive test coverage generation
- Test code documentation and comments
- Test maintainability and readability
- Test performance optimization

**Integration with CDC:**
- Leverages CDC schema for test data generation
- Uses commit diff context for targeted test creation
- Integrates with CDC workflows for test automation
- Supports CDC-based test validation and verification

The agent ensures high-quality, comprehensive test code generation that integrates
seamlessly with test_graph workflows and CDC-based development processes.
"""

    def completion_definition(self) -> str:
        """
        Define completion criteria for test_graph code generation tasks.
        """
        return """
TestGraphCdcCodegenAgent completes when:
1. All requested test code has been generated successfully
2. Test configurations and setup files are created
3. Test data fixtures and mocks are properly implemented
4. Generated test code passes validation and compilation
5. Test code is properly integrated with existing test framework
6. Test documentation and specifications are generated
7. Generated code follows established testing patterns and standards
8. Code is saved and versioned in the appropriate repositories
"""
