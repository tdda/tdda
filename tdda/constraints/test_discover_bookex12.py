"""
test_discover_bookex12.py: Automatically generated test code from tdda gentest.

Generation command:

tdda gentest 'tdda discover -xG testdata/accounts1k.csv scratch/accountsex12.tdda --no-config' 'test_discover_bookex12.py' '.'
"""

import os
import sys
import tempfile
import unittest
from shutil import which

from tdda.referencetest import ReferenceTestCase
from tdda.referencetest.gentest import exec_command


@unittest.skipIf(not which('tdda'), 'tdda not installed')
class TestX_DISCOVER_BOOKEX12(ReferenceTestCase):
    cwd = os.path.abspath(os.path.dirname(__file__))
    refdir = os.path.join(cwd, 'ref', 'discover_bookex12')
    tmpdir = tempfile.mkdtemp()
    tdda_out = os.path.join(tmpdir, 'accountsex12.tdda')
    command = 'tdda discover -xG testdata/accounts1k.csv %s --no-config' % tdda_out

    generated_files = [tdda_out]

    @classmethod
    def setUpClass(cls):
        for path in cls.generated_files:
            if os.path.exists(path):
                os.unlink(path)
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

    def test_accountsex12_tdda(self):
        patterns = [
            r'^        "local_time": "2026\-04\-09T11:59:[0-9]{2}",$',
            r'^        "utc_time": "2026\-04\-09T10:59:[0-9]{2}\+00:00",$',
        ]
        substrings = [
            '2026-04-09',
            'gardot.local',
            'njr',
            '"tddafile": ',
            '"creator": ',
        ]
        self.assertTextFileCorrect(
            self.tdda_out,
            os.path.join(self.refdir, 'accountsex12.tdda'),
            ignore_patterns=patterns,
            ignore_substrings=substrings,
            encoding='MacRoman',
        )


if __name__ == '__main__':
    ReferenceTestCase.main()
