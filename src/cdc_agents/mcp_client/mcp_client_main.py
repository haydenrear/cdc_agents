import warnings

from python_util.logger.log_level import LogLevel, LogLevelFacade

from python_di.configs.app import boot_application
from cdc_agents.mcp_client.cdc_agents_mcp import CdcMcpAgents

warnings.warn = lambda *args, **kwargs: None

LogLevel.set_log_level(LogLevelFacade.Ctx)

@boot_application(root_dir_cls=CdcMcpAgents)
class CdcAgentsApplication:
    pass
