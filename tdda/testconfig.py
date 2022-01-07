import os
import sys
import unittest


class TestSystemConfig(unittest.TestCase):
    def test_01_tdda_path(self):
        print('\ntype tdda')
        with os.popen('type tdda') as f:
            path = f.read()
        print(path)
        print('which tdda')
        with os.popen('which tdda') as f:
            path = f.read()
        print(path)

    def test_02_path(self):
        path = os.environ.get('PATH')
        print('PATH=%s' % path)
        print('COMPONENTS:')
        for p in path.split(':'):
            print(p)
        print()

    def test_03_pythonpath(self):
        print('PYTHON PATH:')
        for p in sys.path:
            print(p)


if __name__ == '__main__':
    unittest.main()

