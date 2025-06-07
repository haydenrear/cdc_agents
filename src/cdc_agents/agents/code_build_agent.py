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
from cdc_agents.agent.agent_orchestrator import DeepResearchOrchestrated
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
from cdc_agents.config.cdc_server_config_props import CdcServerConfigProps
from cdc_agents.model_server.model_provider import ModelProvider
from cdc_agents.tools.tool_call_decorator import ToolCallDecorator
from python_di.configs.autowire import injectable
from python_di.configs.component import component
from python_util.logger.logger import LoggerFacade



# Pydantic models for code build
class CodeBuildResult(pydantic.BaseModel):
    success: bool
    registrationId: Optional[str] = None
    output: Optional[str] = None
    error: typing.List[Error] = []
    buildId: Optional[str] = None
    exitCode: Optional[int] = None
    executionTime: Optional[int] = None
    artifactPaths: typing.List[str] = []
    artifactOutputDirectory: Optional[str] = None

class CodeBuild(pydantic.BaseModel):
    sessionId: Optional[str] = None
    registrationId: str
    buildCommand: str
    status: str
    startTime: Optional[Any] = None
    endTime: Optional[Any] = None
    exitCode: Optional[int] = None
    output: Optional[str] = None
    error: typing.List[Error] = []
    buildId: Optional[str] = None

class CodeBuildRegistration(pydantic.BaseModel):
    registrationId: str
    buildCommand: str
    workingDirectory: Optional[str] = None
    description: Optional[str] = None
    arguments: Optional[str] = None
    timeoutSeconds: Optional[int] = None
    enabled: bool
    artifactPaths: typing.List[str] = []
    artifactOutputDirectory: Optional[str] = None
    executionType: Optional[str] = None

