from python_di.configs.app import boot_application
import os
from cdc_agents.mcp_client.cdc_agents_mcp import CdcMcpAgents

@boot_application(root_dir_cls=CdcMcpAgents)
class CdcAgentsApplication:
    pass
