import unittest

from cdc_agents.agent.task_manager import AgentTaskManager

class DoTestImportsWork(unittest.TestCase):
    def test_imports_work(self):
        a = AgentTaskManager
        assert True, "Imports successful"


