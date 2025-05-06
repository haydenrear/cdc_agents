import abc

from langchain.agents import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agent.agent import A2AAgent, StateGraphOrchestrator, OrchestratedAgent, OrchestratorAgent, \
    BaseAgent, NextAgentResponse, A2AReactAgent
import dataclasses
import enum
import typing
from typing import Any, Dict, AsyncIterable

import httpx
import injector
import torch
from langchain_core.messages import AIMessage, ToolMessage, BaseMessage
from langchain_core.tools import tool

from cdc_agents.agent.agent import A2AAgent, ResponseFormat
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem, AgentMcpTool
from cdc_agents.model_server.model_provider import ModelProvider
from python_di.configs.autowire import injectable
from python_di.configs.component import component
from python_di.inject.profile_composite_injector.composite_injector import profile_scope
from python_di.inject.profile_composite_injector.scopes.profile_scope import ProfileScope


class DeepResearchOrchestrated(BaseAgent, abc.ABC):
    """
    Marker interface for DI, marking the agents being orchestrated.
    """
    @property
    @abc.abstractmethod
    def orchestrator_prompt(self):
        """
        :return: what information to provide the orchestrator in a prompt.
        """
        pass


@tool
def call_a_friend():
    """Call a human in the loop to validate we're moving the correct direction.

    Args:

    Returns:

    """
    raise NotImplementedError

@component(bind_to=[A2AAgent, A2AReactAgent])
@injectable()
class DeepCodeAgent(OrchestratorAgent):

    @injector.inject
    def __init__(self, agent_config: AgentConfigProps, memory_saver: MemorySaver,
                 agents: typing.List[DeepResearchOrchestrated], model_provider: ModelProvider):
        orchestrator_prompts = {a.agent_name: a.orchestrator_prompt for a in agents}
        self.SYSTEM_INSTRUCTION = f"""
        {self.orchestration_prompt()}
        {self._parse_agents_lines(orchestrator_prompts)}
        {self.orchestration_messages()}
        """
        A2AReactAgent.__init__(self, agent_config, [call_a_friend], self.SYSTEM_INSTRUCTION, memory_saver,
                               model_provider)

    def _parse_agents_lines(self, orchestrator_prompts):
        return '\n\n'.join(self._parse_agents(orchestrator_prompts))

    def _parse_agents(self, orchestrator_prompts):
        return [f'''
        agent name: 
            {k} 
        agent info: 
            {v}
        ''' for k, v in orchestrator_prompts.items()]

    def orchestration_messages(self):
        # TODO:
        return '''
        Your primary goal is to interpret the responses from the agents into requests for other agents, including adding any additional 
        context to them to help them along with the overall goal of implementing software using contextual information. Make sure that
        when you interpret the previous agent's response, if you decide to delegate to another agent and add context make sure that
        the context you add relates to their domain. In order to delegate to the agent, please follow the format
        
        NEXT AGENT: [name of the agent, as per the agents provided previously with agent_name]
        ADDITIONAL CONTEXT: [additional relevant contextual information, for example summarizing previous information and what you'd like that agent to do] 
        
        If the agent provides a message with
        
        FINAL ANSWER:  
        [final answer provided]
               
        Please evaluate the answer, and determine whether or not it meets the requirements or additional action is needed. For example, 
        if the CdcCodeSearchAgent provides context, and then you call the CdcCodegenAgent, which provides a final answer,
        then, in order to validate the answer, you may apply the code changes and validate them using the CodeRunnerAgent,
        or generate some tests after applying the changes and run those with the CodeRunnerAgent. In some cases, you may
        need to validate business requirements, or demonstrate the code changes, in which case you may then call the 
        HumanDelegateAgent to validate the changes, or business requirements. 
        
        In any case, please ensure that the software implementation is thorough and complete, and validated, and if you 
        have any questions, please reach out using the HumanDelegateAgent. 
        '''

    def orchestration_prompt(self):
        return '''
        You are the orchestrator agent for code generation. Your job is to orchestrate a group of agents to implement tickets for software projects. 
        After every agent returns, you will then evaluate it's response and delegate to another agent or produce a final answer.
        
        Here are a list of the agents that you are in charge of orchestrating:
        
        '''

    def invoke(self, query, sessionId) -> str:
        config = {"configurable": {"thread_id": sessionId}}
        if isinstance(query, dict) and "messages" in query.keys():
            self.graph.invoke(query, config)
        else:
            self.graph.invoke({"messages": [{"content": query}]}, config)

        return self.get_agent_response(config)

    async def stream(self, query, sessionId, graph=None) -> AsyncIterable[Dict[str, Any]]:
        return self.stream_agent_response_graph(query, sessionId, self.graph)

    def get_agent_response(self, config, graph=None):
        return self.get_agent_response_graph(config, self.graph)

    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]


@component(bind_to=[A2AAgent, A2AReactAgent])
@injectable()
class DeepCodeOrchestrator(StateGraphOrchestrator):

    @injector.inject
    def __init__(self,
                 agents: typing.List[DeepResearchOrchestrated],
                 orchestrator_agent: DeepCodeAgent,
                 props: AgentConfigProps,
                 memory_saver: MemorySaver):
        StateGraphOrchestrator.__init__(self,
                                        {a.agent_name: OrchestratedAgent(a) for a in agents if
                                            isinstance(a, A2AAgent)},
                                        orchestrator_agent, props, memory_saver)

    @property
    def agent_name(self) -> str:
        return f'Graph orchestrator agent; {self.orchestrator_agent.agent_name}'

    def parse_orchestration_response(self, last_message: BaseMessage) -> typing.Union[BaseMessage, NextAgentResponse]:
        found = list(filter(lambda x: 'NEXT AGENT:' in x, last_message.content if isinstance(last_message.content, list) else [last_message.content]))
        if len(found) == 0:
            return last_message
        else:
            split = found[0].split('NEXT AGENT:')
            if len(split) <= 1:
                return last_message
            f = split[1].strip()
            return NextAgentResponse(f)

    def orchestration_prompt(self):
        pass


