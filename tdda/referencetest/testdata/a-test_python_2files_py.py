"""
test_python_2files_py.py: Automatically generated test code from tdda gentest.

Generation command:

tdda gentest --non-zero-exit 'python 2files.py' 'test_python_2files_py.py' '.'
"""

import os
import sys
import tempfile

from tdda.referencetest import ReferenceTestCase
from tdda.referencetest.gentest import exec_command


class Test_PYTHON_2FILES_PY(ReferenceTestCase):
    command = 'python 2files.py'
    cwd = os.path.abspath(os.path.dirname(__file__))
    refdir = os.path.join(cwd, 'ref', 'python_2files_py')

    generated_files = [
        os.path.join(cwd, 'one.txt'),
    os.path.join(cwd, 'subdir/one.txt')
    ]
    @classmethod
    def setUpClass(cls):
        for path in cls.generated_files:
            if os.path.exists(path):
                os.unlink(path)
        (cls.output,
         cls.error,
         cls.exception,
         cls.exit_code,
         cls.duration) = exec_command(cls.command, cls.cwd)

    def test_no_exception(self):
        self.assertIsNone(self.exception)

    def test_exit_code(self):
        self.assertEqual(self.exit_code, 99)

    def test_stdout(self):
        self.assertStringCorrect(self.output,
                                 os.path.join(self.refdir, 'STDOUT'))

    def test_stderr(self):
        self.assertStringCorrect(self.error,
                                 os.path.join(self.refdir, 'STDERR'))

    def test_one_txt(self):
        self.assertTextFileCorrect(os.path.join(self.cwd, 'one.txt'),
                                   os.path.join(self.refdir, 'one.txt'),
                                   encoding='ascii')

    def test_one_txt2(self):
        self.assertTextFileCorrect(os.path.join(self.cwd, 'subdir/one.txt'),
                                   os.path.join(self.refdir, 'one.txt1'),
                                   encoding='ascii')

if __name__ == '__main__':
    ReferenceTestCase.main()
