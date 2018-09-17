# -*- coding: utf-8 -*-

"""
test_meta_2files_fail.py: Automatically generated test code from tdda gentest.

Generation command:

  tdda gentest 'tdda gentest -r "python 2files.py" 2files . stdout stderr' 'test_meta_2files_fail.py' 'ref/2files' STDOUT STDERR NONZEROEXIT
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import os
import sys

from tdda.referencetest import ReferenceTestCase
from tdda.referencetest.gentest import exec_command

COMMAND = 'tdda gentest -r "python 2files.py" 2files . stdout stderr'
CWD = os.environ.get('TDDA_CWD', '/Users/njr/python/tdda/tdda/referencetest/gentesttests')
REFDIR = os.path.join(CWD, 'ref', 'meta_2files_fail')


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
        self.assertEqual(self.exit_code, 1)

    def test_stdout(self):
        self.assertStringCorrect(self.output,
                                 os.path.join(REFDIR, 'STDOUT'))

    def test_stderr(self):
        self.assertStringCorrect(self.error,
                                 os.path.join(REFDIR, 'STDERR'))

if __name__ == '__main__':
    ReferenceTestCase.main()
