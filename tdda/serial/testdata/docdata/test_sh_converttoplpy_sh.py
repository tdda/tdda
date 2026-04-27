"""
test_sh_converttoplpy_sh.py: Automatically generated test code from tdda gentest.

Generation command:

tdda gentest 'sh converttoplpy.sh' 'test_sh_converttoplpy_sh.py' '.'
"""

import os
import sys
import tempfile

from tdda.referencetest import ReferenceTestCase
from tdda.referencetest.gentest import exec_command


class Test_SH_CONVERTTOPLPY(ReferenceTestCase):
    command = 'sh converttoplpy.sh'
    cwd = os.path.abspath(os.path.dirname(__file__))
    refdir = os.path.join(cwd, 'ref', 'sh_converttoplpy_sh')

    generated_files = [
        os.path.join(cwd, 'examplereadpl.py')
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
        self.assertEqual(self.exit_code, 0)

    def test_stdout(self):
        self.assertStringCorrect(self.output,
                                 os.path.join(self.refdir, 'STDOUT'))

    def test_stderr(self):
        self.assertStringCorrect(self.error,
                                 os.path.join(self.refdir, 'STDERR'))

    def test_examplereadpl_py(self):
        self.assertTextFileCorrect(os.path.join(self.cwd, 'examplereadpl.py'),
                                   os.path.join(self.refdir, 'examplereadpl.py'),
                                   ignore_lines=["writer"],
                                   encoding='ascii')

if __name__ == '__main__':
    ReferenceTestCase.main()
