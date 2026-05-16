"""
test_verify_bookex13.py: Automatically generated test code from tdda gentest.

Generation command:

tdda gentest 'tdda verify testdata/accounts1k.csv testdata/accountsex12.tdda --no-config' 'test_verify_bookex13.py' '.'
"""

import os
import sys
import tempfile
import unittest
from shutil import which

from tdda.referencetest import ReferenceTestCase
from tdda.referencetest.gentest import exec_command


@unittest.skipIf(not which('tdda'), 'tdda not installed')
class TestX_VERIFY_BOOKEX13(ReferenceTestCase):
    command = 'tdda verify testdata/accounts1k.csv testdata/accountsex12.tdda --no-config'
    cwd = os.path.abspath(os.path.dirname(__file__))
    refdir = os.path.join(cwd, 'ref', 'verify_bookex13')

    @classmethod
    def setUpClass(cls):
        (cls.output, cls.error, cls.exception, cls.exit_code, cls.duration) = (
            exec_command(cls.command, cls.cwd)
        )

    def test_no_exception(self):
        self.assertIsNone(self.exception)

    def test_exit_code(self):
        self.assertEqual(self.exit_code, 0)

    def test_stdout(self):
        self.assertStringCorrect(
            self.output, os.path.join(self.refdir, 'STDOUT')
        )

    def test_stderr(self):
        self.assertStringCorrect(
            self.error,
            os.path.join(self.refdir, 'STDERR'),
            ignore_lines=['RequestsDependencyWarning', '  warnings.warn('],
        )


if __name__ == '__main__':
    ReferenceTestCase.main()
