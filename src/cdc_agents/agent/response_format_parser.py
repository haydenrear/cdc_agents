import abc
import json
import re
from typing import Dict, Any, Optional, List

from langchain_core.messages import BaseMessage

from cdc_agents.common.types import ResponseFormat
from python_di.configs.autowire import injectable
from python_di.configs.component import component
from python_util.logger.logger import LoggerFacade


class ResponseFormatBuilder:
    """Builder class to accumulate parsing results from various ResponseFormatParser implementations."""

    def __init__(self):
        self.status: Optional[str] = None
        self.message: Optional[str] = None
        self.route_to: Optional[str] = None
        self.history: Optional[List[BaseMessage]] = None
        self.content: Optional[str] = None
        self.raw_content: Optional[str] = None
        self.is_tool_message: bool = False
        self.additional_context: Optional[str] = None
        self.next_agent: Optional[str] = None

    def set_status(self, status: str) -> 'ResponseFormatBuilder':
        self.status = status
        return self

    def set_message(self, message: str) -> 'ResponseFormatBuilder':
        self.message = message
        return self

    def set_route_to(self, route_to: str) -> 'ResponseFormatBuilder':
        self.route_to = route_to
        return self

    def set_history(self, history: List[BaseMessage]) -> 'ResponseFormatBuilder':
        self.history = history
        return self

    def set_content(self, content: str) -> 'ResponseFormatBuilder':
        self.content = content
        return self

    def set_raw_content(self, raw_content: str) -> 'ResponseFormatBuilder':
        self.raw_content = raw_content
        return self

    def set_is_tool_message(self, is_tool: bool) -> 'ResponseFormatBuilder':
        self.is_tool_message = is_tool
        return self

    def set_additional_context(self, additional_context: str) -> 'ResponseFormatBuilder':
        self.additional_context = additional_context
        return self

    def set_next_agent(self, next_agent: str) -> 'ResponseFormatBuilder':
        self.next_agent = next_agent
        return self

    def build(self) -> ResponseFormat:
        """Build the final ResponseFormat object."""
        message = self.additional_context if self.additional_context is not None else self.content

        if self.is_tool_message:
            return ResponseFormat(
                status="goto_agent",
                history=self.history or [],
                message=self.content,
                route_to="orchestrator"
            )

        # Use message if set, otherwise use content
        final_message = self.message if self.message is not None else message

        try:
            if isinstance(final_message, dict):
                final_message = json.dumps(final_message)
        except Exception:
            final_message = str(final_message) if final_message is not None else ""

        # Ensure status is valid
        valid_status = self.status if self.status in ["input_required", "completed", "error", "goto_agent"] else "completed"

        return ResponseFormat(
            status=valid_status,
            message=final_message,
            history=self.history or [],
            route_to=self.route_to or self.next_agent
        )


class ResponseFormatParser(abc.ABC):
    """Abstract base class for response format parsers following the visitor pattern."""

    @abc.abstractmethod
    def parse(self, builder: ResponseFormatBuilder, last_message: BaseMessage, values: Dict[str, Any]) -> ResponseFormatBuilder:
        """Parse the message and update the builder with relevant information."""
        pass

    def ordering(self) -> int:
        """Return the order in which this parser should be executed. Lower values run first."""
        return 0


@component(bind_to=[ResponseFormatParser])
@injectable()
class MessageTypeResponseFormatParser(ResponseFormatParser):
    """Parser to handle basic message type detection and content extraction."""

    def parse(self, builder: ResponseFormatBuilder, last_message: BaseMessage, values: Dict[str, Any]) -> ResponseFormatBuilder:
        messages = values.get('messages', [])
        content = ''.join([str(c) for c in last_message.content]) if isinstance(last_message.content, list) else str(last_message.content)

        builder.set_history(messages)
        builder.set_raw_content(content)
        builder.set_content(content.replace('**', ''))

        if last_message.type == 'tool':
            builder.set_is_tool_message(True)

        return builder

    def ordering(self) -> int:
        return 0


