import unittest

from cdc_agents.agent.agent import get_exchange_rate
from cdc_agents.agent.task_manager import AgentTaskManager

class DoTestImportsWork(unittest.TestCase):
    def test_imports_work(self):
        out = get_exchange_rate
        a = AgentTaskManager


if __name__ == '__main__':
    unittest.main()
