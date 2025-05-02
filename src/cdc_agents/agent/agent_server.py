import dataclasses
import dataclasses
import importlib
import typing

import injector
import uvicorn
from starlette.applications import Starlette

from cdc_agents.agent.agent import A2AAgent
from cdc_agents.agent.task_manager import AgentTaskManager
from cdc_agents.common.server import A2AServer
from cdc_agents.common.server.server import DynamicA2AServer, create_json_response, _add_all_managed_agents
from cdc_agents.common.types import DiscoverAgents, AgentCard
from cdc_agents.common.utils.push_notification_auth import PushNotificationSenderAuth
from cdc_agents.config.agent_config_props import AgentConfigProps
from python_di.configs.autowire import injectable
from python_di.configs.component import component
from python_util.logger.logger import LoggerFacade


@dataclasses.dataclass(init=True)
class DiscoverableAgent:
    agent: A2AAgent
    agent_card: AgentCard



@component()
@injectable()
class AgentServerRunner:

    @injector.inject
    def __init__(self,
                 agent_config_props: AgentConfigProps,
                 agents: typing.List[A2AAgent] = None):
        self.agent_config_props = agent_config_props
        self.agents: typing.Dict[str, DiscoverableAgent] = {
            next_agent.agent_name: DiscoverableAgent(next_agent, self._to_discoverable_agent(next_agent))
            for next_agent in agents}
        _add_all_managed_agents(self.agent_config_props)
        # self.start_dynamic_agent_cards() # TODO:
        self.starlette = self.load_server(agent_config_props.host, agent_config_props.port)
        if agent_config_props.initialize_server:
            self.run_server()

    def _to_discoverable_agent(self, a):
        if a.agent_name in self.agent_config_props.agents.keys():
            return self.agent_config_props.agents[a.agent_name].agent_card
        LoggerFacade.error(f"Could not find agent card in agent config props for agent {a.agent_name}."
                           f"Will not be discoverable.")

    # def start_dynamic_agent_cards(self):
    #     DynamicA2AServer(self.agent_config_props, agents=self.agents).start() # TODO:

    def run_server(self):
        """Starts the Currency Agent server."""
        if self.starlette is None:
            self.starlette = self.load_server(self.agent_config_props.host, self.agent_config_props.port)

        LoggerFacade.info(f"Starting server on {self.agent_config_props.host}:{self.agent_config_props.port}")
        uvicorn.run(self.starlette, host=self.agent_config_props.host,
                    port=self.agent_config_props.port)

    def load_server(self, host, port):
        starlette = Starlette()
        notification_sender_auth = PushNotificationSenderAuth()
        notification_sender_auth.generate_jwk()
        starlette.add_route(
            "/.well-known/jwks.json", notification_sender_auth.handle_jwks_endpoint, methods=["GET"])
        for name, a in self.agent_config_props.agents.items():
            agent_card = a.agent_card

            if name not in self.agents.keys():
                try:
                    LoggerFacade.warn(
                        f"Could not find agent {name} in injected. Looks like it's not being injected. Attempting to create it using reflection.")
                    agent: typing.Type[A2AAgent] = typing.cast(importlib.import_module(a.agent_clazz),
                                                               typing.Type[A2AAgent])
                    self.agents[name] = DiscoverableAgent(
                        agent(a.agent_descriptor.model, [importlib.import_module(t) for t in a.tools],
                              a.agent_descriptor.system_instruction, []),
                        agent_card)
                    self.agents[name].agent.add_mcp_tools(a.mcp_tools)
                except Exception as e:
                    LoggerFacade.error(f"Error resolving agent: {e}. Skipping the agent.")
                    continue

            self.agents[name].agent.add_mcp_tools(a.mcp_tools)

            A2AServer(
                agent_card=agent_card,
                task_manager=AgentTaskManager(agent=self.agents[name].agent,
                                              notification_sender_auth=notification_sender_auth),
                host=host,
                port=port,
                starlette=starlette)

        starlette.add_route('/discover_agents',
                            lambda req: create_json_response(DiscoverAgents(agent_cards=self._parse_discoverable())),
                            methods=['GET'])

        return starlette

    def _parse_discoverable(self):
        return [discoverable_agent.agent_card for discoverable_agent in self.agents.values()]

