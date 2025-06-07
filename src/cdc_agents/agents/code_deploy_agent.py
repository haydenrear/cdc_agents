import injector
import typing
from typing import List, Optional, Any, Dict

import pydantic
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedState
from typing_extensions import Annotated

from cdc_agents.agent.a2a import A2AAgent
from cdc_agents.agent.agent import A2AReactAgent
from cdc_agents.common.graphql_models import execute_graphql_request, Error
from cdc_agents.agents.deep_code_research_agent import DeepResearchOrchestrated
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
from cdc_agents.config.cdc_server_config_props import CdcServerConfigProps
from cdc_agents.model_server.model_provider import ModelProvider
from cdc_agents.tools.tool_call_decorator import ToolCallDecorator
from python_di.configs.autowire import injectable
from python_di.configs.component import component
from python_util.logger.logger import LoggerFacade

# Pydantic models for code deployment
class CodeDeployResult(pydantic.BaseModel):
    success: bool
    registrationId: Optional[str] = None
    output: Optional[str] = None
    error: typing.List[Error] = []
    deployId: Optional[str] = None
    exitCode: Optional[int] = None
    executionTime: Optional[int] = None
    deployLog: Optional[str] = None
    healthCheckStatus: Optional[str] = None

class CodeDeploy(pydantic.BaseModel):
    sessionId: Optional[str] = None
    registrationId: str
    deployCommand: str
    status: str
    startTime: Optional[Any] = None
    endTime: Optional[Any] = None
    exitCode: Optional[int] = None
    output: Optional[str] = None
    error: typing.List[Error] = []
    deployId: Optional[str] = None
    healthCheckStatus: Optional[str] = None
    rollbackReason: Optional[str] = None

class CodeDeployRegistration(pydantic.BaseModel):
    registrationId: str
    deployCommand: str
    workingDirectory: Optional[str] = None
    description: Optional[str] = None
    arguments: Optional[str] = None
    timeoutSeconds: Optional[int] = None
    enabled: bool
    healthCheckUrl: Optional[str] = None
    stopCommand: Optional[str] = None
    executionType: Optional[str] = None
    deploySuccessPatterns: typing.List[str] = []
    deployFailurePatterns: typing.List[str] = []

