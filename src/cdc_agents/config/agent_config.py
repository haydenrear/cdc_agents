import unittest.mock

from langchain.agents.output_parsers import JSONAgentOutputParser, ReActSingleInputOutputParser
from langgraph.checkpoint.memory import MemorySaver
from starlette.applications import Starlette

from cdc_agents.agent.agent_server import AgentServerRunner
from cdc_agents.agents.cdc_server_agent import CdcCodeSearchAgent
from cdc_agents.agents.deep_code_research_agent import DeepCodeOrchestrator, DeepCodeAgent
from cdc_agents.agents.human_delegate_agent import HumanDelegateAgent
from cdc_agents.agents.library_enumeration_agent import LibraryEnumerationAgent
from cdc_agents.agents.summarizer_agent import SummarizerAgent
from cdc_agents.config.agent_config_props import AgentConfigProps
from cdc_agents.config.cdc_server_config_props import CdcServerConfigProps
from cdc_agents.config.checkpoint_config_props import CheckpointConfigProps
from cdc_agents.config.human_delegate_config_props import HumanDelegateConfigProps
from cdc_agents.config.model_server_config_props import ModelServerConfigProps
from cdc_agents.config.runner_props import RunnerConfigProps
from cdc_agents.model_server.model_provider import ModelProvider
from cdc_agents.model_server.model_server_model import ModelServerModel
from python_di.configs.bean import bean
from python_di.configs.component_scan import component_scan
from python_di.configs.di_configuration import configuration
from python_di.configs.enable_configuration_properties import enable_configuration_properties
from python_di.inject.profile_composite_injector.composite_injector import profile_scope
from python_util.logger.logger import LoggerFacade


@configuration()
@enable_configuration_properties(config_props=[AgentConfigProps, ModelServerConfigProps, CheckpointConfigProps, CdcServerConfigProps,
                                               HumanDelegateConfigProps, RunnerConfigProps])
@component_scan(base_classes=[ModelServerModel, CdcCodeSearchAgent, DeepCodeAgent,
                              DeepCodeOrchestrator, ModelProvider, AgentServerRunner, HumanDelegateAgent,
                              SummarizerAgent, LibraryEnumerationAgent])
class AgentConfig:

    @bean(profile='test', scope=profile_scope, bindings=[Starlette])
    def starlette_test(self) -> Starlette:
        return unittest.mock.MagicMock(return_value='hello!')

    @bean(profile='main_profile', scope=profile_scope, bindings=[Starlette])
    def starlette_main(self) -> Starlette:
        return Starlette()

    @bean()
    def memory(self, checkpoint_config_props: CheckpointConfigProps) -> MemorySaver:
        """
        Decouple the memory here into a database for stateless services...
        :return:
        """
        assert checkpoint_config_props
        try:
            assert checkpoint_config_props.uri
            from langgraph.checkpoint.postgres import PostgresSaver
            LoggerFacade.info(f"Loading Postgres save from URI {checkpoint_config_props.uri}")
            return PostgresSaver.from_conn_string(checkpoint_config_props.uri)
        except:
            LoggerFacade.info("Loading MemorySaver checkpointer.")
            return MemorySaver()

    @bean()
    def json_parser(self) -> JSONAgentOutputParser:
        return JSONAgentOutputParser()

    @bean()
    def react_io_parser(self) -> ReActSingleInputOutputParser:
        return ReActSingleInputOutputParser()
