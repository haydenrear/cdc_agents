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
from cdc_agents.config.secret_config_props import SecretConfigProps
from cdc_agents.config.tool_call_properties import ToolCallProps
from cdc_agents.model_server.model_provider import ModelProvider
from cdc_agents.model_server.model_server_model import ModelServerModel
from cdc_agents.tools.tool_call_decorator import ToolCallDecorator
from python_di.configs.bean import bean
from python_di.configs.component_scan import component_scan
from python_di.configs.di_configuration import configuration
from python_di.configs.enable_configuration_properties import enable_configuration_properties
from python_di.inject.profile_composite_injector.composite_injector import profile_scope
from python_util.logger.logger import LoggerFacade


@configuration()
@enable_configuration_properties(config_props=[AgentConfigProps, ModelServerConfigProps, CheckpointConfigProps, CdcServerConfigProps,
                                               HumanDelegateConfigProps, RunnerConfigProps, ToolCallProps, SecretConfigProps])
@component_scan(base_classes=[ModelServerModel, CdcCodeSearchAgent, DeepCodeAgent,
                              DeepCodeOrchestrator, ModelProvider, AgentServerRunner, HumanDelegateAgent,
                              SummarizerAgent, LibraryEnumerationAgent, ToolCallDecorator])
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
            from psycopg import Capabilities, Connection, Cursor, Pipeline
            from psycopg.rows import DictRow, dict_row
            try:
                LoggerFacade.to_ctx(f"Loading Postgres save from URI {checkpoint_config_props.uri}")
                conn = Connection.connect(checkpoint_config_props.uri, autocommit=True, prepare_threshold=0, row_factory=dict_row)
                # Create publications for CDC
                self._create_publications(conn)
                
                p = PostgresSaver(conn)
                p.setup()
                return p
            except Exception as e:
                LoggerFacade.to_ctx(f"Failed to load postgres: {e}. Loading from memory.")
                return MemorySaver()
        except Exception as f:
            LoggerFacade.to_ctx(f"No URI configured or error: {f}. Loading from memory.")
            return MemorySaver()

    def _create_publications(self, conn: 'Connection') -> None:
        """
        Create PostgreSQL publications for Change Data Capture.
        """
        try:
            with conn.cursor() as cur:
                # Check if logical replication is enabled
                cur.execute("SHOW wal_level;")
                wal_level = cur.fetchone()['wal_level']
                if wal_level != 'logical':
                    LoggerFacade.to_ctx("WARNING: PostgreSQL wal_level is not set to 'logical'. CDC will not work!")
                    return
                
                # Create publication if it doesn't exist
                cur.execute("SELECT EXISTS (SELECT 1 FROM pg_publication WHERE pubname = 'langgraph_publication');")
                if not cur.fetchone()['exists']:
                    LoggerFacade.to_ctx("Creating publication for LangGraph CDC...")
                    cur.execute("CREATE PUBLICATION langgraph_publication FOR TABLE checkpoints, checkpoint_blobs, checkpoint_writes;")
                    LoggerFacade.to_ctx("Publication created successfully!")
        except Exception as e:
            LoggerFacade.to_ctx(f"Failed to create publications: {e}")

    @bean()
    def json_parser(self) -> JSONAgentOutputParser:
        return JSONAgentOutputParser()

    @bean()
    def react_io_parser(self) -> ReActSingleInputOutputParser:
        return ReActSingleInputOutputParser()
