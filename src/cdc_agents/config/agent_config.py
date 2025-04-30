from cdc_agents.agent.agent_server import AgentServerRunner
from cdc_agents.agents.commit_diff_context_server_agent import CdcEmbeddingAgent
from cdc_agents.agents.deep_code_research_agent import DeepCodeOrchestrator
from cdc_agents.config.agent_config_props import AgentConfigProps
from python_di.configs.component_scan import component_scan
from python_di.configs.di_configuration import configuration
from python_di.configs.enable_configuration_properties import enable_configuration_properties


@configuration()
@enable_configuration_properties(config_props=[AgentConfigProps])
@component_scan(base_classes=[AgentServerRunner, CdcEmbeddingAgent, DeepCodeOrchestrator])
class AgentConfig:
    pass

