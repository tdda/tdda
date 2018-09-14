HEADER = '''# -*- coding: utf-8 -*-

"""
%s: Automatically generated test code from tdda gentest.
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import os
import sys

from tdda.referencetest import ReferenceTestCase
from tdda.referencetest.gentest import exec_command

COMMAND = %s
CWD = os.environ.get('TDDA_CWD', %s)
REFDIR = os.path.join(CWD, 'ref', %s)


class TestAnalysis(ReferenceTestCase):
    @classmethod
    def setUpClass(cls):
        cls.output, cls.error, cls.exc = exec_command(COMMAND, CWD)

    def test_no_exception(self):
        msg = 'No exception should be generated'
        self.assertEqual((str(self.exc), msg), ('None', msg))
'''


TAIL = '''
if __name__ == '__main__':
    ReferenceTestCase.main()
'''


STDOUT = '''
    def test_stdout(self):
        self.assertStringCorrect(self.output,
                                 %s)
'''

STDERR = '''
    def test_stderr(self):
        self.assertStringCorrect(self.error,
                                 %s)
'''

REFTEST = '''
    def test_file_%s(self):
        self.assertFileCorrect(%s,
                               %s)
'''
