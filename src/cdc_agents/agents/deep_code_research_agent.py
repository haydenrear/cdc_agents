from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agent.agent import A2AReactAgent
from cdc_agents.agent.agent_orchestrator import OrchestratorAgent, OrchestratedAgent, \
    StateGraphOrchestrator, DeepResearchOrchestrated
import typing
from typing import Any, Dict, AsyncIterable

import injector
from langchain_core.tools import tool

from cdc_agents.agent.agent import A2AAgent
from cdc_agents.common.types import AgentGraphResponse
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
from cdc_agents.model_server.model_provider import ModelProvider
from python_di.configs.autowire import injectable
from python_di.configs.component import component


@tool
def rate_codegen_trajectory():
    """Suffering from collapse? Each time, we check to see whether we should revert to previous state.
    :return:
    """
    pass

@tool
def refactor_advisory():
    """
    :return:
    """
    pass

@tool
def dead_code_advisory():
    """
    :return:
    """
    pass

@tool
def review_test_validity():
    """Are we actually testing something?
    :return:
    """
    pass

@tool
def review_business_requirement():
    """Did we resolve anything?
    :return:
    """
    pass

@tool
def is_agent_response_refinable():
    """Should we ask the agent to try again?
    :return:
    """
    pass

@component(bind_to=[A2AAgent, A2AReactAgent])
@injectable()
class DeepCodeAgent(A2AReactAgent, OrchestratorAgent):
    """
    Gets called every time after another sub-agent is called. In between, after it advises which agent to call next,
    or to produce the final answer, it calls various tools to check the agents work.
    """

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver,
                 agents: typing.List[DeepResearchOrchestrated], model_provider: ModelProvider):
        orchestrated_agents: dict[str, DeepResearchOrchestrated] = {a.agent_name: a for a in agents}

        self_card: AgentCardItem = agent_config.agents.get(self.__class__.__name__)

        OrchestratorAgent.__init__(self, self_card)

        self.SYSTEM_INSTRUCTION = self.create_orchestrator_system_prompt(orchestrated_agents)

        A2AReactAgent.__init__(self, agent_config, [], self.SYSTEM_INSTRUCTION, memory_saver,
                               model_provider)

    def invoke(self, query, sessionId) -> AgentGraphResponse:
        config = self._parse_query_config(sessionId)
        if isinstance(query, dict) and "messages" in query.keys():
            self.graph.invoke(query, config)
        else:
            self.graph.invoke({"messages": [{"content": query}]}, config)

        return self.get_agent_response(config)

    def stream(self, query, sessionId, graph=None) -> AsyncIterable[Dict[str, Any]]:
        return self.stream_agent_response_graph(query, sessionId, self.graph)

    def get_agent_response(self, config, graph=None):
        return self.get_agent_response_graph(config, self.graph)



@component(bind_to=[A2AAgent, A2AReactAgent, StateGraphOrchestrator])
@injectable()
class DeepCodeOrchestrator(StateGraphOrchestrator):

    @injector.inject
    def __init__(self,
                 agents: typing.List[DeepResearchOrchestrated],
                 orchestrator_agent: DeepCodeAgent,
                 props: AgentConfigProps,
                 memory_saver: MemorySaver,
                 model_provider: ModelProvider):
        # Include TestGraphOrchestrator if provided
        all_agents = list(agents)
        StateGraphOrchestrator.__init__(self,
                                        {a.agent_name: OrchestratedAgent(a) for a in all_agents if
                                            isinstance(a, A2AAgent)},
                                        orchestrator_agent, props, memory_saver, model_provider)

    def parse_orchestration_response(self, last_message: AgentGraphResponse) -> AgentGraphResponse:
        return last_message

