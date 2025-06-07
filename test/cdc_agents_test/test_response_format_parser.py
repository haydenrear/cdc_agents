import typing
import unittest
import unittest.mock
import uuid

from langchain_core.messages import ToolMessage
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agents.deep_code_research_agent import DeepCodeOrchestrator
from cdc_agents.agents.test_graph.test_graph_cdc_code_search_agent import TestGraphCdcCodeSearchAgent
from cdc_agents.config.agent_config import AgentConfig
from cdc_agents.config.agent_config_props import AgentConfigProps
from cdc_agents.model_server.model_provider import ModelProvider
from cdc_agents.model_server.model_server_model import ModelServerModel
from cdc_agents_test.fixtures.agent_fixtures import (
    create_test_orchestrator, TestA2AAgent, TestOrchestratorAgent
)
from python_di.configs.bean import test_inject
from python_di.configs.test import test_booter, boot_test
from python_di.inject.profile_composite_injector.inject_context_di import autowire_fn
from unittest.mock import Mock
from langchain_core.messages import BaseMessage, AIMessage, ToolMessage

from cdc_agents.agent.response_format_parser import (
    ResponseFormatBuilder,
    MessageTypeResponseFormatParser,
    StatusResponseFormatParser,
    NextAgentResponseFormatParser,
    AdditionalContextResponseFormatParser,
    StatusValidationResponseFormatParser, ResponseFormatParser
)
from cdc_agents.common.types import ResponseFormat


@test_booter(scan_root_module=AgentConfig)
class ServerRunnerBoot:
    pass

