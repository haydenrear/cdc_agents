import typing

import injector
from langchain_core.prompt_values import PromptValue

from cdc_agents.agent.agent import A2AReactAgent

from cdc_agents.agent.a2a import A2AAgent

from cdc_agents.config.agent_config_props import AgentConfigProps
from langchain_core.prompts import PromptTemplate

from python_di.configs.autowire import injectable

from python_di.configs.component import component


@component()
@injectable()
class PromptProvider:

    @injector.inject
    def __init__(self, agent_config_props: AgentConfigProps):
        self.agent_config_props = agent_config_props


    # def parse_prompt_from_agent(self, a2a_agent: A2AAgent) -> typing.Optional[typing.Callable[[typing.Any], PromptValue] | str]:
    #     agent_name = a2a_agent.agent_name
    #     if agent_name not in self.agent_config_props.agents.keys():
    #         return None
    #
    #     if isinstance(a2a_agent, A2AReactAgent):
    #         instruction_template = self.agent_config_props.agents[agent_name].agent_descriptor.system_instruction
    #         return self.produce_prompt_template(instruction_template, tools=a2a_agent.tools)
    #
    #     elif isinstance(a2a_agent, A2AAgent):
    #         return PromptValue()
    #
    #
    # def produce_prompt_template(self, instruction, **kwargs):
    #     pt = PromptTemplate(template=instruction, input_variables=[k for k in kwargs.keys()])
    #     return pt.format(**kwargs)



