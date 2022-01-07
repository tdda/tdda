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
        print('\nPATH=%s' % path)
        print('COMPONENTS:')
        for p in path.split(':'):
            print(p)
        print()

    def test_03_pythonpath(self):
        print('\nPYTHON PATH:')
        for p in sys.path:
            print(p)

    def test_04_numpy_pandas_versions(self):
        try:
            import numpy
            print('\nnumpy version:', numpy.__version__)
        except ImportError:
            print('numpy not found.')

        try:
            import pandas
            print('\npandas version:', pandas.__version__)
        except ImportError:
            print('pandas not found.')


if __name__ == '__main__':
    unittest.main()

