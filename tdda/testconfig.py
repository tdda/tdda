import os
import sys
import unittest


class TestSystemConfig(unittest.TestCase):
    def test_01_tdda_path(self):
        print('\ntype tdda')
        os.system('type tdda')
        print('which tdda')
        os.system('which tdda')

    def test_02_path(self):
        print('$PATH')
        os.system('echo $PATH')

    def test_03_pythonpath(self):
        print('PYTHON PATH')
        for p in sys.path:
            print(p)


if __name__ == '__main__':
    unittest.main()

