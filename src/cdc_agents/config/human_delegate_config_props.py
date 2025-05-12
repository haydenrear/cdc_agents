import typing
from pydantic import BaseModel
from pathlib import Path

from python_di.env.base_module_config_props import ConfigurationProperties
from python_di.properties.configuration_properties_decorator import configuration_properties

@configuration_properties(prefix_name='human_delegate')
class HumanDelegateConfigProps(ConfigurationProperties):
    base_dir: str = "./human_delegate_data"
    default_timeout_seconds: int = 300  # 5 minutes default timeout
    default_poll_interval: int = 5  # 5 seconds between polls
    min_messages_required: int = 1  # Default minimum number of messages to wait for
    session_cleanup_on_finalize: bool = False  # Don't clean up by default
    max_wait_attempts: int = 60  # Maximum number of polling attempts