import os

from python_di.inject.context_builder.injection_context import InjectionContext

inject_ctx = InjectionContext()
env = inject_ctx.initialize_env()

to_scan = os.path.dirname(os.path.dirname(__file__))
inject_ctx.build_context(parent_sources={to_scan}, source_directory=os.path.dirname(to_scan))