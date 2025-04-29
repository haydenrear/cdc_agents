import abc
import typing
from typing import Any, Dict, AsyncIterable
from typing import Literal

from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.messages import HumanMessage, BaseMessage
from langchain_ollama import ChatOllama, OllamaLLM
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import MessagesState, END
from langgraph.graph import StateGraph
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command
from pydantic import BaseModel

from cdc_agents.config.agent_config_props import AgentConfigProps

memory = MemorySaver()

class ResponseFormat(BaseModel):
    """Respond to the user in this format."""
    status: Literal["input_required", "completed", "error"] = "input_required"
    message: str

class BaseAgent(abc.ABC):

    @abc.abstractmethod
    def invoke(self, query, sessionId) -> str:
        pass

    @property
    @abc.abstractmethod
    def agent_name(self) -> str:
        pass


class A2AAgent(BaseAgent, abc.ABC):

    def __init__(self, model, tools, system_instruction):
        self.model = model
        self.tools = tools
        self.system_instruction = system_instruction
        if isinstance(model, str):
            if model.startswith('ollama_text://'):
                self.model = OllamaLLM(model = model.replace("ollama_text://", ""))
            if model.startswith('ollama_chat://'):
                self.model = ChatOllama(model = model.replace("ollama_chat://", ""))

        self.graph = create_react_agent(
            self.model, tools=self.tools, checkpointer=memory,
            prompt = self.system_instruction, response_format=ResponseFormat
        )
        self._agent_name = str(self.__class__)

    @property
    def agent_name(self) -> str:
        return self._agent_name

    @abc.abstractmethod
    async def stream(self, query, sessionId) -> AsyncIterable[Dict[str, Any]]:
        pass

    @abc.abstractmethod
    def get_agent_response(self, config):
        pass

    @staticmethod
    def get_agent_response_graph(config, graph):
        current_state = graph.get_state(config)
        structured_response = current_state.values.get('structured_response')
        if structured_response and isinstance(structured_response, ResponseFormat):
            if structured_response.status == "input_required":
                return {
                    "is_task_complete": False,
                    "require_user_input": True,
                    "content": structured_response.message
                }
            elif structured_response.status == "error":
                return {
                    "is_task_complete": False,
                    "require_user_input": True,
                    "content": structured_response.message
                }
            elif structured_response.status == "completed":
                return {
                    "is_task_complete": True,
                    "require_user_input": False,
                    "content": structured_response.message
                }

        return {
            "is_task_complete": False,
            "require_user_input": True,
            "content": "We are unable to process your request at the moment. Please try again.",
        }

    @staticmethod
    async def stream_agent_response_graph(query, sessionId, graph) -> AsyncIterable[Dict[str, Any]]:
        inputs = {"messages": [("user", query)]}
        config = {"configurable": {"thread_id": sessionId}}

        for item in graph.stream(inputs, config, stream_mode="values"):
            message = item["messages"][-1]
            if (
                    isinstance(message, AIMessage)
                    and message.tool_calls
                    and len(message.tool_calls) > 0
            ):
                yield {
                    "is_task_complete": False,
                    "require_user_input": False,
                    "content": "Looking up the exchange rates...",
                }
            elif isinstance(message, ToolMessage):
                yield {
                    "is_task_complete": False,
                    "require_user_input": False,
                    "content": "Processing the exchange rates..",
                }

class A2AOrchestratorAgent(A2AAgent, abc.ABC):
    pass

class A2AAgentOrchestrator(BaseAgent, abc.ABC):
    # def __init__(self, model, tools, system_instruction, agents: typing.List[A2AAgent]):
    pass

class DelegatingToolA2AAgentOrchestrator(A2AAgentOrchestrator, abc.ABC):
    """
    Generate a tool for each agent being orchestrated, then pass them into one model.
    """
    pass

class OrchestratedAgent:
    def __init__(self, agent: A2AAgent):
        self.agent = agent

class StateGraphA2AOrchestrator(A2AAgentOrchestrator, abc.ABC):
    """
    Facilitate multi-agent through lang-graph state graph. This means multiple models, each with smaller prompt from lower number of tools.
    """
    def __init__(self, agents: typing.Dict[str, OrchestratedAgent],
                 orchestrator_agent: A2AOrchestratorAgent,
                 props: AgentConfigProps):
        """
        :param agents: agents being orchestrated
        :param orchestrator_agent: agent doing orchestration
        """
        self.props = props
        self.orchestrator_agent = orchestrator_agent
        self.agents = agents

    @staticmethod
    def get_next_node(last_message: BaseMessage, goto: str):
        if "FINAL ANSWER" in last_message.content:
            # Any agent decided the work is done
            return END
        return goto

    def next_node(self, agent: BaseAgent, state: MessagesState, sessionId)-> Command[typing.Union[str, END]] :
        result = agent.invoke(state, sessionId)
        goto = self.get_next_node(result["messages"][-1], self.orchestrator_agent.agent_name)
        # wrap in a human message, as not all providers allow
        # AI message at the last position of the input messages list
        result["messages"][-1] = HumanMessage(
            content=result["messages"][-1].content, name=agent.agent_name
        )
        return Command(
            update={
                # share internal message history of chart agent with other agents
                "messages": result["messages"],
            },
            goto=goto,
        )

    def invoke(self, query, sessionId):
        state_graph = StateGraph(MessagesState)
        state_graph.add_node(self.orchestrator_agent.agent_name,
                             lambda state: self.next_node(self.orchestrator_agent, state, sessionId))

        for agent_name, agent in self.agents.items():
            state_graph.add_node(agent_name, lambda state: self.next_node(agent.agent, state, sessionId))

        state_graph.set_entry_point(self.orchestrator_agent.agent_name)
        graph = state_graph.compile()

        config = {
            "configurable": {"thread_id": sessionId},
            "recursion_limit": self.props.orchestrator_max_recurs}

        graph.invoke({"messages": [("user", query)]}, config)

        return A2AAgent.get_agent_response_graph(config, graph)