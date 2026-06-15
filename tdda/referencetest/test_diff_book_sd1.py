"""
test_diff_book_sd1.py: Automatically generated test code from tdda gentest.

Generation command:

tdda gentest 'tdda diff testdata/elements3-old.parquet testdata/elements3-new.parquet --vertical --mono --polars' 'test_diff_book_sd1.py' '.' --non-zero-exit
"""

import os
import sys
import tempfile
import unittest
from shutil import which

from tdda.referencetest import ReferenceTestCase, tag
from tdda.referencetest.gentest import exec_command
from tdda.referencetest.utils import normalise_rich_table


@unittest.skipIf(not which('tdda'), 'tdda not installed')
class TestX_DIFF_BOOK_SD1(ReferenceTestCase):
    command = 'tdda diff testdata/elements3-old.parquet testdata/elements3-new.parquet --vertical --mono --polars'
    cwd = os.path.abspath(os.path.dirname(__file__))
    refdir = os.path.join(cwd, 'ref', 'diff_book_sd1')

    @classmethod
    def setUpClass(cls):
        (cls.output, cls.error, cls.exception, cls.exit_code, cls.duration) = (
            exec_command(cls.command, cls.cwd)
        )

    def test_no_exception(self):
        self.assertIsNone(self.exception)

    def test_exit_code(self):
        self.assertEqual(self.exit_code, 1)

    def test_stdout(self):
        # NOTE: norm_paths=True and preprocess=normalise_rich_table were
        # added manually to ensure this test works on Windows as well as
        # Unix/Linux/Mac.
        self.assertStringCorrect(
            self.output,
            os.path.join(self.refdir, 'STDOUT'),
            ignore_lines=[r'Value Differences (all rows with differences)'],
            norm_paths=True,
            preprocess=normalise_rich_table,
        )

    def test_stderr(self):
        self.assertStringCorrect(
            self.error,
            os.path.join(self.refdir, 'STDERR'),
            ignore_lines=['RequestsDependencyWarning', '  warnings.warn('],
        )


if __name__ == '__main__':
    ReferenceTestCase.main()