@component(bind_to=[DeepResearchOrchestrated, A2AAgent, A2AReactAgent])
@injectable()
class CodeBuildAgent(DeepResearchOrchestrated, A2AReactAgent):
    """Agent that provides tools for building code based on the commit-diff-context GraphQL schema."""

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver, model_provider: ModelProvider,
                 cdc_server: CdcServerConfigProps, tool_call_decorator: ToolCallDecorator):
        self_card: AgentCardItem = agent_config.agents[self.__class__.__name__]
        DeepResearchOrchestrated.__init__(self, self_card)
        A2AReactAgent.__init__(self, agent_config,
                               [
                                   self.produce_build_code(),
                                   self.produce_retrieve_builds(),
                                   self.produce_retrieve_build_registrations(),
                                   self.produce_get_build_output(),
                                   self.produce_register_code_build(),
                                   self.produce_update_code_build_registration(),
                                   self.produce_delete_code_build_registration(),
                                   self.produce_get_code_build_registration(),
                               ],
                               self_card.agent_descriptor.system_prompts,
                               memory_saver, model_provider)
        self.tool_call_decorator = tool_call_decorator
        self.cdc_server = cdc_server

    def produce_build_code(self):
        @tool
        def build_code(registration_id: str, session_id: Annotated[str, InjectedState("session_id")],
                      arguments: Optional[str] = None, timeout_seconds: Optional[int] = None) -> CodeBuildResult:
            """Build code using a registered code build configuration.

            Args:
                registration_id: ID of the registered code build to run
                arguments: Optional additional arguments for the build
                timeout_seconds: Optional timeout in seconds for the build

            Returns:
                Result of the code build including success status, output, and error
            """
            query = """
            mutation BuildCode($options: CodeBuildOptions!) {
                build(options: $options) {
                    success
                    output
                    error {
                        message
                        code
                    }
                    buildId
                    registrationId
                    exitCode
                    executionTime
                    artifactPaths
                    artifactOutputDirectory
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
                    result_key="build",
                    model_class=CodeBuildResult
                )
            except Exception as e:
                return CodeBuildResult(
                    success=False,
                    error=[Error(message=str(e))]
                )

        return build_code

    def produce_register_code_build(self):
        @tool
        def register_code_build(registration_id: str, build_command: str,
                               session_id: Annotated[str, InjectedState("session_id")],
                               working_directory: Optional[str] = None,
                               description: Optional[str] = None,
                               arguments: Optional[str] = None,
                               timeout_seconds: Optional[int] = None,
                               enabled: bool = True,
                               artifact_paths: Optional[List[str]] = None,
                               artifact_output_directory: Optional[str] = None) -> CodeBuildRegistration:
            """Register a new code build configuration.

            Args:
                registration_id: Unique ID for this build registration
                build_command: The build command to execute
                working_directory: Working directory for the build
                description: Description of this build configuration
                arguments: Default arguments for the build
                timeout_seconds: Timeout in seconds for the build
                enabled: Whether this build configuration is enabled
                artifact_paths: Paths to build artifacts
                artifact_output_directory: Directory for build artifacts

            Returns:
                The registered code build configuration
            """
            query = """
            mutation RegisterCodeBuild($codeBuildRegistration: CodeBuildRegistrationIn!) {
                registerCodeBuild(codeBuildRegistration: $codeBuildRegistration) {
                    registrationId
                    buildCommand
                    workingDirectory
                    description
                    arguments
                    timeoutSeconds
                    enabled
                    artifactPaths
                    artifactOutputDirectory
                    executionType
                }
            }
            """

            variables: Dict[str, Any] = {
                "codeBuildRegistration": {
                    "sessionId": session_id,
                    "registrationId": registration_id,
                    "buildCommand": build_command,
                    "enabled": enabled
                }
            }

            if working_directory:
                variables["codeBuildRegistration"]["workingDirectory"] = working_directory
            if description:
                variables["codeBuildRegistration"]["description"] = description
            if arguments:
                variables["codeBuildRegistration"]["arguments"] = arguments
            if timeout_seconds:
                variables["codeBuildRegistration"]["timeoutSeconds"] = timeout_seconds
            if artifact_paths:
                variables["codeBuildRegistration"]["artifactPaths"] = artifact_paths
            if artifact_output_directory:
                variables["codeBuildRegistration"]["artifactOutputDirectory"] = artifact_output_directory

            try:
                return execute_graphql_request(
                    endpoint=self.cdc_server.graphql_endpoint,
                    query=query,
                    variables=variables,
                    result_key="registerCodeBuild",
                    model_class=CodeBuildRegistration
                )
            except Exception as e:
                return CodeBuildRegistration(
                    registrationId=registration_id,
                    buildCommand=build_command,
                    enabled=False
                )

        return register_code_build

    def produce_update_code_build_registration(self):
        @tool
        def update_code_build_registration(registration_id: str,
                                          session_id: Annotated[str, InjectedState("session_id")],
                                          enabled: Optional[bool] = None,
                                          build_command: Optional[str] = None,
                                          working_directory: Optional[str] = None,
                                          arguments: Optional[str] = None,
                                          timeout_seconds: Optional[int] = None) -> CodeBuildRegistration:
            """Update an existing code build registration.

            Args:
                registration_id: ID of the registration to update
                enabled: Whether this build configuration is enabled
                build_command: The build command to execute
                working_directory: Working directory for the build
                arguments: Default arguments for the build
                timeout_seconds: Timeout in seconds for the build

            Returns:
                The updated code build registration
            """
            query = """
            mutation UpdateCodeBuildRegistration(
                $registrationId: String!
                $enabled: Boolean
                $buildCommand: String
                $workingDirectory: String
                $arguments: String
                $timeoutSeconds: Int
                $sessionId: String
            ) {
                updateCodeBuildRegistration(
                    registrationId: $registrationId
                    enabled: $enabled
                    buildCommand: $buildCommand
                    workingDirectory: $workingDirectory
                    arguments: $arguments
                    timeoutSeconds: $timeoutSeconds
                    sessionId: $sessionId
                ) {
                    registrationId
                    buildCommand
                    workingDirectory
                    description
                    arguments
                    timeoutSeconds
                    enabled
                    artifactPaths
                    artifactOutputDirectory
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
            if build_command:
                variables["buildCommand"] = build_command
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
                    result_key="updateCodeBuildRegistration",
                    model_class=CodeBuildRegistration
                )
            except Exception as e:
                return CodeBuildRegistration(
                    registrationId=registration_id,
                    buildCommand="",
                    enabled=False
                )

        return update_code_build_registration

    def produce_delete_code_build_registration(self):
        @tool
        def delete_code_build_registration(registration_id: str,
                                          session_id: Annotated[str, InjectedState("session_id")]) -> bool:
            """Delete a code build registration.

            Args:
                registration_id: ID of the registration to delete

            Returns:
                True if deletion was successful, False otherwise
            """
            query = """
            mutation DeleteCodeBuildRegistration($registrationId: String!, $sessionId: String!) {
                deleteCodeBuildRegistration(registrationId: $registrationId, sessionId: $sessionId)
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
                    result_key="deleteCodeBuildRegistration",
                    model_class=bool
                )
                return result
            except Exception as e:
                LoggerFacade.error(f"Error deleting code build registration: {e}")
                return False

        return delete_code_build_registration

    def produce_retrieve_builds(self):
        @tool
        def retrieve_builds() -> List[CodeBuild]:
            """Retrieve all code builds.

            Returns:
                List of code builds
            """
            query = """
            query RetrieveBuilds {
                retrieveBuilds {
                    sessionId
                    registrationId
                    buildCommand
                    status
                    startTime
                    endTime
                    exitCode
                    output
                    error {
                        message
                        code
                    }
                    buildId
                }
            }
            """

            try:
                return execute_graphql_request(
                    endpoint=self.cdc_server.graphql_endpoint,
                    query=query,
                    variables={},
                    result_key="retrieveBuilds",
                    model_class=List[CodeBuild]
                )
            except Exception as e:
                LoggerFacade.error(f"Error retrieving builds: {e}")
                return []

        return retrieve_builds

    def produce_retrieve_build_registrations(self):
        @tool
        def retrieve_build_registrations() -> List[CodeBuildRegistration]:
            """Retrieve all code build registrations.

            Returns:
                List of code build registrations
            """
            query = """
            query RetrieveBuildRegistrations {
                retrieveBuildRegistrations {
                    registrationId
                    buildCommand
                    workingDirectory
                    description
                    arguments
                    timeoutSeconds
                    enabled
                    artifactPaths
                    artifactOutputDirectory
                    executionType
                }
            }
            """

            try:
                return execute_graphql_request(
                    endpoint=self.cdc_server.graphql_endpoint,
                    query=query,
                    variables={},
                    result_key="retrieveBuildRegistrations",
                    model_class=List[CodeBuildRegistration]
                )
            except Exception as e:
                LoggerFacade.error(f"Error retrieving build registrations: {e}")
                return []

        return retrieve_build_registrations

    def produce_get_code_build_registration(self):
        @tool
        def get_code_build_registration(registration_id: str) -> Optional[CodeBuildRegistration]:
            """Get a specific code build registration by ID.

            Args:
                registration_id: ID of the registration to retrieve

            Returns:
                The code build registration if found, None otherwise
            """
            query = """
            query GetCodeBuildRegistration($registrationId: String!) {
                getCodeBuildRegistration(registrationId: $registrationId) {
                    registrationId
                    buildCommand
                    workingDirectory
                    description
                    arguments
                    timeoutSeconds
                    enabled
                    artifactPaths
                    artifactOutputDirectory
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
                    result_key="getCodeBuildRegistration",
                    model_class=CodeBuildRegistration
                )
            except Exception as e:
                LoggerFacade.error(f"Error getting code build registration: {e}")
                return None

        return get_code_build_registration

    def produce_get_build_output(self):
        @tool
        def get_build_output(build_id: str, session_id: Annotated[str, InjectedState("session_id")]) -> Optional[CodeBuildResult]:
            """Get the output of a specific build by ID.

            Args:
                build_id: ID of the build to get output for

            Returns:
                The build result if found, None otherwise
            """
            query = """
            query GetBuildOutput($buildId: String!, $sessionId: String) {
                getBuildOutput(buildId: $buildId, sessionId: $sessionId) {
                    success
                    output
                    error {
                        message
                        code
                    }
                    buildId
                    registrationId
                    exitCode
                    executionTime
                    artifactPaths
                    artifactOutputDirectory
                }
            }
            """

            variables: Dict[str, Any] = {
                "buildId": build_id,
                "sessionId": session_id
            }

            try:
                return execute_graphql_request(
                    endpoint=self.cdc_server.graphql_endpoint,
                    query=query,
                    variables=variables,
                    result_key="getBuildOutput",
                    model_class=CodeBuildResult
                )
            except Exception as e:
                LoggerFacade.error(f"Error getting build output: {e}")
                return None

        return get_build_output
