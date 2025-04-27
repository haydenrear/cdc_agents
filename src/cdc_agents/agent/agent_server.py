from cdc_agents.common.server import A2AServer
from cdc_agents.common.types import AgentCard, AgentCapabilities, AgentSkill, MissingAPIKeyError
from cdc_agents.common.utils.push_notification_auth import PushNotificationSenderAuth
from cdc_agents.agent.task_manager import AgentTaskManager
from cdc_agents.agent.agent import CurrencyAgent
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
    def __init__(self, agent_config_props: AgentConfigProps):
        self.agent_config_props = agent_config_props

    def run_server(self, host, port):
        """Starts the Currency Agent server."""
        capabilities = AgentCapabilities(streaming=True, pushNotifications=True)

        skill = AgentSkill(
            id="convert_currency",
            name="Currency Exchange Rates Tool",
            description="Helps with exchange values between various currencies",
            tags=["currency conversion", "currency exchange"],
            examples=["What is exchange rate between USD and GBP?"],
        )
        agent_card = AgentCard(
            name="Currency Agent",
            description="Helps with exchange rates for currencies",
            url=f"http://{host}:{port}/",
            version="1.0.0",
            defaultInputModes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
        )

        notification_sender_auth = PushNotificationSenderAuth()
        notification_sender_auth.generate_jwk()
        server = A2AServer(
            agent_card=agent_card,
            task_manager=AgentTaskManager(agent=CurrencyAgent(), notification_sender_auth=notification_sender_auth),
            host=host,
            port=port,
        )

        server.app.add_route(
            "/.well-known/jwks.json", notification_sender_auth.handle_jwks_endpoint, methods=["GET"]
        )

        LoggerFacade.info(f"Starting server on {host}:{port}")
        server.start()