@component(bind_to=[DeepResearchOrchestrated, A2AAgent, A2AReactAgent])
@injectable()
class CodeDeployAgent(DeepResearchOrchestrated, A2AReactAgent):
    """Agent that provides tools for deploying code based on the commit-diff-context GraphQL schema."""

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver, model_provider: ModelProvider,
                 cdc_server: CdcServerConfigProps, tool_call_decorator: ToolCallDecorator):
        self_card: AgentCardItem = agent_config.agents[self.__class__.__name__]
        DeepResearchOrchestrated.__init__(self, self_card)
        A2AReactAgent.__init__(self, agent_config,
                               [
                                   self.produce_deploy_code(),
                                   self.produce_stop_deployment(),
                                   self.produce_retrieve_deploys(),
                                   self.produce_retrieve_deploy_registrations(),
                                   self.produce_get_deploy_output(),
                                   self.produce_get_running_deployments(),
                                   self.produce_register_code_deploy(),
                                   self.produce_update_code_deploy_registration(),
                                   self.produce_delete_code_deploy_registration(),
                                   self.produce_get_code_deploy_registration(),
                               ],
                               self_card.agent_descriptor.system_prompts,
                               memory_saver, model_provider)
        self.tool_call_decorator = tool_call_decorator
        self.cdc_server = cdc_server

    def produce_deploy_code(self):
        @tool
        def deploy_code(registration_id: str, session_id: Annotated[str, InjectedState("session_id")],
                       arguments: Optional[str] = None, timeout_seconds: Optional[int] = None) -> CodeDeployResult:
            """Deploy code using a registered code deployment configuration.

            Args:
                registration_id: ID of the registered code deployment to run
                arguments: Optional additional arguments for the deployment
                timeout_seconds: Optional timeout in seconds for the deployment

            Returns:
                Result of the code deployment including success status, output, and error
            """
            query = """
            mutation DeployCode($options: CodeDeployOptions!) {
                deploy(options: $options) {
                    success
                    output
                    error {
                        message
                        code
                    }
                    deployId
                    registrationId
                    exitCode
                    executionTime
                    deployLog
                    healthCheckStatus
                }
            }
            """

            variables: Dict[str, Any] = {
                "options": {
                    "registrationId": registration_id,
                    "sessionId": session_id
                }
            }

            if arguments:
                variables["options"]["arguments"] = arguments
            if timeout_seconds:
                variables["options"]["timeoutSeconds"] = timeout_seconds

            try:
                return execute_graphql_request(
                    endpoint=self.cdc_server.graphql_endpoint,
                    query=query,
                    variables=variables,
                    result_key="deploy",
                    model_class=CodeDeployResult
                )
            except Exception as e:
                return CodeDeployResult(
                    success=False,
                    error=[Error(message=str(e))]
                )

        return deploy_code

    def produce_stop_deployment(self):
        @tool
        def stop_deployment(registration_id: str, session_id: Annotated[str, InjectedState("session_id")]) -> CodeDeployResult:
            """Stop a running deployment.

            Args:
                registration_id: ID of the deployment registration to stop

            Returns:
                Result of stopping the deployment
            """
            query = """
            mutation StopDeployment($registrationId: String!, $sessionId: String!) {
                stopDeployment(registrationId: $registrationId, sessionId: $sessionId) {
                    success
                    output
                    error {
                        message
                        code
                    }
                    deployId
                    registrationId
                    exitCode
                    executionTime
                    deployLog
                    healthCheckStatus
                }
            }
            """

            variables: Dict[str, Any] = {
                "registrationId": registration_id,
                "sessionId": session_id
            }

            try:
                return execute_graphql_request(
                    endpoint=self.cdc_server.graphql_endpoint,
                    query=query,
                    variables=variables,
                    result_key="stopDeployment",
                    model_class=CodeDeployResult
                )
            except Exception as e:
                return CodeDeployResult(
                    success=False,
                    error=[Error(message=str(e))]
                )

        return stop_deployment

    def produce_register_code_deploy(self):
        @tool
        def register_code_deploy(registration_id: str, deploy_command: str,
                                session_id: Annotated[str, InjectedState("session_id")],
                                working_directory: Optional[str] = None,
                                description: Optional[str] = None,
                                arguments: Optional[str] = None,
                                timeout_seconds: Optional[int] = None,
                                enabled: bool = True,
                                health_check_url: Optional[str] = None,
                                stop_command: Optional[str] = None,
                                deploy_success_patterns: Optional[List[str]] = None,
                                deploy_failure_patterns: Optional[List[str]] = None) -> CodeDeployRegistration:
            """Register a new code deployment configuration.

            Args:
                registration_id: Unique ID for this deployment registration
                deploy_command: The deployment command to execute
                working_directory: Working directory for the deployment
                description: Description of this deployment configuration
                arguments: Default arguments for the deployment
                timeout_seconds: Timeout in seconds for the deployment
                enabled: Whether this deployment configuration is enabled
                health_check_url: URL for health checks after deployment
                stop_command: Command to stop the deployment
                deploy_success_patterns: Patterns indicating successful deployment
                deploy_failure_patterns: Patterns indicating failed deployment

            Returns:
                The registered code deployment configuration
            """
            query = """
            mutation RegisterCodeDeploy($codeDeployRegistration: CodeDeployRegistrationIn!) {
                registerCodeDeploy(codeDeployRegistration: $codeDeployRegistration) {
                    registrationId
                    deployCommand
                    workingDirectory
                    description
                    arguments
                    timeoutSeconds
                    enabled
                    healthCheckUrl
                    stopCommand
                    executionType
                }
            }
            """

            variables: Dict[str, Any] = {
                "codeDeployRegistration": {
                    "sessionId": session_id,
                    "registrationId": registration_id,
                    "deployCommand": deploy_command,
                    "enabled": enabled
                }
            }

            if working_directory:
                variables["codeDeployRegistration"]["workingDirectory"] = working_directory
            if description:
                variables["codeDeployRegistration"]["description"] = description
            if arguments:
                variables["codeDeployRegistration"]["arguments"] = arguments
            if timeout_seconds:
                variables["codeDeployRegistration"]["timeoutSeconds"] = timeout_seconds
            if health_check_url:
                variables["codeDeployRegistration"]["healthCheckUrl"] = health_check_url
            if stop_command:
                variables["codeDeployRegistration"]["stopCommand"] = stop_command
            if deploy_success_patterns:
                variables["codeDeployRegistration"]["deploySuccessPatterns"] = deploy_success_patterns
            if deploy_failure_patterns:
                variables["codeDeployRegistration"]["deployFailurePatterns"] = deploy_failure_patterns

            try:
                return execute_graphql_request(
                    endpoint=self.cdc_server.graphql_endpoint,
                    query=query,
                    variables=variables,
                    result_key="registerCodeDeploy",
                    model_class=CodeDeployRegistration
                )
            except Exception as e:
                return CodeDeployRegistration(
                    registrationId=registration_id,
                    deployCommand=deploy_command,
                    enabled=False
                )

        return register_code_deploy

    def produce_update_code_deploy_registration(self):
        @tool
        def update_code_deploy_registration(registration_id: str,
                                           session_id: Annotated[str, InjectedState("session_id")],
                                           enabled: Optional[bool] = None,
                                           deploy_command: Optional[str] = None,
                                           working_directory: Optional[str] = None,
                                           arguments: Optional[str] = None,
                                           timeout_seconds: Optional[int] = None) -> CodeDeployRegistration:
            """Update an existing code deployment registration.

            Args:
                registration_id: ID of the registration to update
                enabled: Whether this deployment configuration is enabled
                deploy_command: The deployment command to execute
                working_directory: Working directory for the deployment
                arguments: Default arguments for the deployment
                timeout_seconds: Timeout in seconds for the deployment

            Returns:
                The updated code deployment registration
            """
            query = """
            mutation UpdateCodeDeployRegistration(
                $registrationId: String!
                $enabled: Boolean
                $deployCommand: String
                $workingDirectory: String
                $arguments: String
                $timeoutSeconds: Int
                $sessionId: String
            ) {
                updateCodeDeployRegistration(
                    registrationId: $registrationId
                    enabled: $enabled
                    deployCommand: $deployCommand
                    workingDirectory: $workingDirectory
                    arguments: $arguments
                    timeoutSeconds: $timeoutSeconds
                    sessionId: $sessionId
                ) {
                    registrationId
                    deployCommand
                    workingDirectory
                    description
                    arguments
                    timeoutSeconds
                    enabled
                    healthCheckUrl
                    stopCommand
                    executionType
                }
            }
            """

            variables: Dict[str, Any] = {
                "registrationId": registration_id,
                "sessionId": session_id
            }

            if enabled is not None:
                variables["enabled"] = enabled
            if deploy_command:
                variables["deployCommand"] = deploy_command
            if working_directory:
                variables["workingDirectory"] = working_directory
            if arguments:
                variables["arguments"] = arguments
            if timeout_seconds:
                variables["timeoutSeconds"] = timeout_seconds

            try:
                return execute_graphql_request(
                    endpoint=self.cdc_server.graphql_endpoint,
                    query=query,
                    variables=variables,
                    result_key="updateCodeDeployRegistration",
                    model_class=CodeDeployRegistration
                )
            except Exception as e:
                return CodeDeployRegistration(
                    registrationId=registration_id,
                    deployCommand="",
                    enabled=False
                )

        return update_code_deploy_registration

    def produce_delete_code_deploy_registration(self):
        @tool
        def delete_code_deploy_registration(registration_id: str,
                                           session_id: Annotated[str, InjectedState("session_id")]) -> bool:
            """Delete a code deployment registration.

            Args:
                registration_id: ID of the registration to delete

            Returns:
                True if deletion was successful, False otherwise
            """
            query = """
            mutation DeleteCodeDeployRegistration($registrationId: String!, $sessionId: String!) {
                deleteCodeDeployRegistration(registrationId: $registrationId, sessionId: $sessionId)
            }
            """

            variables: Dict[str, Any] = {
                "registrationId": registration_id,
                "sessionId": session_id
            }

            try:
                result = execute_graphql_request(
                    endpoint=self.cdc_server.graphql_endpoint,
                    query=query,
                    variables=variables,
                    result_key="deleteCodeDeployRegistration",
                    model_class=bool
                )
                return result
            except Exception as e:
                LoggerFacade.error(f"Error deleting code deploy registration: {e}")
                return False

        return delete_code_deploy_registration

    def produce_retrieve_deploys(self):
        @tool
        def retrieve_deploys() -> List[CodeDeploy]:
            """Retrieve all code deployments.

            Returns:
                List of code deployments
            """
            query = """
            query RetrieveDeploys {
                retrieveDeploys {
                    sessionId
                    registrationId
                    deployCommand
                    status
                    startTime
                    endTime
                    exitCode
                    output
                    error {
                        message
                        code
                    }
                    deployId
                }
            }
            """

            try:
                return execute_graphql_request(
                    endpoint=self.cdc_server.graphql_endpoint,
                    query=query,
                    variables={},
                    result_key="retrieveDeploys",
                    model_class=List[CodeDeploy]
                )
            except Exception as e:
                LoggerFacade.error(f"Error retrieving deployments: {e}")
                return []

        return retrieve_deploys

    def produce_retrieve_deploy_registrations(self):
        @tool
        def retrieve_deploy_registrations() -> List[CodeDeployRegistration]:
            """Retrieve all code deployment registrations.

            Returns:
                List of code deployment registrations
            """
            query = """
            query RetrieveDeployRegistrations {
                retrieveDeployRegistrations {
                    registrationId
                    deployCommand
                    workingDirectory
                    description
                    arguments
                    timeoutSeconds
                    enabled
                    healthCheckUrl
                    stopCommand
                    executionType
                }
            }
            """

            try:
                return execute_graphql_request(
                    endpoint=self.cdc_server.graphql_endpoint,
                    query=query,
                    variables={},
                    result_key="retrieveDeployRegistrations",
                    model_class=List[CodeDeployRegistration]
                )
            except Exception as e:
                LoggerFacade.error(f"Error retrieving deploy registrations: {e}")
                return []

        return retrieve_deploy_registrations

    def produce_get_code_deploy_registration(self):
        @tool
        def get_code_deploy_registration(registration_id: str) -> Optional[CodeDeployRegistration]:
            """Get a specific code deployment registration by ID.

            Args:
                registration_id: ID of the registration to retrieve

            Returns:
                The code deployment registration if found, None otherwise
            """
            query = """
            query GetCodeDeployRegistration($registrationId: String!) {
                getCodeDeployRegistration(registrationId: $registrationId) {
                    registrationId
                    deployCommand
                    workingDirectory
                    description
                    arguments
                    timeoutSeconds
                    enabled
                    healthCheckUrl
                    stopCommand
                    executionType
                }
            }
            """

            variables: Dict[str, Any] = {
                "registrationId": registration_id
            }

            try:
                return execute_graphql_request(
                    endpoint=self.cdc_server.graphql_endpoint,
                    query=query,
                    variables=variables,
                    result_key="getCodeDeployRegistration",
                    model_class=CodeDeployRegistration
                )
            except Exception as e:
                LoggerFacade.error(f"Error getting code deploy registration: {e}")
                return None

        return get_code_deploy_registration

    def produce_get_deploy_output(self):
        @tool
        def get_deploy_output(deploy_id: str, session_id: Annotated[str, InjectedState("session_id")]) -> Optional[CodeDeployResult]:
            """Get the output of a specific deployment by ID.

            Args:
                deploy_id: ID of the deployment to get output for

            Returns:
                The deployment result if found, None otherwise
            """
            query = """
            query GetDeployOutput($deployId: String!, $sessionId: String) {
                getDeployOutput(deployId: $deployId, sessionId: $sessionId) {
                    success
                    output
                    error {
                        message
                        code
                    }
                    deployId
                    registrationId
                    exitCode
                    executionTime
                    deployLog
                    healthCheckStatus
                }
            }
            """

            variables: Dict[str, Any] = {
                "deployId": deploy_id,
                "sessionId": session_id
            }

            try:
                return execute_graphql_request(
                    endpoint=self.cdc_server.graphql_endpoint,
                    query=query,
                    variables=variables,
                    result_key="getDeployOutput",
                    model_class=CodeDeployResult
                )
            except Exception as e:
                LoggerFacade.error(f"Error getting deploy output: {e}")
                return None

        return get_deploy_output

    def produce_get_running_deployments(self):
        @tool
        def get_running_deployments() -> List[CodeDeploy]:
            """Get all currently running deployments.

            Returns:
                List of running deployments
            """
            query = """
            query GetRunningDeployments {
                getRunningDeployments {
                    sessionId
                    registrationId
                    deployCommand
                    status
                    startTime
                    endTime
                    exitCode
                    output
                    error {
                        message
                        code
                    }
                    deployId
                }
            }
            """

            try:
                return execute_graphql_request(
                    endpoint=self.cdc_server.graphql_endpoint,
                    query=query,
                    variables={},
                    result_key="getRunningDeployments",
                    model_class=List[CodeDeploy]
                )
            except Exception as e:
                LoggerFacade.error(f"Error getting running deployments: {e}")
                return []

        return get_running_deployments
