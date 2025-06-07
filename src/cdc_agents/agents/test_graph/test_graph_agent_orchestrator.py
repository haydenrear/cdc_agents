import typing
from typing import Any, Dict, AsyncIterable

import injector
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agent.agent import A2AAgent, A2AReactAgent
from cdc_agents.agent.agent_orchestrator import (
    OrchestratorAgent,
    TestGraphOrchestrated,
    OrchestratedAgent, DeepResearchOrchestrated, StateGraphOrchestrator
)
from cdc_agents.agents.deep_code_research_agent import DeepCodeAgent
from cdc_agents.common.types import AgentGraphResponse
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
from cdc_agents.model_server.model_provider import ModelProvider
from python_di.configs.autowire import injectable
from python_di.configs.component import component

@component(bind_to=[A2AAgent, A2AReactAgent])
@injectable()
class TestGraphAgent(A2AReactAgent, OrchestratorAgent):
    """
    Orchestrator agent for test_graph integration that manages code generation,
    dependency building, and integration test execution. Acts as a sub-graph
    within DeepCodeOrchestrator.
    """

    @injector.inject
    def __init__(self,
                 agent_config: AgentConfigProps,
                 memory_saver: MemorySaver,
                 agents: typing.List[TestGraphOrchestrated],
                 model_provider: ModelProvider):
        OrchestratorAgent.__init__(self, agent_config, memory_saver, agents, model_provider)



@component(bind_to=[A2AAgent, A2AReactAgent, StateGraphOrchestrator, DeepResearchOrchestrated])
@injectable()
class TestGraphOrchestrator(StateGraphOrchestrator, DeepResearchOrchestrated):
    """
    State graph orchestrator for test_graph integration.
    Acts as a sub-graph within DeepCodeOrchestrator and manages the complete
    test_graph workflow including code generation, building, and test execution.
    """

    @injector.inject
    def __init__(self,
                 agents: typing.List[TestGraphOrchestrated],
                 orchestrator_agent: TestGraphAgent,
                 props: AgentConfigProps,
                 memory_saver: MemorySaver,
                 model_provider: ModelProvider):
        StateGraphOrchestrator.__init__(self,
                                        {a.agent_name: OrchestratedAgent(a) for a in agents if
                                         isinstance(a, A2AAgent)},
                                        orchestrator_agent, props, memory_saver, model_provider)
        self_card: AgentCardItem = props.agents[self.__class__.__name__]
        DeepResearchOrchestrated.__init__(self, self_card)


