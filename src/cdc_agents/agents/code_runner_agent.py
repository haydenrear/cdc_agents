from typing import Any, Dict, AsyncIterable

import injector

from cdc_agents.agent.agent import A2AAgent, A2AReactAgent
from cdc_agents.agents.deep_code_research_agent import DeepResearchOrchestrated
from cdc_agents.config.agent_config_props import AgentConfigProps, AgentCardItem
from python_di.configs.autowire import injectable
from python_di.configs.component import component
from langchain_core.tools import tool

@tool
def perform_docker_operation():
    """
    """
    pass

@tool
def perform_local_file_operation():
    """
    """
    pass

@tool
def perform_git_operation():
    """
    """
    pass

@tool
def perform_browser_operation():
    """
    """
    pass

# @component(bind_to=[DeepResearchOrchestrated, A2AReactAgent])
# @injectable()
class CodeRunnerAgent(DeepResearchOrchestrated, A2AReactAgent):

    SYSTEM_INSTRUCTION = (
        """
        You are a specialized assistant for code context information.
        # Your sole purpose is to use the 'get_exchange_rate' tool to answer questions about currency exchange rates.
        # If the user asks about anything other than currency conversion or exchange rates,
        # politely state that you cannot help with that topic and can only assist with currency-related queries. 
        # Do not attempt to answer unrelated questions or use tools for other purposes.
        # Set response status to input_required if the user needs to provide more information.
        # Set response status to error if there is an error while processing the request.
        # Set response status to completed if the request is complete.
        """
    )

    # @injector.inject
    def __init__(self, agent_config: AgentConfigProps):
        cdc_codegen_agent = str(CodeRunnerAgent)
        A2AReactAgent.__init__(self,
                          agent_config.agents[cdc_codegen_agent].agent_descriptor.model if cdc_codegen_agent in agent_config.agents.keys() else None,
                          [perform_git_operation, perform_browser_operation, perform_docker_operation, perform_local_file_operation],
                          self.SYSTEM_INSTRUCTION)
        self.agent_config: AgentCardItem = agent_config.agents[cdc_codegen_agent] \
            if cdc_codegen_agent in agent_config.agents.keys() else None

    @property
    def orchestrator_prompt(self):
        return """
        An agent that facilitates the running of the code after making code changes, to validate code changes with respect
        for particular tickets, bug changes, or any other unit of work.
        """

    def invoke(self, query, sessionId) -> str:
        config = {"configurable": {"thread_id": sessionId}}
        self.graph.invoke({"messages": [("user", query)]}, config)
        return self.get_agent_response(config)

    async def stream(self, query, sessionId, graph=None) -> AsyncIterable[Dict[str, Any]]:
        return self.stream_agent_response_graph(query, sessionId, self.graph)

    def get_agent_response(self, config, graph=None):
        return self.get_agent_response_graph(config, self.graph)


    SUPPORTED_CONTENT_TYPES = ["text", "text/plain"]

