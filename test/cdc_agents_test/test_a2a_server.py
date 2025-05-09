import unittest


class A2AServerTest(unittest.TestCase):

    def test_receive_a2a_invoke(self):
        pass

    def test_receive_a2a_invoke_orchestrator_needs_input_invoke_again(self):
        pass

    def test_receive_a2a_invoke_inner_agent_needs_input_invoke_again(self):
        pass

    def test_concurrent_execution_add_history_invoke(self):
        pass

    def test_stream_video_file(self):
        pass

    def test_invalid_session_id(self):
        pass

    def test_push_notification(self):
        pass

    def test_stream_agent(self):
        pass

    def test_stream_agent_deny_concurrent_execution(self):
        pass

    def test_stream_agent_add_history(self):
        pass

    def test_postgres_checkpointer_concurrent_execution(self):
        """
        The TaskManager must be made to be a postgres repository in this case, and need distributed lock stripes.
        :return:
        """
        pass