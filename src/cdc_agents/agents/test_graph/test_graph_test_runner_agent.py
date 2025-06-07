import typing
import injector
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agent.agent import A2AAgent, A2AReactAgent
from cdc_agents.agent.agent_orchestrator import TestGraphOrchestrated
from cdc_agents.agents.cdc_server_agent import CdcServerAgentToolCallProvider
from cdc_agents.agents.test_runner_agent import TestRunnerAgent
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
from cdc_agents.config.cdc_server_config_props import CdcServerConfigProps
from cdc_agents.model_server.model_provider import ModelProvider
from cdc_agents.tools.tool_call_decorator import ToolCallDecorator
from python_di.configs.autowire import injectable
from python_di.configs.component import component


@component(bind_to=[A2AAgent, A2AReactAgent, TestGraphOrchestrated])
@injectable()
class TestGraphTestRunnerAgent(TestRunnerAgent, TestGraphOrchestrated):
    """
    TestGraph variant of TestRunnerAgent specialized for test_graph integration workflows.
    Focuses on executing integration tests, test suites, and validation workflows.
    """

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver, model_provider: ModelProvider,
                 cdc_server: CdcServerConfigProps, tool_call_provider: ToolCallDecorator):
        self_card: AgentCardItem = agent_config.agents[self.__class__.__name__]
        TestRunnerAgent.__init__(self, agent_config, memory_saver, model_provider, cdc_server, tool_call_provider)
        TestGraphOrchestrated.__init__(self, self_card)

    def orchestrator_prompt(self) -> str:
        """
        Override to provide test_graph specific orchestration prompt.
        """
        return """
TestGraphTestRunnerAgent specializes in test execution for test_graph workflows including:

**Core Capabilities:**
- Integration test suite execution
- End-to-end test workflow orchestration
- Test environment validation and setup
- Performance and load test execution
- Test artifact collection and management
- Test coverage analysis and reporting

**Test Context Focus:**
- Executes test_graph integration test suites
- Validates service dependencies and connections
- Runs database migration and schema tests
- Performs API contract and compatibility testing
- Executes security and compliance test suites
- Validates test data integrity and consistency

**Usage in TestGraph:**
- Call for primary test execution phases
- Use for test environment validation
- Employ for integration test orchestration
- Utilize for test artifact and report generation

**Test Execution Categories:**
- Unit test execution with dependency injection
- Integration test suites for service interactions
- End-to-end workflow validation tests
- Performance benchmarking and load tests
- Security and penetration testing
- Database consistency and migration tests
- API contract and schema validation tests

**Test Environment Management:**
- Test database setup and teardown
- Service dependency validation
- Test data preparation and cleanup
- Environment configuration verification
- Resource allocation and monitoring

**Test Reporting and Analysis:**
- Test result aggregation and summarization
- Coverage analysis and gap identification
- Performance metrics collection
- Failure analysis and root cause identification
- Test artifact preservation and archival

The agent ensures comprehensive test execution with proper environment management
and detailed reporting for test_graph integration workflows.
"""

    def completion_definition(self) -> str:
        """
        Define completion criteria for test_graph test execution tasks.
        """
        return """
TestGraphTestRunnerAgent completes when:
1. All requested tests have been executed successfully
2. Test results are collected and properly formatted
3. Test environment is validated and stable
4. Test artifacts and reports are generated
5. Test coverage metrics are calculated and documented
6. Any test failures are analyzed and documented
7. Test cleanup and resource deallocation is completed
"""
