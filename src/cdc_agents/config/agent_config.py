from langchain.agents.output_parsers import JSONAgentOutputParser, ReActSingleInputOutputParser
from langgraph.checkpoint.memory import MemorySaver

from cdc_agents.agent.agent_server import AgentServerRunner
from cdc_agents.agent.task_manager import AgentTaskManager
from cdc_agents.agents.cdc_server_agent import CdcCodeSearchAgent
from cdc_agents.agents.deep_code_research_agent import DeepCodeOrchestrator, DeepCodeAgent
from cdc_agents.common.server import TaskManager
from cdc_agents.config.agent_config_props import AgentConfigProps
from cdc_agents.config.checkpoint_config_props import CheckpointConfigProps
from cdc_agents.config.model_server_config_props import ModelServerConfigProps
from cdc_agents.model_server.model_provider import ModelProvider
from cdc_agents.model_server.model_server_model import ModelServerModel
from python_di.configs.bean import bean
from python_di.configs.component_scan import component_scan
from python_di.configs.di_configuration import configuration
from python_di.configs.enable_configuration_properties import enable_configuration_properties
from python_util.logger.logger import LoggerFacade


@configuration()
@enable_configuration_properties(config_props=[AgentConfigProps, ModelServerConfigProps, CheckpointConfigProps])
@component_scan(base_classes=[ModelServerModel, AgentServerRunner, CdcCodeSearchAgent, DeepCodeAgent,
                              DeepCodeOrchestrator, ModelProvider])
class AgentConfig:

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
