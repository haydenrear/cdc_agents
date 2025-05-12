import typing

from pydantic import BaseModel

from python_di.env.base_module_config_props import ConfigurationProperties
from python_di.properties.configuration_properties_decorator import configuration_properties

@configuration_properties(prefix_name='cdc_server')
class CdcServerConfigProps(ConfigurationProperties):
    graphql_endpoint: str = "localhost:9991"
