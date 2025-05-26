from cdc_agents.agent.agent_server import AgentServerRunner
from python_di.configs.app import boot_application
import os

os.environ['SPRING_PROFILES_ACTIVE'] = 'a2a,secret'

@boot_application(root_dir_cls=AgentServerRunner)
class CdcAgentsApplication:
    pass
