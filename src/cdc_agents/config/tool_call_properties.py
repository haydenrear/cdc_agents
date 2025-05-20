from python_di.env.base_module_config_props import ConfigurationProperties
from python_di.properties.configuration_properties_decorator import configuration_properties


@configuration_properties(prefix_name='tool_call')
class ToolCallProps(ConfigurationProperties):
    register_tool_calls: bool = False
