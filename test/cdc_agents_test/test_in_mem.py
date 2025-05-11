import unittest

from cdc_agents.agent.task_manager import AgentTaskManager
from cdc_agents.common.server import InMemoryTaskManager


class TestInMem(unittest.IsolatedAsyncioTestCase):
    async def test_something(self):
        t = AgentTaskManager(None, None)
        with t.lock:
            print("hello!")


if __name__ == '__main__':
    unittest.main()
