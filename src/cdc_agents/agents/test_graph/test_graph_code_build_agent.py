import typing
import injector
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agent.agent import A2AAgent, A2AReactAgent
from cdc_agents.agent.agent_orchestrator import TestGraphOrchestrated
from cdc_agents.agents.code_build_agent import CodeBuildAgent
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
from cdc_agents.config.cdc_server_config_props import CdcServerConfigProps
from cdc_agents.model_server.model_provider import ModelProvider
from cdc_agents.tools.tool_call_decorator import ToolCallDecorator
from python_di.configs.autowire import injectable
from python_di.configs.component import component


@component(bind_to=[A2AAgent, A2AReactAgent, TestGraphOrchestrated])
@injectable()
class TestGraphCodeBuildAgent(CodeBuildAgent, TestGraphOrchestrated):
    """
    TestGraph variant of CodeBuildAgent specialized for test_graph integration workflows.
    Focuses on building test code, test dependencies, and test-specific artifacts.
    """

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver, model_provider: ModelProvider,
                 cdc_server: CdcServerConfigProps, tool_call_decorator: ToolCallDecorator):
        self_card: AgentCardItem = agent_config.agents[self.__class__.__name__]
        CodeBuildAgent.__init__(self, agent_config, memory_saver, model_provider, cdc_server, tool_call_decorator)
        TestGraphOrchestrated.__init__(self, self_card)

    @property
    def agent_name(self) -> str:
        return self.__class__.__name__

    def orchestrator_prompt(self) -> str:
        """
        Override to provide test_graph specific orchestration prompt.
        """
        return """
TestGraphCodeBuildAgent specializes in building test-related code and artifacts for test_graph workflows including:

**Core Capabilities:**
- Test code compilation and validation
- Test dependency resolution and building
- Test artifact packaging and preparation
- Test environment container building
- Test resource compilation and bundling
- Test configuration validation and setup

**Test Context Focus:**
- Builds integration test suites and dependencies
- Compiles test-specific modules and libraries
- Packages test artifacts for distribution
- Prepares containerized test environments
- Validates test build configurations
- Manages test-specific resource compilation

**Usage in TestGraph:**
- Call before test execution phases
- Use for test dependency preparation
- Employ for test environment setup
- Utilize for test artifact generation

**Test Build Categories:**
- Unit test compilation and packaging
- Integration test suite building
- Test data and resource preparation
- Test configuration compilation
- Test container image building
- Test dependency artifact creation

**Build Environment Management:**
- Test-specific build configuration
- Test dependency isolation and management
- Test environment containerization
- Test resource compilation and optimization
- Build artifact verification and validation

**Test Artifact Types:**
- Test executable JAR files
- Test dependency libraries
- Test configuration bundles
- Test data archives
- Test container images
- Test documentation artifacts

**Quality Assurance:**
- Build verification testing
- Dependency conflict resolution
- Test build performance optimization
- Build artifact integrity validation
- Test environment compatibility verification

The agent ensures reliable and efficient building of all test-related code and artifacts
required for comprehensive test_graph integration workflows.
"""

    def completion_definition(self) -> str:
        """
        Define completion criteria for test_graph build tasks.
        """
        return """
TestGraphCodeBuildAgent completes when:
1. All test-related code has been successfully compiled
2. Test dependencies are resolved and built
3. Test artifacts are properly packaged and validated
4. Test environment containers are built and ready
5. Build verification tests pass successfully
6. Test build artifacts are available for downstream processes
7. Build logs and metrics are captured for analysis
"""