@component(bind_to=[ResponseFormatParser])
@injectable()
class StatusResponseFormatParser(ResponseFormatParser):
    """Parser to extract status information using regex."""

    def __init__(self):
        self.STATUS_RX = re.compile(
            r"""^.*?
            STATUS\s*:\s*
            (?P<state>[A-Za-z_]+)
            \s*$
            """,
            re.IGNORECASE | re.VERBOSE | re.MULTILINE
        )
        self.status = set([])

    def add_status(self, status):
        for s in status:
            self.status.add(s)

    def parse(self, builder: ResponseFormatBuilder, last_message: BaseMessage, values: Dict[str, Any]) -> ResponseFormatBuilder:
        if builder.is_tool_message:
            return builder

        content = builder.content or ""
        match = self.STATUS_RX.search(content)

        if match:
            status_token = self._get_match_group(match)
            if status_token == 'skip':
                status_token = "completed"
            if status_token == 'input_needed':
                status_token = "input_required"

            if status_token in self.status:
                builder.set_status(status_token)
            else:
                LoggerFacade.error(f"Found unknown status token {status_token}")

            # Remove the status header from content
            header_end = content.find("\n", match.end())
            remaining_content = content[header_end + 1:] if header_end != -1 else ""
            builder.set_content(remaining_content)

        return builder

    def _get_match_group(self, match):
        status_token = match.group("state")
        if status_token is not None:
            status_token = status_token.strip()
        return status_token

    def ordering(self) -> int:
        return 10


@component(bind_to=[ResponseFormatParser])
@injectable()
class NextAgentResponseFormatParser(ResponseFormatParser):
    """Parser to extract next agent information using regex."""

    def __init__(self):
        self.NEXT_AGENT_RX = re.compile(r"NEXT AGENT\s*:\s*(?P<state>[A-Za-z0-9_]+)", re.IGNORECASE)
        self.possible_agents = set([])

    def set_agents(self, agents):
        for a in agents:
            self.possible_agents.add(a)

    def parse(self, builder: ResponseFormatBuilder, last_message: BaseMessage, values: Dict[str, Any]) -> ResponseFormatBuilder:
        if builder.is_tool_message:
            return builder

        content = builder.content or ""

        for line in content.splitlines():
            match = self.NEXT_AGENT_RX.search(line)
            if match:
                agent = self._get_match_group(match)
                if agent == 'skip':
                    agent = None
                elif agent is not None and agent in self.possible_agents:
                    builder.set_next_agent(agent)
                else:
                    LoggerFacade.error(f"Found unknown agent {agent}")
                break

        return builder

    def _get_match_group(self, match):
        agent = match.group("state")
        if agent is not None:
            agent = agent.strip()
        return agent

    def ordering(self) -> int:
        return 20


@component(bind_to=[ResponseFormatParser])
@injectable()
class AdditionalContextResponseFormatParser(ResponseFormatParser):
    """Parser to extract additional context information using regex."""

    def __init__(self):
        self.ADDITIONAL_CTX_RX = re.compile(r"ADDITIONAL CONTEXT\s*:\s*(?P<state>.*)", re.IGNORECASE)

    def parse(self, builder: ResponseFormatBuilder, last_message: BaseMessage, values: Dict[str, Any]) -> ResponseFormatBuilder:
        if builder.is_tool_message:
            return builder

        content = builder.content or ""
        additional_ctx = None
        found_ctx = False

        for line in content.splitlines():
            if not found_ctx:
                match = self.ADDITIONAL_CTX_RX.search(line)
                if match:
                    additional_ctx = self._get_match_group(match)
                    found_ctx = True
            else:
                # Continue accumulating additional context lines
                if additional_ctx is None and line is not None and len(line) != 0:
                    additional_ctx = line
                elif line is not None and len(line) != 0:
                    additional_ctx += '\n' + line

        if additional_ctx is not None and len(additional_ctx) != 0:
            builder.set_additional_context(additional_ctx)

        return builder

    def _get_match_group(self, match):
        state = match.group("state")
        if state is not None:
            state = state.strip()
        return state

    def ordering(self) -> int:
        return 30


@component(bind_to=[ResponseFormatParser])
@injectable()
class StatusValidationResponseFormatParser(ResponseFormatParser):
    """Parser to validate and normalize status values."""
    def __init__(self):
        self.status = set([])
        self.completed_token = None

    def add_status(self, status, completed_status):
        for s in status:
            self.status.add(s)
        self.completed_token = completed_status


    def parse(self, builder: ResponseFormatBuilder, last_message: BaseMessage, values: Dict[str, Any]) -> ResponseFormatBuilder:
        if not self.completed_token:
            raise NotImplementedError("Did not initialize status.")

        if builder.is_tool_message:
            return builder

        status = builder.status
        if status:
            did_any_status = False
            for s in self.status:
                if status.startswith(s):
                    builder.set_status(s)
                    did_any_status = True
                    break

            if not did_any_status:
                LoggerFacade.info(f"Found unknown status token {status}.")
                builder.set_status(self.completed_token)

        return builder

    def ordering(self) -> int:
        return 100
