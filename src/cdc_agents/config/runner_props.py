import enum
import typing
from pydantic import model_validator, ConfigDict, field_serializer
from python_util.logger.logger import LoggerFacade

from cdc_agents.common.types import AgentCard, AgentSkill, AgentDescriptor, AgentType
from python_di.env.base_module_config_props import ConfigurationProperties
from python_di.properties.configuration_properties_decorator import configuration_properties
from pydantic.main import BaseModel

class RunnerOption(enum.Enum):
    A2A = 'A2A'
    MCP = 'MCP'
    SKIP = 'SKIP'

@configuration_properties(prefix_name='runner')
class RunnerConfigProps(ConfigurationProperties):
    runner_option: RunnerOption = RunnerOption.SKIP


    def is_mcp(self):
        return self.runner_option == RunnerOption.MCP

    def is_a2a(self):
        LoggerFacade.info(f"Testing if {self.runner_option} is skip")
        return self.runner_option == RunnerOption.A2A
