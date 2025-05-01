import asyncio
import importlib
import inspect
import typing

from starlette.applications import Starlette

from cdc_agents.common.server import A2AServer
from cdc_agents.common.server.server import DynamicA2AServer
from cdc_agents.common.types import AgentCard, AgentCapabilities, AgentSkill, MissingAPIKeyError
from cdc_agents.common.utils.push_notification_auth import PushNotificationSenderAuth
from cdc_agents.agent.task_manager import AgentTaskManager
from cdc_agents.agent.agent import A2AAgent
import click
import os

from cdc_agents.config.agent_config_props import AgentConfigProps
from python_di.configs.autowire import injectable, post_construct
from python_di.configs.component import component
from python_di.inject.profile_composite_injector.composite_injector import profile_scope
from python_util.logger.logger import LoggerFacade
import injector
import uvicorn

@component()
@injectable()
class AgentServerRunner:

    @injector.inject
    def __init__(self,
                 agent_config_props: AgentConfigProps,
                 agents: typing.List[A2AAgent] = None):
        self.agent_config_props = agent_config_props
        self.agents: typing.Dict[str, A2AAgent] = {a.agent_name: a for a in agents}
        # self.start_dynamic_agent_cards() # TODO:
        self.starlette = self.load_server(agent_config_props.host, agent_config_props.port)
        if agent_config_props.initialize_server:
            self.run_server()

    def start_dynamic_agent_cards(self):
        DynamicA2AServer(self.agent_config_props.host, self.agent_config_props.port, agents=self.agents).start()

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
                    self.agents[name] = agent(a.agent_descriptor.model, [importlib.import_module(t) for t in a.tools],
                                              a.agent_descriptor.system_instruction, [])
                    self.agents[name].add_mcp_tools(a.mcp_tools)
                except Exception as e:
                    LoggerFacade.error(f"Error resolving agent: {e}. Skipping the agent.")
                    continue

            self.agents[name].add_mcp_tools(a.mcp_tools)

            A2AServer(
                agent_card=agent_card,
                task_manager=AgentTaskManager(agent=self.agents[name],
                                              notification_sender_auth=notification_sender_auth),
                host=host,
                port=port,
                starlette=starlette)
        return starlette
