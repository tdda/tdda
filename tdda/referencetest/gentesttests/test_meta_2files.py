# -*- coding: utf-8 -*-

"""
test_meta_2files.py: Automatically generated test code from tdda gentest.

Generation command:

  tdda gentest 'tdda gentest "python 2files.py" 2files . stdout stderr nonzeroexit' 'test_meta_2files.py' 'ref/2files' STDOUT STDERR
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import os
import sys

from tdda.referencetest import ReferenceTestCase
from tdda.referencetest.gentest import exec_command

COMMAND = 'tdda gentest "python 2files.py" 2files . stdout stderr nonzeroexit'
CWD = os.environ.get('TDDA_CWD', '/Users/njr/python/tdda/tdda/referencetest/gentesttests')
REFDIR = os.path.join(CWD, 'ref', 'meta_2files')


class TestAnalysis(ReferenceTestCase):
    @classmethod
    def setUpClass(cls):
        (cls.output,
         cls.error,
         cls.exc,
         cls.exit_code,
         cls.duration) = exec_command(COMMAND, CWD)

    def test_no_exception(self):
        msg = 'No exception should be generated'
        self.assertEqual((str(self.exc), msg), ('None', msg))

    def test_exit_code(self):
        self.assertEqual(self.exit_code, 0)

    def test_stdout(self):
        IGNORES = [
            r'Command execution took:\s+\d+\.\d+s'
        ]
        self.assertStringCorrect(self.output,
                                 os.path.join(REFDIR, 'STDOUT'),
                                 ignore_patterns=IGNORES)

    def test_stderr(self):
        self.assertStringCorrect(self.error,
                                 os.path.join(REFDIR, 'STDERR'))

    def test_file_STDERR(self):
        self.assertFileCorrect(os.path.join(CWD, 'ref/2files/STDERR'),
                               os.path.join(REFDIR, 'STDERR'))

    def test_file_STDOUT(self):
        self.assertFileCorrect(os.path.join(CWD, 'ref/2files/STDOUT'),
                               os.path.join(REFDIR, 'STDOUT1'))

    def test_file_one_txt(self):
        self.assertFileCorrect(os.path.join(CWD, 'ref/2files/one.txt'),
                               os.path.join(REFDIR, 'one.txt'))

    def test_file_one_txt1(self):
        self.assertFileCorrect(os.path.join(CWD, 'ref/2files/one.txt1'),
                               os.path.join(REFDIR, 'one.txt1'))

if __name__ == '__main__':
    ReferenceTestCase.main()
