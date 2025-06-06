import os
import typing
import unittest.mock
import uuid

from langchain_core.messages import ToolMessage
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agents.cdc_server_agent import CdcCodegenAgent
from cdc_agents.agents.deep_code_research_agent import DeepCodeOrchestrator
from cdc_agents.common.server import TaskManager
from cdc_agents.common.types import ResponseFormat
from cdc_agents.config.agent_config import AgentConfig
from cdc_agents.config.agent_config_props import AgentConfigProps
from cdc_agents.model_server.model_provider import ModelProvider
from cdc_agents.model_server.model_server_model import ModelServerModel
from python_di.configs.bean import test_inject
from python_di.configs.test import test_booter, boot_test
from python_di.inject.profile_composite_injector.inject_context_di import autowire_fn
from python_util.logger.logger import LoggerFacade

from cdc_agents_test.test_utils.graphql_mocks import (
    CDCGraphQLMocker, MockCommit, MockCodeSearchResult, MockFileContent,
    create_sample_repository, patch_cdc_tools
)

os.environ['SPRING_PROFILES_ACTIVE'] = 'test,secret'

@test_booter(scan_root_module=AgentConfig)
class ServerRunnerBoot:
    pass

@boot_test(ctx=ServerRunnerBoot)
class ModelServerModelTest(unittest.IsolatedAsyncioTestCase):
    ai_suite: AgentConfigProps
    server: DeepCodeOrchestrator
    model: ModelServerModel
    memory: MemorySaver
    model_provider: ModelProvider


    @test_inject(profile='test')
    @autowire_fn(profile='test')
    def construct(self,
                  ai_suite: AgentConfigProps,
                  server: DeepCodeOrchestrator,
                  model: ModelServerModel,
                  memory_saver: MemorySaver,
                  model_provider: ModelProvider):
        ModelServerModelTest.memory = memory_saver
        ModelServerModelTest.ai_suite = ai_suite
        ModelServerModelTest.server = server
        ModelServerModelTest.model = model
        ModelServerModelTest.model_provider = model_provider


    def test_git_status(self):
        test = str(uuid.uuid4())
        invoked = self.server.invoke(TaskManager.get_user_query_message('Please retrieve the git status of the repository in the directory /Users/hayde/IdeaProjects/drools',
                                                              test),
                                     self.server._create_orchestration_config(test))

        LoggerFacade.info(f"Message: {invoked.content.message}")
        LoggerFacade.info('History:')
        LoggerFacade.info('\n'.join([h.content for h in invoked.content.history]))

        assert invoked
        assert isinstance(invoked.content, ResponseFormat)

    def test_complex_multi_agent_git_workflow(self):
        """Test complex workflow: analyze git history, find problematic commits, suggest fixes"""
        test = str(uuid.uuid4())
        invoked = self.server.invoke(
            TaskManager.get_user_query_message(
                '''In the repository at /Users/hayde/IdeaProjects/drools:
                1. Find commits from the last week that modified Java files
                2. Identify any commits with messages containing "fix" or "bug"
                3. Analyze the changes and suggest potential improvements''',
                test
            ),
            self.server._create_orchestration_config(test)
        )

        LoggerFacade.info(f"Message: {invoked.content.message}")
        LoggerFacade.info('History:')
        LoggerFacade.info('\n'.join([h.content for h in invoked.content.history]))

        assert invoked
        assert isinstance(invoked.content, ResponseFormat)
        assert invoked.content.status == 'completed'
        # Should use git tools multiple times
        git_tool_calls = [t for t in invoked.content.history
                         if isinstance(t, ToolMessage) and 'git' in t.name]
        assert len(git_tool_calls) >= 1
        # Should contain analysis
        assert any(['fix' in str(h.content).lower() or 'bug' in str(h.content).lower()
                   or 'improvement' in str(h.content).lower()
                   for h in invoked.content.history])

    def test_library_enumeration_to_code_search_flow(self):
        """Test flow from library enumeration to code search"""
        test = str(uuid.uuid4())
        invoked = self.server.invoke(
            TaskManager.get_user_query_message(
                '''Find information about the main dependencies used in this project,
                then search for code that imports or uses the most common dependency''',
                test
            ),
            self.server._create_orchestration_config(test)
        )

        LoggerFacade.info(f"Message: {invoked.content.message}")
        LoggerFacade.info('History:')
        LoggerFacade.info('\n'.join([h.content for h in invoked.content.history]))

        assert invoked
        assert isinstance(invoked.content, ResponseFormat)
        assert invoked.content.status == 'completed'
        # Should involve multiple agents
        assert len(invoked.content.history) > 3

    def test_code_generation_with_validation(self):
        """Test code generation followed by execution to validate"""
        test = str(uuid.uuid4())
        invoked = self.server.invoke(
            TaskManager.get_user_query_message(
                '''Generate a Python function that:
                1. Takes a list of numbers as input
                2. Returns the mean, median, and mode
                3. Handles edge cases (empty list, etc.)
                Then test it with sample data: [1, 2, 2, 3, 4, 4, 4, 5]''',
                test
            ),
            self.server._create_orchestration_config(test)
        )

        LoggerFacade.info(f"Message: {invoked.content.message}")
        LoggerFacade.info('History:')
        LoggerFacade.info('\n'.join([h.content for h in invoked.content.history]))

        assert invoked
        assert isinstance(invoked.content, ResponseFormat)
        assert invoked.content.status == 'completed'
        # Should have code execution
        assert any([isinstance(t, ToolMessage) and t.status == 'success'
                   for t in invoked.content.history])
        # Should contain statistics terms
        assert any(['mean' in str(h.content).lower() and 'median' in str(h.content).lower()
                   for h in invoked.content.history])

    def test_human_delegate_interaction_flow(self):
        """Test flow requiring human delegate agent"""
        test = str(uuid.uuid4())
        # This simulates a request that might need human input
        invoked = self.server.invoke(
            TaskManager.get_user_query_message(
                '''I need to make an architectural decision about the database schema.
                Should we use PostgreSQL or MongoDB for the new microservice?
                Consider our existing stack uses PostgreSQL.''',
                test
            ),
            self.server._create_orchestration_config(test)
        )

        LoggerFacade.info(f"Message: {invoked.content.message}")
        LoggerFacade.info('History:')
        LoggerFacade.info('\n'.join([h.content for h in invoked.content.history]))

        assert invoked
        assert isinstance(invoked.content, ResponseFormat)
        # Might route to human delegate or provide analysis
        assert invoked.content.status in ['completed', 'goto_agent', 'input_required']

    def test_summarizer_agent_long_context(self):
        """Test summarizer agent with long context"""
        test = str(uuid.uuid4())
        invoked = self.server.invoke(
            TaskManager.get_user_query_message(
                '''Analyze all README files in /Users/hayde/IdeaProjects,
                summarize the main purposes of each project,
                and create a consolidated summary of the entire codebase''',
                test
            ),
            self.server._create_orchestration_config(test)
        )

        LoggerFacade.info(f"Message: {invoked.content.message}")
        LoggerFacade.info('History:')
        LoggerFacade.info('\n'.join([h.content for h in invoked.content.history]))

        assert invoked
        assert isinstance(invoked.content, ResponseFormat)
        # Should complete with summary
        assert invoked.content.status == 'completed'
        assert 'summary' in invoked.content.message.lower() or 'summarize' in invoked.content.message.lower()

    def test_orchestrator_error_recovery(self):
        """Test orchestrator's ability to recover from agent errors"""
        test = str(uuid.uuid4())
        invoked = self.server.invoke(
            TaskManager.get_user_query_message(
                '''Try to:
                1. Access a file that doesn't exist: /nonexistent/path/file.txt
                2. If that fails, search for any Python files in /Users/hayde/IdeaProjects instead''',
                test
            ),
            self.server._create_orchestration_config(test)
        )

        LoggerFacade.info(f"Message: {invoked.content.message}")
        LoggerFacade.info('History:')
        LoggerFacade.info('\n'.join([h.content for h in invoked.content.history]))

        assert invoked
        assert isinstance(invoked.content, ResponseFormat)
        # Should recover and complete
        assert invoked.content.status == 'completed'
        # Should have tried both operations
        assert len([t for t in invoked.content.history if isinstance(t, ToolMessage)]) >= 2

    def test_multi_stage_code_refactoring(self):
        """Test multi-stage workflow: find code, analyze, suggest refactoring"""
        test = str(uuid.uuid4())
        invoked = self.server.invoke(
            TaskManager.get_user_query_message(
                '''Find any Python files in the project that have functions longer than 50 lines,
                analyze them for code smells, and suggest refactoring strategies''',
                test
            ),
            self.server._create_orchestration_config(test)
        )

        LoggerFacade.info(f"Message: {invoked.content.message}")
        LoggerFacade.info('History:')
        LoggerFacade.info('\n'.join([h.content for h in invoked.content.history]))

        assert invoked
        assert isinstance(invoked.content, ResponseFormat)
        assert invoked.content.status == 'completed'
        # Should involve code analysis
        assert any(['refactor' in str(h.content).lower() or 'function' in str(h.content).lower()
                   for h in invoked.content.history])

    @patch_cdc_tools
    def test_cdc_staged_changes_workflow(self, mocker):
        """Test CDC staged changes workflow"""
        test = str(uuid.uuid4())

        # Add staged changes
        mocker.staged_changes['/Users/hayde/IdeaProjects/example/src/payment.py'] = """
+def validate_amount(amount):
+    return amount > 0 and amount < 1000000
"""

        invoked = self.server.invoke(
            TaskManager.get_user_query_message(
                'Show me the current staged changes and apply them if they look good',
                test
            ),
            self.server._create_orchestration_config(test)
        )

        LoggerFacade.info(f"Message: {invoked.content.message}")
        LoggerFacade.info('History:')
        LoggerFacade.info('\n'.join([h.content for h in invoked.content.history]))

        assert invoked
        assert isinstance(invoked.content, ResponseFormat)
        assert invoked.content.status == 'completed'

    @patch_cdc_tools
    def test_cdc_file_context_retrieval(self, mocker):
        """Test CDC file context retrieval"""
        test = str(uuid.uuid4())

        invoked = self.server.invoke(
            TaskManager.get_user_query_message(
                'Retrieve the content of the payment.py file and analyze it for potential improvements',
                test
            ),
            self.server._create_orchestration_config(test)
        )

        LoggerFacade.info(f"Message: {invoked.content.message}")
        LoggerFacade.info('History:')
        LoggerFacade.info('\n'.join([h.content for h in invoked.content.history]))

        assert invoked
        assert isinstance(invoked.content, ResponseFormat)
        assert invoked.content.status == 'completed'
        # Should contain analysis of the payment module
        assert any(['payment' in str(h.content).lower() or 'process_payment' in str(h.content)
                    for h in invoked.content.history])

    @patch_cdc_tools
    def test_cdc_multi_file_analysis(self, mocker):
        """Test CDC multi-file analysis workflow"""
        test = str(uuid.uuid4())

        # Add another related file
        mocker.add_mock_file(MockFileContent(
            path="/Users/hayde/IdeaProjects/example/src/validation.py",
            content="""
# Validation module

def validate_transaction(transaction):
    if not transaction.get('amount'):
        return False, "Amount is required"
    if not transaction.get('recipient'):
        return False, "Recipient is required"
    return True, "Valid"
"""
        ))

        invoked = self.server.invoke(
            TaskManager.get_user_query_message(
                'Analyze the payment.py and validation.py files together and suggest how they could be better integrated',
                test
            ),
            self.server._create_orchestration_config(test)
        )

        LoggerFacade.info(f"Message: {invoked.content.message}")
        LoggerFacade.info('History:')
        LoggerFacade.info('\n'.join([h.content for h in invoked.content.history]))

        assert invoked
        assert isinstance(invoked.content, ResponseFormat)
        assert invoked.content.status == 'completed'
        # Should analyze both files
        assert any(['payment' in str(h.content).lower() and 'validation' in str(h.content).lower()
                    for h in invoked.content.history])

    @patch_cdc_tools
    def test_cdc_commit_diff_analysis(self, mocker):
        """Test CDC commit diff analysis"""
        test = str(uuid.uuid4())

        invoked = self.server.invoke(
            TaskManager.get_user_query_message(
                'Show me the diff for commit abc123 and explain what changed',
                test
            ),
            self.server._create_orchestration_config(test)
        )

        LoggerFacade.info(f"Message: {invoked.content.message}")
        LoggerFacade.info('History:')
        LoggerFacade.info('\n'.join([h.content for h in invoked.content.history]))

        assert invoked
        assert isinstance(invoked.content, ResponseFormat)
        assert invoked.content.status == 'completed'
        # Should contain diff analysis
        assert any(['diff' in str(h.content).lower() or 'change' in str(h.content).lower()
                    for h in invoked.content.history])

    @unittest.mock.patch('cdc_agents.agents.cdc_server_agent.CdcServerAgentToolCallProvider')
    def test_cdc_code_search_with_mock(self, mock_cdc_provider):
        """Test CDC code search with mocked GraphQL"""
        test = str(uuid.uuid4())

        mock_instance = self._mock_cdc_tools(mock_cdc_provider)

        # Mock code search response
        mock_search_response = {
            'results': [
                {
                    'file': '/Users/hayde/IdeaProjects/test/example.py',
                    'line': 10,
                    'content': 'def example_function():',
                    'score': 0.95
                }
            ],
            'total': 1
        }

        # This would integrate with actual CDC tools when GraphQL is mocked
        invoked = self.server.invoke(
            TaskManager.get_user_query_message(
                'Use the CDC code search to find all functions named "example_function"',
                test
            ),
            self.server._create_orchestration_config(test)
        )

        LoggerFacade.info(f"Message: {invoked.content.message}")
        LoggerFacade.info('History:')
        LoggerFacade.info('\n'.join([h.content for h in invoked.content.history]))

        assert invoked
        assert isinstance(invoked.content, ResponseFormat)

    @patch_cdc_tools
    def test_cdc_commit_analysis_with_mock(self, mocker):
        """Test CDC commit analysis with mocked GraphQL"""
        test = str(uuid.uuid4())

        a: CdcCodegenAgent = typing.cast(CdcCodegenAgent, self.server.agents[CdcCodegenAgent.__name__].agent)
        a.tool_call_provider = mocker

        invoked = self.server.invoke(
            TaskManager.get_user_query_message(
                'Analyze recent commits related to payment processing using CDC tools',
                test
            ),
            self.server._create_orchestration_config(test)
        )

        LoggerFacade.info(f"Message: {invoked.content.message}")
        LoggerFacade.info('History:')
        LoggerFacade.info('\n'.join(['Agent Name: ' + str(h.name if h.name else 'None') + '\n' + h.content for h in invoked.content.history]))

        assert invoked
        assert isinstance(invoked.content, ResponseFormat)
        assert invoked.content.status == 'completed'
        # Verify payment-related analysis
        assert any(['payment' in str(h.content).lower() for h in invoked.content.history])

    def test_concurrent_agent_coordination(self):
        """Test coordination when multiple agents could handle a task"""
        test = str(uuid.uuid4())
        invoked = self.server.invoke(
            TaskManager.get_user_query_message(
                '''I need to:
                1. Find all test files in the project
                2. Generate a test coverage report
                3. Identify areas that need more testing
                Please coordinate this across relevant agents''',
                test
            ),
            self.server._create_orchestration_config(test)
        )

        LoggerFacade.info(f"Message: {invoked.content.message}")
        LoggerFacade.info('History:')
        LoggerFacade.info('\n'.join([h.content for h in invoked.content.history]))

        assert invoked
        assert isinstance(invoked.content, ResponseFormat)
        assert invoked.content.status == 'completed'
        # Should show coordinated effort
        assert len(invoked.content.history) > 4

    def test_agent_state_persistence(self):
        """Test that agent state persists across invocations"""
        test = str(uuid.uuid4())

        # First invocation - set up some context
        invoked1 = self.server.invoke(
            TaskManager.get_user_query_message(
                'Remember that we are working on the drools project at /Users/hayde/IdeaProjects/drools',
                test
            ),
            self.server._create_orchestration_config(test)
        )

        assert invoked1
        assert isinstance(invoked1.content, ResponseFormat)

        # Second invocation - reference previous context
        invoked2 = self.server.invoke(
            TaskManager.get_user_query_message(
                'What project were we just discussing? Show me its git status',
                test
            ),
            self.server._create_orchestration_config(test)
        )

        LoggerFacade.info(f"Message: {invoked2.content.message}")
        LoggerFacade.info('History:')
        LoggerFacade.info('\n'.join([h.content for h in invoked2.content.history]))

        assert invoked2
        assert isinstance(invoked2.content, ResponseFormat)
        # Should reference drools project
        assert 'drools' in invoked2.content.message.lower() or any(['drools' in str(h.content).lower()
                                                                    for h in invoked2.content.history])

    @patch_cdc_tools
    def test_cdc_complex_refactoring_workflow(self, mocker):
        """Test complex CDC workflow: analyze, suggest refactoring, stage changes"""
        test = str(uuid.uuid4())

        invoked = self.server.invoke(
            TaskManager.get_user_query_message(
                '''Using CDC tools:
                1. Search for all payment-related functions
                2. Analyze the code for potential issues
                3. Suggest refactoring improvements
                4. Create staged changes for the improvements''',
                test
            ),
            self.server._create_orchestration_config(test)
        )

        LoggerFacade.info(f"Message: {invoked.content.message}")
        LoggerFacade.info('History:')
        LoggerFacade.info('\n'.join([h.content for h in invoked.content.history]))

        assert invoked
        assert isinstance(invoked.content, ResponseFormat)
        assert invoked.content.status == 'completed'
        # Should show comprehensive workflow
        assert len(invoked.content.history) > 5
        assert any(['refactor' in str(h.content).lower() or 'improve' in str(h.content).lower()
                    for h in invoked.content.history])

    @patch_cdc_tools
    def test_cdc_code_generation_and_validation(self, mocker):
        """Test CDC code generation followed by validation"""
        test = str(uuid.uuid4())

        invoked = self.server.invoke(
            TaskManager.get_user_query_message(
                '''Using CDC tools:
                1. Generate a new utility function for currency conversion
                2. Add appropriate unit tests
                3. Stage the changes for review''',
                test
            ),
            self.server._create_orchestration_config(test)
        )

        LoggerFacade.info(f"Message: {invoked.content.message}")
        LoggerFacade.info('History:')
        LoggerFacade.info('\n'.join([h.content for h in invoked.content.history]))

        assert invoked
        assert isinstance(invoked.content, ResponseFormat)
        assert invoked.content.status == 'completed'
        # Should generate code and tests
        assert any(['currency' in str(h.content).lower() or 'conversion' in str(h.content).lower()
                    for h in invoked.content.history])
        assert any(['test' in str(h.content).lower() for h in invoked.content.history])

    def test_filesystem_search(self):
        """Test basic filesystem search capability"""
        test = str(uuid.uuid4())
        invoked = self.server.invoke(
            TaskManager.get_user_query_message(
                'Search for all Python files in /Users/hayde/IdeaProjects that contain the word "agent"',
                test
            ),
            self.server._create_orchestration_config(test)
        )

        LoggerFacade.info(f"Message: {invoked.content.message}")
        LoggerFacade.info('History:')
        LoggerFacade.info('\n'.join([h.content for h in invoked.content.history]))

        assert invoked
        assert isinstance(invoked.content, ResponseFormat)
        # Check that filesystem tool was used
        assert any([isinstance(t, ToolMessage) and 'filesystem' in t.name
                    for t in invoked.content.history])
        assert invoked.content.status in ['completed', 'goto_agent']

    def test_code_execution_basic(self):
        """Test basic code execution capability"""
        test = str(uuid.uuid4())
        code_snippet = '''
def hello_world():
    return "Hello from test!"

print(hello_world())
'''
        invoked = self.server.invoke(
            TaskManager.get_user_query_message(
                f'Execute this Python code and tell me the output:\n{code_snippet}',
                test
            ),
            self.server._create_orchestration_config(test)
        )

        LoggerFacade.info(f"Message: {invoked.content.message}")
        LoggerFacade.info('History:')
        LoggerFacade.info('\n'.join([h.content for h in invoked.content.history]))

        assert invoked
        assert isinstance(invoked.content, ResponseFormat)
        # Check that code execution happened
        assert any([isinstance(t, ToolMessage) and t.status == 'success'
                    for t in invoked.content.history])
        # Verify output contains expected result
        assert any(['Hello from test!' in str(h.content)
                    for h in invoked.content.history])

    def test_multi_agent_code_search_and_analyze(self):
        """Test multi-agent flow: search for code then analyze it"""
        test = str(uuid.uuid4())
        invoked = self.server.invoke(
            TaskManager.get_user_query_message(
                'Find the DeepCodeAgent class in the codebase and explain its purpose and key methods',
                test
            ),
            self.server._create_orchestration_config(test)
        )

        LoggerFacade.info(f"Message: {invoked.content.message}")
        LoggerFacade.info('History:')
        LoggerFacade.info('\n'.join([h.content for h in invoked.content.history]))

        assert invoked
        assert isinstance(invoked.content, ResponseFormat)
        # Should involve multiple agents - code search and analysis
        assert invoked.content.status == 'completed'
        # Check that the response mentions DeepCodeAgent
        assert 'DeepCodeAgent' in invoked.content.message
        # Verify tool usage
        assert any([isinstance(t, ToolMessage) for t in invoked.content.history])

    def test_git_log_analysis(self):
        """Test git log retrieval and analysis"""
        test = str(uuid.uuid4())
        invoked = self.server.invoke(
            TaskManager.get_user_query_message(
                'Show me the last 5 commits in the repository at /Users/hayde/IdeaProjects/drools and summarize the changes',
                test
            ),
            self.server._create_orchestration_config(test)
        )

        LoggerFacade.info(f"Message: {invoked.content.message}")
        LoggerFacade.info('History:')
        LoggerFacade.info('\n'.join([h.content for h in invoked.content.history]))

        assert invoked
        assert isinstance(invoked.content, ResponseFormat)
        # Check git tool was used
        assert any([isinstance(t, ToolMessage) and 'git' in t.name
                    for t in invoked.content.history])
        assert invoked.content.status in ['completed', 'goto_agent']

    def test_error_handling_invalid_path(self):
        """Test error handling for invalid paths"""
        test = str(uuid.uuid4())
        invoked = self.server.invoke(
            TaskManager.get_user_query_message(
                'Get git status for non-existent path: /invalid/path/that/does/not/exist',
                test
            ),
            self.server._create_orchestration_config(test)
        )

        LoggerFacade.info(f"Message: {invoked.content.message}")
        LoggerFacade.info('History:')
        LoggerFacade.info('\n'.join([h.content for h in invoked.content.history]))

        assert invoked
        assert isinstance(invoked.content, ResponseFormat)
        # Should handle error gracefully
        assert invoked.content.status in ['error', 'completed', 'goto_agent']

    def test_multi_agent_file_discovery_and_read(self):
        """Test multi-agent flow: discover files then read specific one"""
        test = str(uuid.uuid4())
        invoked = self.server.invoke(
            TaskManager.get_user_query_message(
                'Find all configuration files (yml, yaml, json) in /Users/hayde/IdeaProjects and show me the content of the first one you find',
                test
            ),
            self.server._create_orchestration_config(test)
        )

        LoggerFacade.info(f"Message: {invoked.content.message}")
        LoggerFacade.info('History:')
        LoggerFacade.info('\n'.join([h.content for h in invoked.content.history]))

        assert invoked
        assert isinstance(invoked.content, ResponseFormat)
        # Should use filesystem tool for discovery
        assert any([isinstance(t, ToolMessage) and 'filesystem' in t.name
                    for t in invoked.content.history])
        assert invoked.content.status == 'completed'

    def test_code_execution_with_registration(self):
        """Test code execution with registration flow"""
        test = str(uuid.uuid4())
        invoked = self.server.invoke(
            TaskManager.get_user_query_message(
                '''Create a simple Python function that calculates fibonacci numbers,
                register it for later use, and then execute it with n=10''',
                test
            ),
            self.server._create_orchestration_config(test)
        )

        LoggerFacade.info(f"Message: {invoked.content.message}")
        LoggerFacade.info('History:')
        LoggerFacade.info('\n'.join([h.content for h in invoked.content.history]))

        assert invoked
        assert isinstance(invoked.content, ResponseFormat)
        # Should have successful tool calls
        assert any([isinstance(t, ToolMessage) and t.status == 'success'
                    for t in invoked.content.history])
        assert invoked.content.status == 'completed'

    def test_repository_analysis_workflow(self):
        """Test comprehensive repository analysis workflow"""
        test = str(uuid.uuid4())
        invoked = self.server.invoke(
            TaskManager.get_user_query_message(
                '''Analyze the repository structure at /Users/hayde/IdeaProjects/drools:
                1. Show the directory structure
                2. Count the number of Java files
                3. Check if it uses Maven or Gradle''',
                test
            ),
            self.server._create_orchestration_config(test)
        )

        LoggerFacade.info(f"Message: {invoked.content.message}")
        LoggerFacade.info('History:')
        LoggerFacade.info('\n'.join([h.content for h in invoked.content.history]))

        assert invoked
        assert isinstance(invoked.content, ResponseFormat)
        # Should use multiple tools
        assert len([t for t in invoked.content.history if isinstance(t, ToolMessage)]) > 1
        assert invoked.content.status == 'completed'
        # Response should contain analysis results
        assert any(['java' in str(h.content).lower() or 'maven' in str(h.content).lower() or 'gradle' in str(h.content).lower()
                    for h in invoked.content.history])

    def test_agent_routing_decision(self):
        """Test that orchestrator correctly routes between agents"""
        test = str(uuid.uuid4())
        invoked = self.server.invoke(
            TaskManager.get_user_query_message(
                'First, search for test files in the codebase, then create a simple unit test example',
                test
            ),
            self.server._create_orchestration_config(test)
        )

        LoggerFacade.info(f"Message: {invoked.content.message}")
        LoggerFacade.info('History:')
        LoggerFacade.info('\n'.join([h.content for h in invoked.content.history]))

        assert invoked
        assert isinstance(invoked.content, ResponseFormat)
        # Should show agent transitions
        assert invoked.content.status == 'completed'
        # Check for multiple agent involvement
        history_contents = [str(h.content) for h in invoked.content.history]
        assert len(history_contents) > 2  # Multiple steps indicate agent routing

    @patch_cdc_tools
    def test_mock_graphql_code_search(self, mocker):
        """Test code search with mocked GraphQL responses"""
        test = str(uuid.uuid4())

        # Add specific search results for this test
        mocker.add_mock_search_result(MockCodeSearchResult(
            file='/Users/hayde/IdeaProjects/example/src/main.py',
            line=42,
            content='def process_data(input_data):',
            context='    """Process input data"""\n    def process_data(input_data):\n        return processed'
        ))

        invoked = self.server.invoke(
            TaskManager.get_user_query_message(
                'Search for the process_data function in the codebase using the code server',
                test
            ),
            self.server._create_orchestration_config(test)
        )

        LoggerFacade.info(f"Message: {invoked.content.message}")
        LoggerFacade.info('History:')
        LoggerFacade.info('\n'.join([h.content for h in invoked.content.history]))

        assert invoked
        assert isinstance(invoked.content, ResponseFormat)
        assert invoked.content.status == 'completed'
        # Verify the search was performed
        assert any(['process_data' in str(h.content) for h in invoked.content.history])
