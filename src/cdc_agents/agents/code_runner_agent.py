import injector
import typing

import pydantic
import requests
from typing import Dict, Any, TypeVar, Type, cast, List, Optional
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import tool
from langgraph.prebuilt import InjectedStore, InjectedState
from typing_extensions import Annotated

from cdc_agents.agent.a2a import A2AAgent
from cdc_agents.agent.agent import A2AReactAgent
from cdc_agents.agents.deep_code_research_agent import DeepResearchOrchestrated
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
from cdc_agents.config.cdc_server_config_props import CdcServerConfigProps
from cdc_agents.model_server.model_provider import ModelProvider
from cdc_agents.tools.tool_call_decorator import ToolCallDecorator
from python_di.configs.autowire import injectable
from python_di.configs.component import component
from python_util.logger.logger import LoggerFacade

T = TypeVar('T')

def execute_graphql_request(
        endpoint: str,
        query: str,
        variables: Dict[str, Any],
        result_key: str,
        model_class: Type[T],
        err_producer: typing.Callable[[str], T] = None
) -> T:
    """Execute a GraphQL request and parse the response into the specified model.
    
    Args:
        err_producer: Error producer function
        endpoint: GraphQL endpoint URL
        query: GraphQL query or mutation
        variables: Variables for the GraphQL query
        result_key: Key in the response data to extract
        model_class: Pydantic model class to parse the response into
        
    Returns:
        Parsed response data as a Pydantic model
    """
    headers = {
        "Content-Type": "application/json",
    }

    data = {
        "query": query,
        "variables": variables
    }

    try:
        response = requests.post(endpoint, headers=headers, json=data)
        response.raise_for_status()

        response_json = response.json()
        result_data = response_json.get("data", {}).get(result_key, {})

        # Safely handle model instantiation regardless of Pydantic version
        try:
            # Try Pydantic v2 style
            if hasattr(model_class, 'model_validate'):
                return model_class.model_validate(result_data)
            # Try Pydantic v1 style
            elif hasattr(model_class, 'parse_obj'):
                return model_class.parse_obj(result_data)
            # Fallback to direct instantiation
            else:
                return cast(T, model_class(**result_data))
        except TypeError:
            # If all else fails, try direct instantiation
            return cast(T, model_class(**result_data))
    except Exception as e:
        LoggerFacade.error(f"GraphQL request:\n{query}\n{data}\n{headers} failed: {str(e)}")
        raise e

# Pydantic models for code execution
class CodeExecutionResult(pydantic.BaseModel):
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    executionId: Optional[str] = None
    exitCode: Optional[int] = None
    executionTime: Optional[int] = None
    outputFile: Optional[str] = None

class CodeExecution(pydantic.BaseModel):
    id: str
    command: str
    status: str
    startTime: Optional[Any] = None
    endTime: Optional[Any] = None
    exitCode: Optional[int] = None
    output: Optional[str] = None
    error: Optional[str] = None
    outputFile: Optional[str] = None

class CodeExecutionRegistration(pydantic.BaseModel):
    registrationId: str
    command: str
    workingDirectory: Optional[str] = None
    description: Optional[str] = None
    arguments: Optional[str] = None
    timeoutSeconds: Optional[int] = None
    enabled: bool

