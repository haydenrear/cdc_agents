import typing
import injector
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agent.agent import A2AAgent, A2AReactAgent
from cdc_agents.agent.agent_orchestrator import TestGraphOrchestrated
from cdc_agents.agents.code_deploy_agent import CodeDeployAgent
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
from cdc_agents.config.cdc_server_config_props import CdcServerConfigProps
from cdc_agents.model_server.model_provider import ModelProvider
from cdc_agents.tools.tool_call_decorator import ToolCallDecorator
from python_di.configs.autowire import injectable
from python_di.configs.component import component


@component(bind_to=[A2AAgent, A2AReactAgent, TestGraphOrchestrated])
@injectable()
class TestGraphCodeDeployAgent(CodeDeployAgent, TestGraphOrchestrated):
    """
    TestGraph variant of CodeDeployAgent specialized for test_graph integration workflows.
    Focuses on deploying test environments, test services, and test infrastructure.
    """

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver, model_provider: ModelProvider,
                 cdc_server: CdcServerConfigProps, tool_call_decorator: ToolCallDecorator):
        self_card: AgentCardItem = agent_config.agents[self.__class__.__name__]
        CodeDeployAgent.__init__(self, agent_config, memory_saver, model_provider, cdc_server, tool_call_decorator)
        TestGraphOrchestrated.__init__(self, self_card)

    @property
    def agent_name(self) -> str:
        return self.__class__.__name__

    def orchestrator_prompt(self) -> str:
        """
        Override to provide test_graph specific orchestration prompt.
        """
        return """
TestGraphCodeDeployAgent specializes in deploying test environments and infrastructure for test_graph workflows including:

**Core Capabilities:**
- Test environment deployment and configuration
- Test service orchestration and management
- Test infrastructure provisioning and setup
- Test database deployment and migration
- Test container orchestration and networking
- Test deployment validation and health checks

**Test Context Focus:**
- Deploys isolated test environments for integration testing
- Sets up test-specific databases and message brokers
- Configures test service dependencies and networking
- Manages test data seeding and environment preparation
- Orchestrates containerized test service deployments
- Validates test environment readiness and connectivity

**Usage in TestGraph:**
- Call before test execution phases
- Use for test environment preparation
- Employ for test service dependency setup
- Utilize for test infrastructure provisioning

**Test Deployment Categories:**
- Integration test environment setup
- Test database deployment and schema migration
- Test service container orchestration
- Test API gateway and routing configuration
- Test monitoring and logging infrastructure
- Test security and access control setup

**Environment Management:**
- Test environment isolation and sandboxing
- Test resource allocation and scaling
- Test environment lifecycle management
- Test deployment rollback and recovery
- Test environment cleanup and teardown
- Test resource monitoring and optimization

**Service Orchestration:**
- Test microservice deployment coordination
- Test service discovery and registration
- Test load balancing and traffic routing
- Test service health monitoring and alerting
- Test service configuration management
- Test inter-service communication setup

**Infrastructure Provisioning:**
- Test cloud resource provisioning
- Test network configuration and security
- Test storage and data management setup
- Test compute resource allocation
- Test backup and disaster recovery setup
- Test compliance and audit trail configuration

**Deployment Validation:**
- Test environment health verification
- Test service connectivity validation
- Test performance baseline establishment
- Test security posture verification
- Test data integrity and consistency checks
- Test environment readiness confirmation

The agent ensures reliable and scalable test environment deployment with proper
isolation, monitoring, and validation for comprehensive test_graph integration workflows.
"""

    def completion_definition(self) -> str:
        """
        Define completion criteria for test_graph deployment tasks.
        """
        return """
TestGraphCodeDeployAgent completes when:
1. All test environments are successfully deployed and configured
2. Test services are running and healthy
3. Test infrastructure is provisioned and validated
4. Test databases are deployed with proper schema and data
5. Test environment connectivity and networking is verified
6. Test deployment health checks pass successfully
7. Test environment is ready for test execution
8. Deployment logs and metrics are captured for monitoring
"""
