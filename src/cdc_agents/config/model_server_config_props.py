import typing

from pydantic import BaseModel

from python_di.env.base_module_config_props import ConfigurationProperties
from python_di.properties.configuration_properties_decorator import configuration_properties

class ModelServerModelProps(BaseModel):
    path: str
    api_key: str

@configuration_properties(prefix_name='model_server')
class ModelServerConfigProps(ConfigurationProperties):
    host: str
    port: int
    models: typing.List[ModelServerModelProps] = None