@component(bind_to=[DeepResearchOrchestrated, A2AAgent, A2AReactAgent])
@injectable()
class CodeRunnerAgent(DeepResearchOrchestrated, A2AReactAgent):
    """Agent that provides tools for code execution based on the commit-diff-context GraphQL schema."""

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver, model_provider: ModelProvider, 
                 cdc_server: CdcServerConfigProps, tool_call_decorator: ToolCallDecorator):
        self_card: AgentCardItem = agent_config.agents[self.__class__.__name__]
        DeepResearchOrchestrated.__init__(self, self_card)
        A2AReactAgent.__init__(self, agent_config, 
                               [
                                   self.produce_execute_code(),
                                   self.produce_execute_code_with_output_file(),
                                   self.produce_register_code_execution(),
                                   self.produce_update_code_execution_registration(),
                                   self.produce_delete_code_execution_registration(),
                                   self.produce_retrieve_executions(),
                                   self.produce_retrieve_registrations(),
                                   self.produce_get_code_execution_registration(),
                                   self.produce_get_execution_output()
                               ], 
                               self_card.agent_descriptor.system_instruction,
                               memory_saver, model_provider)
        self.tool_call_decorator = tool_call_decorator
        self.cdc_server = cdc_server

    def produce_execute_code(self):
        @tool
        def execute_code(registration_id: str, arguments: str = None, timeout_seconds: int = None) -> CodeExecutionResult:
            """Execute code using a registered code execution configuration.
            
            Args:
                registration_id: ID of the registered code execution to run
                arguments: Optional arguments to pass to the command
                timeout_seconds: Optional timeout in seconds
                
            Returns:
                Result of the code execution including success status, output, and error
            """
            query = """
            mutation ExecuteCode($options: CodeExecutionOptions!) {
                execute(options: $options) {
                    success
                    output
                    error
                    executionId
                    exitCode
                    executionTime
                    outputFile
                }
            }
            """
            
            variables = {
                "options": {
                    "registrationId": registration_id,
                    "arguments": arguments,
                    "timeoutSeconds": timeout_seconds
                }
            }
            
            try:
                return execute_graphql_request(
                    endpoint=self.cdc_server.graphql_endpoint,
                    query=query,
                    variables=variables,
                    result_key="execute",
                    model_class=CodeExecutionResult
                )
            except Exception as e:
                return CodeExecutionResult(
                    success=False,
                    error=f"Failed to execute code: {str(e)}"
                )
    
    def produce_execute_code_with_output_file(self):
        @tool
        def execute_code_with_output_file(registration_id: str, output_file_path: str, 
                                         arguments: str = None, timeout_seconds: int = None) -> CodeExecutionResult:
            """Execute code and write the output to a file.
            
            Args:
                registration_id: ID of the registered code execution to run
                output_file_path: Path where the output should be written
                arguments: Optional arguments to pass to the command
                timeout_seconds: Optional timeout in seconds
                
            Returns:
                Result of the code execution including success status, output, and error
            """
            query = """
            mutation ExecuteCodeWithOutputFile($options: CodeExecutionOptions!, $outputFilePath: String!) {
                executeWithOutputFile(options: $options, outputFilePath: $outputFilePath) {
                    success
                    output
                    error
                    executionId
                    exitCode
                    executionTime
                    outputFile
                }
            }
            """
            
            variables = {
                "options": {
                    "registrationId": registration_id,
                    "arguments": arguments,
                    "timeoutSeconds": timeout_seconds,
                    "writeToFile": True
                },
                "outputFilePath": output_file_path
            }
            
            try:
                return execute_graphql_request(
                    endpoint=self.cdc_server.graphql_endpoint,
                    query=query,
                    variables=variables,
                    result_key="executeWithOutputFile",
                    model_class=CodeExecutionResult
                )
            except Exception as e:
                return CodeExecutionResult(
                    success=False,
                    error=f"Failed to execute code with output file: {str(e)}"
                )
    
    def produce_register_code_execution(self):
        @tool
        def register_code_execution(registration_id: str, command: str, working_directory: str = None,
                                   description: str = None, arguments: str = None, 
                                   timeout_seconds: int = None, enabled: bool = True) -> CodeExecutionRegistration:
            """Register a new code execution configuration.
            
            Args:
                registration_id: Unique identifier for this code execution registration
                command: The command to execute
                working_directory: Optional working directory for command execution
                description: Optional description of the command
                arguments: Optional default arguments for the command
                timeout_seconds: Optional default timeout in seconds
                enabled: Whether this registration is enabled
                
            Returns:
                The registered code execution configuration
            """
            query = """
            mutation RegisterCodeExecution($registration: CodeExecutionRegistrationIn!) {
                registerCodeExecution(codeExecutionRegistration: $registration) {
                    registrationId
                    command
                    workingDirectory
                    description
                    arguments
                    timeoutSeconds
                    enabled
                }
            }
            """
            
            variables = {
                "registration": {
                    "registrationId": registration_id,
                    "command": command,
                    "workingDirectory": working_directory,
                    "description": description,
                    "arguments": arguments,
                    "timeoutSeconds": timeout_seconds,
                    "enabled": enabled
                }
            }
            
            try:
                return execute_graphql_request(
                    endpoint=self.cdc_server.graphql_endpoint,
                    query=query,
                    variables=variables,
                    result_key="registerCodeExecution",
                    model_class=CodeExecutionRegistration
                )
            except Exception as e:
                return CodeExecutionRegistration(
                    registrationId="",
                    command="",
                    enabled=False,
                    error=f"Failed to register code execution: {str(e)}"
                )
    
    def produce_update_code_execution_registration(self):
        @tool
        def update_code_execution_registration(id: str, enabled: bool = None, command: str = None,
                                              working_directory: str = None, arguments: str = None,
                                              timeout_seconds: int = None) -> CodeExecutionRegistration:
            """Update an existing code execution registration.
            
            Args:
                id: ID of the registration to update
                enabled: Optional new enabled status
                command: Optional new command
                working_directory: Optional new working directory
                arguments: Optional new arguments
                timeout_seconds: Optional new timeout in seconds
                
            Returns:
                The updated code execution registration
            """
            query = """
            mutation UpdateCodeExecutionRegistration($id: String!, $enabled: Boolean, $command: String,
                                                    $workingDirectory: String, $arguments: String,
                                                    $timeoutSeconds: Int) {
                updateCodeExecutionRegistration(id: $id, enabled: $enabled, command: $command,
                                               workingDirectory: $workingDirectory, arguments: $arguments,
                                               timeoutSeconds: $timeoutSeconds) {
                    registrationId
                    command
                    workingDirectory
                    description
                    arguments
                    timeoutSeconds
                    enabled
                }
            }
            """
            
            variables = {
                "id": id
            }
            
            if enabled is not None:
                variables["enabled"] = enabled
            if command is not None:
                variables["command"] = command
            if working_directory is not None:
                variables["workingDirectory"] = working_directory
            if arguments is not None:
                variables["arguments"] = arguments
            if timeout_seconds is not None:
                variables["timeoutSeconds"] = timeout_seconds
            
            try:
                return execute_graphql_request(
                    endpoint=self.cdc_server.graphql_endpoint,
                    query=query,
                    variables=variables,
                    result_key="updateCodeExecutionRegistration",
                    model_class=CodeExecutionRegistration
                )
            except Exception as e:
                return CodeExecutionRegistration(
                    registrationId=id,
                    command="",
                    enabled=False,
                    error=f"Failed to update code execution registration: {str(e)}"
                )
    
    def produce_delete_code_execution_registration(self):
        @tool
        def delete_code_execution_registration(id: str) -> bool:
            """Delete a code execution registration.
            
            Args:
                id: ID of the registration to delete
                
            Returns:
                True if the deletion was successful, False otherwise
            """
            query = """
            mutation DeleteCodeExecutionRegistration($id: String!) {
                deleteCodeExecutionRegistration(id: $id)
            }
            """
            
            variables = {
                "id": id
            }
            
            try:
                result = execute_graphql_request(
                    endpoint=self.cdc_server.graphql_endpoint,
                    query=query,
                    variables=variables,
                    result_key="deleteCodeExecutionRegistration",
                    model_class=bool
                )
                return result
            except Exception as e:
                LoggerFacade.error(f"Failed to delete code execution registration: {str(e)}")
                return False
    
    def produce_retrieve_executions(self):
        @tool
        def retrieve_executions() -> List[CodeExecution]:
            """Retrieve all code executions.
            
            Returns:
                List of code executions
            """
            query = """
            query RetrieveExecutions {
                retrieveExecutions {
                    id
                    command
                    status
                    startTime
                    endTime
                    exitCode
                    output
                    error
                    outputFile
                }
            }
            """
            
            try:
                return execute_graphql_request(
                    endpoint=self.cdc_server.graphql_endpoint,
                    query=query,
                    variables={},
                    result_key="retrieveExecutions",
                    model_class=List[CodeExecution]
                )
            except Exception as e:
                LoggerFacade.error(f"Failed to retrieve executions: {str(e)}")
                return []
    
    def produce_retrieve_registrations(self):
        @tool
        def retrieve_registrations() -> List[CodeExecutionRegistration]:
            """Retrieve all code execution registrations.
            
            Returns:
                List of code execution registrations
            """
            query = """
            query RetrieveRegistrations {
                retrieveRegistrations {
                    registrationId
                    command
                    workingDirectory
                    description
                    arguments
                    timeoutSeconds
                    enabled
                }
            }
            """
            
            try:
                return execute_graphql_request(
                    endpoint=self.cdc_server.graphql_endpoint,
                    query=query,
                    variables={},
                    result_key="retrieveRegistrations",
                    model_class=List[CodeExecutionRegistration]
                )
            except Exception as e:
                LoggerFacade.error(f"Failed to retrieve registrations: {str(e)}")
                return []
    
    def produce_get_code_execution_registration(self):
        @tool
        def get_code_execution_registration(id: str) -> CodeExecutionRegistration:
            """Get a specific code execution registration.
            
            Args:
                id: ID of the registration to get
                
            Returns:
                The code execution registration with the specified ID
            """
            query = """
            query GetCodeExecutionRegistration($id: String!) {
                getCodeExecutionRegistration(id: $id) {
                    registrationId
                    command
                    workingDirectory
                    description
                    arguments
                    timeoutSeconds
                    enabled
                }
            }
            """
            
            variables = {
                "id": id
            }
            
            try:
                return execute_graphql_request(
                    endpoint=self.cdc_server.graphql_endpoint,
                    query=query,
                    variables=variables,
                    result_key="getCodeExecutionRegistration",
                    model_class=CodeExecutionRegistration
                )
            except Exception as e:
                return CodeExecutionRegistration(
                    registrationId="",
                    command="",
                    enabled=False,
                    error=f"Failed to get code execution registration: {str(e)}"
                )
    
    def produce_get_execution_output(self):
        @tool
        def get_execution_output(execution_id: str) -> CodeExecutionResult:
            """Get the output of a specific code execution.
            
            Args:
                execution_id: ID of the execution to get output for
                
            Returns:
                The code execution result with output and error information
            """
            query = """
            query GetExecutionOutput($executionId: String!) {
                getExecutionOutput(executionId: $executionId) {
                    success
                    output
                    error
                    executionId
                    exitCode
                    executionTime
                    outputFile
                }
            }
            """
            
            variables = {
                "executionId": execution_id
            }
            
            try:
                return execute_graphql_request(
                    endpoint=self.cdc_server.graphql_endpoint,
                    query=query,
                    variables=variables,
                    result_key="getExecutionOutput",
                    model_class=CodeExecutionResult
                )
            except Exception as e:
                return CodeExecutionResult(
                    success=False,
                    error=f"Failed to get execution output: {str(e)}"
                )

