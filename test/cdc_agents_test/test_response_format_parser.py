import unittest
from unittest.mock import Mock
from langchain_core.messages import BaseMessage, AIMessage, ToolMessage

from cdc_agents.agent.response_format_parser import (
    ResponseFormatBuilder,
    MessageTypeResponseFormatParser,
    StatusResponseFormatParser,
    NextAgentResponseFormatParser,
    AdditionalContextResponseFormatParser,
    StatusValidationResponseFormatParser
)
from cdc_agents.common.types import ResponseFormat


class TestResponseFormatParser(unittest.TestCase):

    def setUp(self):
        self.parsers = [
            MessageTypeResponseFormatParser(),
            StatusResponseFormatParser(),
            NextAgentResponseFormatParser(),
            AdditionalContextResponseFormatParser(),
            StatusValidationResponseFormatParser()
        ]

    def test_basic_message_parsing(self):
        """Test basic message type detection and content extraction."""
        message = AIMessage(content="Hello world")
        values = {"messages": [message]}

        builder = ResponseFormatBuilder()
        parser = MessageTypeResponseFormatParser()

        result = parser.parse(builder, message, values)

        self.assertEqual(result.raw_content, "Hello world")
        self.assertEqual(result.content, "Hello world")
        self.assertEqual(result.history, [message])
        self.assertFalse(result.is_tool_message)

    def test_tool_message_parsing(self):
        """Test tool message detection."""
        message = ToolMessage(content="Tool result", tool_call_id="123")
        values = {"messages": [message]}

        builder = ResponseFormatBuilder()
        parser = MessageTypeResponseFormatParser()

        result = parser.parse(builder, message, values)

        self.assertTrue(result.is_tool_message)

    def test_status_parsing(self):
        """Test status extraction from message content."""
        message = AIMessage(content="STATUS: completed\nThis is the response content")
        values = {"messages": [message]}

        builder = ResponseFormatBuilder()
        builder.set_content("STATUS: completed\nThis is the response content")

        parser = StatusResponseFormatParser()
        result = parser.parse(builder, message, values)

        self.assertEqual(result.status, "completed")
        self.assertEqual(result.content, "This is the response content")

    def test_status_parsing_with_skip(self):
        """Test status parsing with 'skip' value converts to 'completed'."""
        message = AIMessage(content="STATUS: skip\nContent here")
        values = {"messages": [message]}

        builder = ResponseFormatBuilder()
        builder.set_content("STATUS: skip\nContent here")

        parser = StatusResponseFormatParser()
        result = parser.parse(builder, message, values)

        self.assertEqual(result.status, "completed")

    def test_status_parsing_with_input_needed(self):
        """Test status parsing with 'input_needed' converts to 'input_required'."""
        message = AIMessage(content="STATUS: input_needed\nNeed more info")
        values = {"messages": [message]}

        builder = ResponseFormatBuilder()
        builder.set_content("STATUS: input_needed\nNeed more info")

        parser = StatusResponseFormatParser()
        result = parser.parse(builder, message, values)

        self.assertEqual(result.status, "input_required")

    def test_next_agent_parsing(self):
        """Test next agent extraction."""
        content = "NEXT AGENT: data_processor\nSome other content"
        message = AIMessage(content=content)
        values = {"messages": [message]}

        builder = ResponseFormatBuilder()
        builder.set_content(content)

        parser = NextAgentResponseFormatParser()
        result = parser.parse(builder, message, values)

        self.assertEqual(result.next_agent, "data_processor")

    def test_next_agent_parsing_with_skip(self):
        """Test next agent parsing with 'skip' value."""
        content = "NEXT AGENT: skip\nContent"
        message = AIMessage(content=content)
        values = {"messages": [message]}

        builder = ResponseFormatBuilder()
        builder.set_content(content)

        parser = NextAgentResponseFormatParser()
        result = parser.parse(builder, message, values)

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

        parser = AdditionalContextResponseFormatParser()
        result = parser.parse(builder, message, values)

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

        parser = StatusValidationResponseFormatParser()
        result = parser.parse(builder, message, values)

        self.assertEqual(result.status, "completed")

    def test_complete_parsing_flow(self):
        """Test complete parsing flow with all parsers."""
        content = """STATUS: input_required
NEXT AGENT: user_input_handler
ADDITIONAL CONTEXT: Please provide your email address
We need this information to proceed."""

        message = AIMessage(content=content)
        values = {"messages": [message]}

        # Sort parsers by ordering
        sorted_parsers = sorted(self.parsers, key=lambda p: p.ordering())

        # Initialize builder
        builder = ResponseFormatBuilder()

        # Apply all parsers in order
        for parser in sorted_parsers:
            builder = parser.parse(builder, message, values)

        # Build final response
        response = builder.build()

        self.assertEqual(response.status, "input_required")
        self.assertEqual(response.route_to, "user_input_handler")
        expected_message = """Please provide your email address
We need this information to proceed."""
        self.assertEqual(response.message, expected_message)

    def test_tool_message_flow(self):
        """Test tool message handling flow."""
        message = ToolMessage(content="Tool execution result", tool_call_id="123")
        values = {"messages": [message]}

        # Sort parsers by ordering
        sorted_parsers = sorted(self.parsers, key=lambda p: p.ordering())

        # Initialize builder
        builder = ResponseFormatBuilder()

        # Apply all parsers in order
        for parser in sorted_parsers:
            builder = parser.parse(builder, message, values)

        # Build final response
        response = builder.build()

        self.assertEqual(response.status, "goto_agent")
        self.assertEqual(response.route_to, "orchestrator")
        self.assertEqual(response.message, "Tool execution result")

    def test_parser_ordering(self):
        """Test that parsers have correct ordering."""
        message_parser = MessageTypeResponseFormatParser()
        status_parser = StatusResponseFormatParser()
        next_agent_parser = NextAgentResponseFormatParser()
        context_parser = AdditionalContextResponseFormatParser()
        validation_parser = StatusValidationResponseFormatParser()

        self.assertEqual(message_parser.ordering(), 0)
        self.assertEqual(status_parser.ordering(), 10)
        self.assertEqual(next_agent_parser.ordering(), 20)
        self.assertEqual(context_parser.ordering(), 30)
        self.assertEqual(validation_parser.ordering(), 100)

    def test_list_content_handling(self):
        """Test handling of list content in messages."""
        message = AIMessage(content=["Hello ", "world", "!"])
        values = {"messages": [message]}

        builder = ResponseFormatBuilder()
        parser = MessageTypeResponseFormatParser()

        result = parser.parse(builder, message, values)

        self.assertEqual(result.raw_content, "Hello world!")
        self.assertEqual(result.content, "Hello world!")


if __name__ == '__main__':
    unittest.main()
