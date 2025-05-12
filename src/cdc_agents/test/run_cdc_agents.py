from dotenv import load_dotenv

from python_util.logger.log_level import LogLevel, LogLevelFacade
from python_util.logger.logger import LoggerFacade

LogLevel.set_log_level(LogLevelFacade.Ctx)

def main():
    import sys, os, unittest
    s = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    load_dotenv(os.path.join(s, '.env'))
    test_dir = os.path.join(s, 'test')
    sys.path.insert(0, s)
    suite = unittest.defaultTestLoader.discover(test_dir)
    runner = unittest.TextTestRunner()
    try:
        tr = runner.run(suite)

        if len(tr.errors) != 0:
            LoggerFacade.to_ctx(f"I ran the tests and still found some errors.\n")
            LoggerFacade.to_ctx(f"We have found {len(tr.errors)} errors.\n")

        for e in tr.errors:
            LoggerFacade.to_ctx(f'Here is another error: {e}\n')

        if len(tr.errors):
            LoggerFacade.to_ctx("Ran all tests successfully!")

        LoggerFacade.to_ctx(f"Test Report:\n{tr}\n")
    except Exception as e:
        LoggerFacade.to_ctx(f"Failed to run tests with error:\n{e}\n")