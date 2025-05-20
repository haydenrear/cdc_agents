import inspect
import typing

import injector
from langchain.callbacks.base import BaseCallbackHandler
from langchain_core.messages import ToolMessage

from cdc_agents.config.tool_call_properties import ToolCallProps
from python_di.configs.autowire import injectable
from python_di.configs.component import component
from python_di.inject.profile_composite_injector.inject_context_di import autowire_fn, InjectionDescriptor, \
    InjectionType



@component()
@injectable()
class ToolCallDecorator:

    @injector.inject
    def __init__(self, tool_call_props: ToolCallProps):
        self.tool_call_props = tool_call_props
        self.tool_call_repository = {}


    def register_tool_call(self, tool_message: typing.Optional[ToolMessage], session_id: str, a2a_agent):
        if tool_message is not None and self.tool_call_props.register_tool_calls:
            agent = a2a_agent.agent_name
            name = tool_message.name
            status = tool_message.status
            if session_id not in self.tool_call_repository.keys():
                self.tool_call_repository[session_id] = {agent: []}

            (self.tool_call_repository[session_id][agent]
                .append({'name': name, 'agent': agent, 'status': status, 'session_id': session_id}))

class LoggingToolCallback(BaseCallbackHandler):
    """
    Run through fifty cases with various LLM to validate their efficacy, capturing information about tool calls for
    comparison.
    """
    def __init__(self, agent):
        self.agent = agent

    @staticmethod
    def _retrieve_session_id():
        session_id = 'could not find session ID'
        stack = inspect.stack()
        if len(stack) >= 3:
            s = stack[3]
            for k, v in s.frame.f_locals.items():
                if hasattr(v, 'metadata'):
                    m = getattr(v, 'metadata')
                    if isinstance(m, dict) and 'thread_id' in m.keys():
                        session_id = m.get('thread_id')
        return session_id

    @autowire_fn({
        'tool_call_decorator': InjectionDescriptor(injection_ty=InjectionType.Dependency),
        'tool_message': InjectionDescriptor(injection_ty=InjectionType.Provided),
        'session_id': InjectionDescriptor(injection_ty=InjectionType.Provided)
    })
    def register_tool_call(self, tool_call_decorator: ToolCallDecorator, tool_message: typing.Optional[ToolMessage],
                           session_id: typing.Optional[str]):
        tool_call_decorator.register_tool_call(tool_message, session_id, self.agent)
