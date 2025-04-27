import typing

from cdc_agents.common.types import AgentCard
from python_di.env.base_module_config_props import ConfigurationProperties
from python_di.properties.configuration_properties_decorator import configuration_properties
from pydantic.main import BaseModel



class AgentCardItem(BaseModel):
    agent_card: typing.Optional[AgentCard] = None
    agent_clazz: typing.Optional[str] = None

@configuration_properties(prefix_name='agent_config')
class AgentConfigProps(ConfigurationProperties):
    agents: typing.List[AgentCardItem] = []
