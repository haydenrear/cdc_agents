import typing

from cdc_agents.common.types import AgentCard, AgentSkill, AgentDescriptor
from python_di.env.base_module_config_props import ConfigurationProperties
from python_di.properties.configuration_properties_decorator import configuration_properties
from pydantic.main import BaseModel

class AgentCardItem(BaseModel):
    agent_card: typing.Optional[AgentCard] = None
    agent_descriptor: typing.Optional[AgentDescriptor] = None
    agent_clazz: typing.Optional[str] = None

@configuration_properties(prefix_name='agent_config')
class AgentConfigProps(ConfigurationProperties):
    agents: typing.Dict[str, AgentCardItem] = {}
    orchestrator_max_recurs: typing.Optional[int] = 5000
    host: typing.Optional[str] = "0.0.0.0"
    port: typing.Optional[int] = 5000