@boot_test(ctx=ServerRunnerBoot)
class TestResponseFormatParser(unittest.TestCase):

    parsers: typing.List[ResponseFormatParser]
    server: DeepCodeOrchestrator

    @test_inject(profile='test')
    @autowire_fn(profile='test')
    def construct(self,
                  parsers: typing.List[ResponseFormatParser],
                  server: DeepCodeOrchestrator):
        TestResponseFormatParser.parsers = parsers
        TestResponseFormatParser.server = server
        sorted(TestResponseFormatParser.parsers, key=lambda p: p.ordering())


    def test_basic_message_parsing(self):
        """Test basic message type detection and content extraction."""
        message = AIMessage(content="Hello world")
        values = {"messages": [message]}

        builder = ResponseFormatBuilder()


        result = self.do_parse(builder, message, values)

        self.assertEqual(result.raw_content, "Hello world")
        self.assertEqual(result.content, "Hello world")
        self.assertEqual(result.history, [message])
        self.assertFalse(result.is_tool_message)

    def test_tool_message_parsing(self):
        """Test tool message detection."""
        message = ToolMessage(content="Tool result", tool_call_id="123")
        values = {"messages": [message]}

        builder = ResponseFormatBuilder()


        result = self.do_parse(builder, message, values)

        self.assertTrue(result.is_tool_message)

    def test_status_parsing(self):
        """Test status extraction from message content."""
        message = AIMessage(content="STATUS: completed\nThis is the response content")
        values = {"messages": [message]}

        builder = ResponseFormatBuilder()
        builder.set_content("STATUS: completed\nThis is the response content")


        result = self.do_parse(builder, message, values)

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.content, "This is the response content")

    def test_status_parsing_with_skip(self):
        """Test status parsing with 'skip' value converts to 'completed'."""
        message = AIMessage(content="STATUS: skip\nContent here")
        values = {"messages": [message]}

        builder = ResponseFormatBuilder()
        builder.set_content("STATUS: skip\nContent here")


        result = self.do_parse(builder, message, values)

        self.assertEqual(result.status, "completed")

    def test_status_parsing_with_input_needed(self):
        """Test status parsing with 'input_needed' converts to 'input_required'."""
        message = AIMessage(content="STATUS: input_needed\nNeed more info")
        values = {"messages": [message]}

        builder = ResponseFormatBuilder()
        builder.set_content("STATUS: input_needed\nNeed more info")


        result = self.do_parse(builder, message, values)

        self.assertEqual(result.status, "input_required")

    def test_next_agent_parsing(self):
        """Test next agent extraction."""
        content = f"NEXT AGENT: {TestGraphCdcCodeSearchAgent.__name__}\nSome other content"
        message = AIMessage(content=content)
        values = {"messages": [message]}

        builder = ResponseFormatBuilder()
        builder.set_content(content)


        result = self.do_parse(builder, message, values)

        self.assertEqual(result.next_agent, TestGraphCdcCodeSearchAgent.__name__)

    def do_parse(self, builder, message, values):
        for p in self.parsers:
            builder = p.parse(builder, message, values)
        return builder

    def test_next_agent_parsing_with_skip(self):
        """Test next agent parsing with 'skip' value."""
        content = "NEXT AGENT: skip\nContent"
        message = AIMessage(content=content)
        values = {"messages": [message]}

        builder = ResponseFormatBuilder()
        builder.set_content(content)


        result = self.do_parse(builder, message, values)

        self.assertIsNone(result.next_agent)

    def test_additional_context_parsing(self):
        """Test additional context extraction."""
        content = """Some content
ADDITIONAL CONTEXT: This is additional context
Line 2 of context
Line 3 of context"""

        message = AIMessage(content=content)
        values = {"messages": [message]}

        builder = ResponseFormatBuilder()
        builder.set_content(content)


        result = self.do_parse(builder, message, values)

        expected_context = """This is additional context
Line 2 of context
Line 3 of context"""
        self.assertEqual(result.additional_context, expected_context)

    def test_status_validation(self):
        """Test status validation and normalization."""
        message = AIMessage(content="Test")
        values = {"messages": [message]}

        builder = ResponseFormatBuilder()
        builder.set_status("unknown_status")


        result = self.do_parse(builder, message, values)

        self.assertEqual(result.status, "completed")

    def test_complete_parsing_flow(self):
        """Test complete parsing flow with all parsers."""
        content = f"""STATUS: input_required
NEXT AGENT: {TestGraphCdcCodeSearchAgent.__name__} 
ADDITIONAL CONTEXT: Please provide your email address
We need this information to proceed."""

        message = AIMessage(content=content)
        values = {"messages": [message]}

        # Initialize builder
        builder = ResponseFormatBuilder()

        # Apply all parsers in order
        builder = self.do_parse(builder, message, values)

        # Build final response
        response = builder.build()

        self.assertEqual(response.status, "input_required")
        self.assertEqual(response.route_to, TestGraphCdcCodeSearchAgent.__name__)
        expected_message = """Please provide your email address
We need this information to proceed."""
        self.assertEqual(response.message, expected_message)

    def test_tool_message_flow(self):
        """Test tool message handling flow."""
        message = ToolMessage(content="Tool execution result", tool_call_id="123")
        values = {"messages": [message]}

        # Initialize builder
        builder = ResponseFormatBuilder()

        # Apply all parsers in order
        builder = self.do_parse(builder, message, values)

        # Build final response
        response = builder.build()

        self.assertEqual(response.status, "goto_agent")
        self.assertEqual(response.route_to, "orchestrator")
        self.assertEqual(response.message, "Tool execution result")

    def get_ordering(self, t):
        for p in self.parsers:
            if isinstance(p, t):
                return p.ordering()
        raise ValueError(f"Could not find parser of type {t.__name__}")

    def test_parser_ordering(self):
        """Test that parsers have correct ordering."""
        message_parser = MessageTypeResponseFormatParser
        status_parser = StatusResponseFormatParser
        next_agent_parser = NextAgentResponseFormatParser
        context_parser = AdditionalContextResponseFormatParser
        validation_parser = StatusValidationResponseFormatParser

        self.assertEqual(self.get_ordering(message_parser), 0)
        self.assertEqual(self.get_ordering(status_parser), 10)
        self.assertEqual(self.get_ordering(next_agent_parser), 20)
        self.assertEqual(self.get_ordering(context_parser), 30)
        self.assertEqual(self.get_ordering(validation_parser), 100)

    def test_list_content_handling(self):
        """Test handling of list content in messages."""
        message = AIMessage(content=["Hello ", "world", "!"])
        values = {"messages": [message]}

        builder = ResponseFormatBuilder()


        result = self.do_parse(builder, message, values)

        self.assertEqual(result.raw_content, "Hello world!")
        self.assertEqual(result.content, "Hello world!")


if __name__ == '__main__':
    unittest.main()
