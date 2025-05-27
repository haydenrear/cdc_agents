import typing

import pydantic

from cdc_agents.common.types import AgentCard, AgentSkill, AgentDescriptor, AgentType
from python_di.env.base_module_config_props import ConfigurationProperties
from python_di.properties.configuration_properties_decorator import configuration_properties
from pydantic.main import BaseModel

class McpToolSecret(pydantic.BaseModel):
    tool_name: str
    secret_name: str
    secret_value: str

@configuration_properties(prefix_name='secrets')
class SecretConfigProps(ConfigurationProperties):
    model_secrets: typing.Dict[str, str] = None
    mcp_tool_secrets: typing.Optional[typing.List[McpToolSecret]] = None