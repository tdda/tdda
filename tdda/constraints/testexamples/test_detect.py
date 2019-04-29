# -*- coding: utf-8 -*-

"""
test_detect.py: Automatically generated test code from tdda gentest.

Generation command:

  tdda gentest 'tdda detect -7 INPUTS/testdata/accounts25k.csv INPUTS/testdata/accounts1kedited.tdda output/bads.csv' 'test_detect.py' '.' STDOUT STDERR
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import os
import sys

from tdda.referencetest import ReferenceTestCase
from tdda.referencetest.gentest import exec_command

COMMAND = 'tdda detect -7 INPUTS/testdata/accounts25k.csv INPUTS/testdata/accounts1kedited.tdda output/bads.csv'
CWD = os.path.abspath(os.path.dirname(__file__))
REFDIR = os.path.join(CWD, 'ref', 'detect')


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
        self.assertStringCorrect(self.output,
                                 os.path.join(REFDIR, 'STDOUT'))

    def test_stderr(self):
        self.assertStringCorrect(self.error,
                                 os.path.join(REFDIR, 'STDERR'))

    def test_bads_csv(self):
        self.assertFileCorrect(os.path.join(CWD, 'output/bads.csv'),
                               os.path.join(REFDIR, 'bads.csv'))

if __name__ == '__main__':
    ReferenceTestCase.main()
