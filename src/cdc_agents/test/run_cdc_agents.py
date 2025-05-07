from dotenv import load_dotenv

from python_util.logger.logger import LoggerFacade


def main():
    import sys, os, unittest
    s = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    print(s)
    load_dotenv(os.path.join(s, '.env'))
    test_dir = os.path.join(s, 'test')
    sys.path.insert(0, s)
    suite = unittest.defaultTestLoader.discover(test_dir)
    runner = unittest.TextTestRunner()
    tr = runner.run(suite)
    LoggerFacade.info(f'RAN TESTS: {tr}')