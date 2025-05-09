import typing

from cdc_agents.common.types import AgentCard, AgentSkill, AgentDescriptor, AgentType
from python_di.env.base_module_config_props import ConfigurationProperties
from python_di.properties.configuration_properties_decorator import configuration_properties
from pydantic.main import BaseModel

@configuration_properties(prefix_name='checkpoint')
class CheckpointConfigProps(ConfigurationProperties):
    uri: typing.Optional[str] = None