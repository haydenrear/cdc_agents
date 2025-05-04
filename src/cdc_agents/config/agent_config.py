from langchain.agents.output_parsers import JSONAgentOutputParser, ReActSingleInputOutputParser
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agent.agent_server import AgentServerRunner
from cdc_agents.agents.cdc_server_agent import CdcCodeSearchAgent
from cdc_agents.agents.deep_code_research_agent import DeepCodeOrchestrator, DeepCodeAgent
from cdc_agents.config.agent_config_props import AgentConfigProps
from cdc_agents.config.model_server_config_props import ModelServerConfigProps
from cdc_agents.model_server.language_model_input_parser import LanguageModelOutputParser
from cdc_agents.model_server.model_server_model import ModelServerModel
from python_di.configs.bean import bean
from python_di.configs.component_scan import component_scan
from python_di.configs.di_configuration import configuration
from python_di.configs.enable_configuration_properties import enable_configuration_properties


@configuration()
@enable_configuration_properties(config_props=[AgentConfigProps, ModelServerConfigProps])
@component_scan(base_classes=[ModelServerModel, AgentServerRunner, CdcCodeSearchAgent, DeepCodeAgent, DeepCodeOrchestrator])
class AgentConfig:

    @bean()
    def memory(self) -> MemorySaver:
        return MemorySaver()

    @bean()
    def json_parser(self) -> JSONAgentOutputParser:
        return JSONAgentOutputParser()

    @bean()
    def react_io_parser(self) -> ReActSingleInputOutputParser:
        return ReActSingleInputOutputParser()
