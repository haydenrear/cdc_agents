import dataclasses
import subprocess
import typing

from langchain_core.messages import BaseMessage
import unittest
from typing import AsyncIterable, Dict, Any

from langchain_core.runnables import AddableDict

from cdc_agents.agent.a2a import A2AAgent
from cdc_agents.common.types import ResponseFormat
from unittest.mock import MagicMock

class TestA2AResponse(unittest.TestCase):
    def test_a2a_response(self):
        class TestA2A(A2AAgent):
            async def stream(self, query, sessionId, graph=None) -> AsyncIterable[Dict[str, Any]]:
                pass

            def get_agent_response(self, config, graph):
                pass

            def invoke(self, query, sessionId) -> typing.Union[AddableDict, ResponseFormat]:
                pass

        t = TestA2A()
        class Graph:
            pass
        graph = Graph()

        @dataclasses.dataclass(init=True)
        class GraphState:
            values: dict[str, str]

        g = GraphState({'messages': [BaseMessage(content=["""
        status: completed
        hello whatever!
        """], type='human')]})

        graph.get_state = MagicMock(return_value=g)
        t.get_agent_response_graph({}, graph)

        found = t.get_status_message(BaseMessage(content=["""
        status_message: awaiting input for TestA2A
        """], type="human"))
        assert found.agent_route == "TestA2A"

        found = t.get_status_message(BaseMessage(content=["""
        other code...
        status_message: awaiting input for TestA2A
        """], type="human"))
        assert found.agent_route == "TestA2A"
