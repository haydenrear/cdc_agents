import abc

from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import Runnable
from langchain_ollama import OllamaLLM, ChatOllama

from cdc_agents.config.agent_config_props import AgentCardItem
from cdc_agents.model_server.model_server_model import ModelServerModel
from python_di.configs.autowire import injectable
from python_di.configs.component import component
from python_di.inject.profile_composite_injector.inject_context_di import autowire_fn, InjectionDescriptor, \
    InjectionType


class ModelProvider(abc.ABC):

    @abc.abstractmethod
    def retrieve_model(self, agent_card: AgentCardItem, model=None):
        pass


@component(bind_to=[ModelProvider])
@injectable()
class ModelServerModelProvider(ModelProvider):

    def retrieve_model(self, agent_card: AgentCardItem, model=None):
        if model is not None and any([isinstance(model, m) for m in [BaseChatModel, Runnable]]):
            return model

        model = agent_card.agent_descriptor.model

        if isinstance(model, str):
            if model.startswith('ollama_text://'):
                return OllamaLLM(model = model.replace("ollama_text://ollama_text/", ""))
            if model.startswith('ollama_chat://'):
                return ChatOllama(model = model.replace("ollama_chat://ollama_chat/", ""))


        return self.build_model(agent_card=agent_card)

    @autowire_fn(descr={
        'model_server_model': InjectionDescriptor(injection_ty=InjectionType.Dependency),
        'agent_card': InjectionDescriptor(injection_ty=InjectionType.Provided)
    })
    def build_model(self, model_server_model: ModelServerModel, agent_card: AgentCardItem):
        model_server_model.initialize(agent_card)
        return model_server_model