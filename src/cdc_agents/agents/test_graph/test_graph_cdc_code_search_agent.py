import typing
import injector
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agent.agent import A2AAgent, A2AReactAgent
from cdc_agents.agent.agent_orchestrator import TestGraphOrchestrated
from cdc_agents.agents.cdc_server_agent import CdcCodeSearchAgent, CdcServerAgentToolCallProvider
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
from cdc_agents.config.cdc_server_config_props import CdcServerConfigProps
from cdc_agents.model_server.model_provider import ModelProvider
from python_di.configs.autowire import injectable
from python_di.configs.component import component


@component(bind_to=[A2AAgent, A2AReactAgent, TestGraphOrchestrated])
@injectable()
class TestGraphCdcCodeSearchAgent(CdcCodeSearchAgent, TestGraphOrchestrated):
    """
    TestGraph variant of CdcCodeSearchAgent specialized for test_graph integration workflows.
    Focuses on searching test code, test configurations, and test-related artifacts.
    """

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver, model_provider: ModelProvider,
                 cdc_server: CdcServerConfigProps, tool_call_provider: CdcServerAgentToolCallProvider):
        self_card: AgentCardItem = agent_config.agents[self.__class__.__name__]
        CdcCodeSearchAgent.__init__(self, agent_config, memory_saver, model_provider, cdc_server, tool_call_provider)
        TestGraphOrchestrated.__init__(self, self_card)

    @property
    def agent_name(self) -> str:
        return self.__class__.__name__

    def orchestrator_prompt(self) -> str:
        """
        Override to provide test_graph specific orchestration prompt.
        """
        return """
TestGraphCdcCodeSearchAgent specializes in searching and analyzing test-related code and artifacts for test_graph workflows including:

**Core Capabilities:**
- Test code discovery and analysis
- Test configuration file location and parsing
- Test dependency identification and mapping
- Test artifact search and classification
- Test coverage analysis and reporting
- Test pattern and anti-pattern detection

**Test Context Focus:**
- Searches for existing integration test implementations
- Locates test configuration files and settings
- Identifies test dependencies and their versions
- Finds test data files, fixtures, and resources
- Discovers test utilities and helper libraries
- Analyzes test code quality and coverage patterns

**Usage in TestGraph:**
- Call for test discovery and analysis phases
- Use for test dependency mapping
- Employ for test coverage assessment
- Utilize for test pattern analysis

**Test Search Categories:**
- Unit test discovery and classification
- Integration test suite identification
- End-to-end test scenario location
- Performance and load test detection
- Security and compliance test discovery
- API contract test identification

**Test Configuration Search:**
- Test environment configuration files
- Test database connection and setup configs
- Test service configuration properties
- Test data source and fixture definitions
- Test container and deployment configurations
- Test CI/CD pipeline and build configs

**Test Artifact Analysis:**
- Test execution logs and reports
- Test coverage reports and metrics
- Test performance benchmarks and results
- Test failure analysis and diagnostics
- Test artifact dependencies and relationships
- Test documentation and specifications

**Code Quality Assessment:**
- Test code complexity and maintainability analysis
- Test coverage gap identification
- Test duplication and redundancy detection
- Test performance bottleneck identification
- Test security vulnerability scanning
- Test best practice compliance verification

**Integration with CDC:**
- Leverages CDC schema for test code indexing
- Uses commit diff context for targeted test search
- Integrates with CDC workflows for test discovery
- Supports CDC-based test impact analysis

**Search Result Processing:**
- Categorizes search results by test type and purpose
- Provides relevance scoring for test artifacts
- Generates test dependency graphs and relationships
- Creates test coverage maps and visualizations
- Produces test quality metrics and recommendations

The agent ensures comprehensive discovery and analysis of test-related code and artifacts
to support informed decision-making in test_graph integration workflows.
"""

    def completion_definition(self) -> str:
        """
        Define completion criteria for test_graph code search tasks.
        """
        return """
TestGraphCdcCodeSearchAgent completes when:
1. All requested test code and artifacts have been discovered
2. Test configurations and dependencies are properly mapped
3. Test coverage analysis is completed and documented
4. Search results are categorized and prioritized
5. Test quality metrics are calculated and reported
6. Test relationships and dependencies are identified
7. Search findings are formatted for downstream agent consumption
8. Test discovery results are integrated with CDC context
"""
