import typing
import injector
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agent.agent import A2AAgent, A2AReactAgent
from cdc_agents.agent.agent_orchestrator import TestGraphOrchestrated
from cdc_agents.agents.human_delegate_agent import HumanDelegateAgent
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
from cdc_agents.config.cdc_server_config_props import CdcServerConfigProps
from cdc_agents.config.human_delegate_config_props import HumanDelegateConfigProps
from cdc_agents.model_server.model_provider import ModelProvider
from cdc_agents.tools.tool_call_decorator import ToolCallDecorator
from python_di.configs.autowire import injectable
from python_di.configs.component import component


@component(bind_to=[A2AAgent, A2AReactAgent, TestGraphOrchestrated])
@injectable()
class TestGraphHumanDelegateAgent(HumanDelegateAgent, TestGraphOrchestrated):
    """
    TestGraph variant of HumanDelegateAgent specialized for test_graph integration workflows.
    Focuses on delegating test validation, test result review, and manual test execution to humans.
    """

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver, model_provider: ModelProvider,
                 cdc_server: HumanDelegateConfigProps):
        self_card: AgentCardItem = agent_config.agents[self.__class__.__name__]
        HumanDelegateAgent.__init__(self, agent_config, memory_saver, model_provider, cdc_server)
        TestGraphOrchestrated.__init__(self, self_card)


    @property
    def agent_name(self) -> str:
        return self.__class__.__name__

    def orchestrator_prompt(self) -> str:
        """
        Override to provide test_graph specific orchestration prompt.
        """
        return """
TestGraphHumanDelegateAgent specializes in human delegation for test_graph workflows including:

**Core Capabilities:**
- Manual test result validation and review
- Human approval for test deployment decisions
- Expert review of integration test failures
- Manual test execution coordination
- Test environment validation and sign-off

**Test Context Focus:**
- Delegates critical test validation decisions to humans
- Requests manual verification of complex test scenarios
- Obtains human approval for production-like test environments
- Facilitates expert review of test failure analysis
- Coordinates manual exploratory testing

**Usage in TestGraph:**
- Call for test result validation that requires human judgment
- Use when automated test failures need expert analysis
- Employ for manual acceptance testing coordination
- Utilize for test environment approval workflows

**Test-Specific Delegation Scenarios:**
- Integration test failure analysis
- Performance test result interpretation
- Security test validation
- User acceptance test coordination
- Test data validation and privacy review
- Test environment configuration approval

**Human Interaction Patterns:**
- Structured test result presentation
- Clear pass/fail criteria communication
- Detailed failure context and reproduction steps
- Risk assessment for test environment changes
- Approval workflows for critical test phases

The agent ensures human oversight for critical test decisions while maintaining
efficient automation for routine test_graph workflow operations.
"""

    def completion_definition(self) -> str:
        """
        Define completion criteria for test_graph human delegation tasks.
        """
        return """
TestGraphHumanDelegateAgent completes when:
1. Human input or approval has been successfully collected
2. Test validation decisions have been documented
3. Manual test execution results are captured
4. Human feedback is properly formatted for downstream agents
5. Test workflow can proceed based on human decisions
6. All test-related human interactions are properly closed
"""
