import dataclasses
import dataclasses
import importlib
import typing

import injector
import uvicorn
from langgraph.checkpoint.memory import MemorySaver
from starlette.applications import Starlette

from cdc_agents.agent.a2a import A2AAgent
from cdc_agents.agent.task_manager import AgentTaskManager
from cdc_agents.common.server import A2AServer
from cdc_agents.common.server.server import DynamicA2AServer, create_json_response, _add_all_managed_agents
from cdc_agents.common.types import DiscoverAgents, AgentCard
from cdc_agents.common.utils.push_notification_auth import PushNotificationSenderAuth
from cdc_agents.config.agent_config_props import AgentConfigProps
from cdc_agents.config.runner_props import RunnerConfigProps
from cdc_agents.model_server.model_provider import ModelProvider
from python_di.configs.autowire import injectable
from python_di.configs.component import component
from python_di.inject.profile_composite_injector.composite_injector import profile_scope
from python_util.logger.logger import LoggerFacade


@dataclasses.dataclass(init=True)
class DiscoverableAgent:
    agent: A2AAgent
    agent_card: AgentCard



@component(profile=['main_profile', 'test'], scope=profile_scope)
@injectable()
class AgentServerRunner:

    @injector.inject
    def __init__(self,
                 agent_config_props: AgentConfigProps,
                 memory: MemorySaver,
                 runner_config_props: RunnerConfigProps,
                 model_server_provider: ModelProvider,
                 starlette: Starlette,
                 agents: typing.List[A2AAgent] = None):
        self.model_server_provider = model_server_provider
        self.memory = memory
        self.agent_config_props = agent_config_props
        self.agents: typing.Dict[str, DiscoverableAgent] = {
            next_agent.agent_name: DiscoverableAgent(next_agent, self._to_discoverable_agent(next_agent))
            for next_agent in agents}
        _add_all_managed_agents(self.agent_config_props)
        # self.start_dynamic_agent_cards() # TODO:
        self.starlette = self.load_server(agent_config_props.host, agent_config_props.port, starlette)

        if runner_config_props.is_a2a():
            self.run_server()

    # def start_dynamic_agent_cards(self):
    #     DynamicA2AServer(self.agent_config_props, agents=self.agents).start() # TODO:

    def run_server(self):
        """Starts the Currency Agent server."""
        LoggerFacade.info(f"Starting server on {self.agent_config_props.host}:{self.agent_config_props.port}")
        uvicorn.run(self.starlette, host=self.agent_config_props.host,
                    port=self.agent_config_props.port)

    def load_server(self, host, port, starlette: Starlette):
        notification_sender_auth = PushNotificationSenderAuth()
        notification_sender_auth.generate_jwk()
        starlette.add_route(
            "/.well-known/jwks.json", notification_sender_auth.handle_jwks_endpoint, methods=["GET"])
        for name, a in self.agent_config_props.agents.items():
            agent_card = a.agent_card

            if name not in self.agents.keys():
                raise ValueError(f"Could not find agent: {name}.")

            task_manager = AgentTaskManager(agent=self.agents[name].agent, notification_sender_auth=notification_sender_auth)
            self.agents[name].agent.set_task_manager(task_manager)
            self.agents[name].agent.system_instruction = a.agent_descriptor.system_instruction
            A2AServer(
                agent_card=agent_card,
                task_manager=task_manager,
                host=host,
                port=port,
                starlette=starlette,
                endpoint=agent_card.path)

        # Be able for server/client to discover all available A2A agents for a task
        starlette.add_route('/discover_agents',
                            lambda req: create_json_response(DiscoverAgents(agent_cards=self._parse_discoverable())),
                            methods=['GET'])

        return starlette

    def _parse_discoverable(self):
        return [discoverable_agent.agent_card for discoverable_agent in self.agents.values()]

    def _to_discoverable_agent(self, a):
        if a.agent_name in self.agent_config_props.agents.keys():
            return self.agent_config_props.agents[a.agent_name].agent_card
        LoggerFacade.error(f"Could not find agent card in agent config props for agent {a.agent_name}."
                           f"Will not be discoverable.")
