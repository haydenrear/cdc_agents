import importlib
import inspect
import typing

from cdc_agents.common.server import A2AServer
from cdc_agents.common.server.server import DynamicA2AServer
from cdc_agents.common.types import AgentCard, AgentCapabilities, AgentSkill, MissingAPIKeyError
from cdc_agents.common.utils.push_notification_auth import PushNotificationSenderAuth
from cdc_agents.agent.task_manager import AgentTaskManager
from cdc_agents.agent.agent import A2AAgent
import click
import os

from cdc_agents.config.agent_config_props import AgentConfigProps
from python_di.configs.autowire import injectable
from python_di.configs.component import component
from python_util.logger.logger import LoggerFacade
import injector


@component()
@injectable()
class AgentServerRunner:

    @injector.inject
    def __init__(self, agent_config_props: AgentConfigProps,
                 agents: typing.List[A2AAgent] = None):
        self.agent_config_props = agent_config_props
        self.agents: typing.Dict[str, A2AAgent] = {a.agent_name: a for a in agents}
        # self.start_dynamic_agent_cards() # TODO:
        self.run_server(agent_config_props.host, agent_config_props.port)

    def start_dynamic_agent_cards(self, host="0.0.0.0", port=5000):
        DynamicA2AServer(host, port, agents=self.agents).start()

    def run_server(self, host, port):
        """Starts the Currency Agent server."""
        for name, a in self.agent_config_props.agents.items():
            agent_card = a.agent_card

            if name not in self.agents.keys():
                try:
                    LoggerFacade.warn(f"Could not find agent {name} in injected. Looks like it's not being injected. Attempting to create it using reflection.")
                    agent: typing.Type[A2AAgent] = typing.cast(importlib.import_module(a.agent_clazz), typing.Type[A2AAgent])
                    self.agents[name] = agent(a.agent_descriptor.model, [importlib.import_module(t) for t in a.tools],
                                              a.agent_descriptor.system_instruction)
                except Exception as e:
                    LoggerFacade.error(f"Error resolving agent: {e}. Skipping the agent.")
                    continue

            notification_sender_auth = PushNotificationSenderAuth()
            notification_sender_auth.generate_jwk()
            server = A2AServer(
                agent_card=agent_card,
                task_manager=AgentTaskManager(agent=self.agents[name], notification_sender_auth=notification_sender_auth),
                host=host,
                port=port)

            server.app.add_route(
                "/.well-known/jwks.json", notification_sender_auth.handle_jwks_endpoint, methods=["GET"])

            LoggerFacade.info(f"Starting server on {host}:{port}")
            server.start()
