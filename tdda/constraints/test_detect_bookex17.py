"""
test_detect_bookex17.py: Automatically generated test code from tdda gentest.

Generation command:

tdda gentest 'tdda detect testdata/accounts25k.parquet testdata/accountsv2.tdda scratch/a25k-bads-v2c.csv --report txt --key account_number' 'test_detect_bookex17.py' '.'
"""

import os
import sys
import tempfile

from tdda.referencetest import ReferenceTestCase
from tdda.referencetest.gentest import exec_command


class TestX_DETECT_BOOKEX17(ReferenceTestCase):
    command = 'tdda detect testdata/accounts25k.parquet testdata/accountsv2.tdda scratch/a25k-bads-v2c.csv --report txt --key account_number'
    cwd = os.path.abspath(os.path.dirname(__file__))
    refdir = os.path.join(cwd, 'ref', 'detect_bookex17')

    generated_files = [
        os.path.join(cwd, 'scratch/a25k-bads-v2c.csv'),
    os.path.join(cwd, 'scratch/a25k-bads-v2c.txt')
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

    def test_a25k_bads_v2c_csv(self):
        self.assertTextFileCorrect(os.path.join(self.cwd, 'scratch/a25k-bads-v2c.csv'),
                                   os.path.join(self.refdir, 'a25k-bads-v2c.csv'),
                                   encoding='ascii')

    def test_a25k_bads_v2c_txt(self):
        self.assertTextFileCorrect(os.path.join(self.cwd, 'scratch/a25k-bads-v2c.txt'),
                                   os.path.join(self.refdir, 'a25k-bads-v2c.txt'),
                                   encoding='utf-8')

if __name__ == '__main__':
    ReferenceTestCase.main()
