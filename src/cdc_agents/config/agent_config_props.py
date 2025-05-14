import typing

from cdc_agents.common.types import AgentCard, AgentSkill, AgentDescriptor, AgentType
from python_di.env.base_module_config_props import ConfigurationProperties
from python_di.properties.configuration_properties_decorator import configuration_properties
from pydantic.main import BaseModel

class AgentMcpTool(BaseModel):
    tool_options: typing.Any
    name: typing.Optional[str] = None
    tool_prompt: typing.Optional[str] = None
    stop_tool: typing.Optional[str] = None
    # TODO: should be able to keep it running and call exec instead
    # exec_tool_options: typing.Optional[typing.Any] = None

class AgentCardItem(BaseModel):
    agent_card: typing.Optional[AgentCard] = None
    agent_descriptor: typing.Optional[AgentDescriptor] = None
    agent_clazz: typing.Optional[str] = None
    mcp_tools: typing.Dict[str, AgentMcpTool] = None
    agent_type: AgentType = AgentType.LangChainReact

@configuration_properties(prefix_name='agent_config')
class AgentConfigProps(ConfigurationProperties):
    agents: typing.Dict[str, AgentCardItem] = {}
    let_orchestrated_agents_terminate: bool = True
    orchestrator_max_recurs: typing.Optional[int] = 5000
    host: typing.Optional[str] = "0.0.0.0"
    port: typing.Optional[int] = 50000
    max_tokens_message_state: int = 20000