import os

from cdc_agents.agent.agent_server import AgentServerRunner
from python_di.configs.app import boot_application

@boot_application(root_dir_cls=AgentServerRunner)
class CdcAgentsApplication:
    pass
