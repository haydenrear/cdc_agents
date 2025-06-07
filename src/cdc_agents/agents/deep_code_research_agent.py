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
        OrchestratorAgent.__init__(self, agent_config, memory_saver, agents, model_provider)


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
        StateGraphOrchestrator.__init__(self,
                                        {a.agent_name: OrchestratedAgent(a) for a in agents if
                                            isinstance(a, A2AAgent)},
                                        orchestrator_agent, props, memory_saver, model_provider)
