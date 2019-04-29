# -*- coding: utf-8 -*-

"""
test_discover1k.py: Automatically generated test code from tdda gentest.

Generation command:

  tdda gentest 'tdda discover -r INPUTS/testdata/accounts1k.csv output/accounts1k.tdda' 'test_discover1k.py' '.' STDOUT STDERR
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import os
import sys

from tdda.referencetest import ReferenceTestCase
from tdda.referencetest.gentest import exec_command

COMMAND = 'tdda discover -r INPUTS/testdata/accounts1k.csv output/accounts1k.tdda'
CWD = os.path.abspath(os.path.dirname(__file__))
REFDIR = os.path.join(CWD, 'ref', 'discover1k')


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

    def test_accounts1k_tdda(self):
        patterns = [
            r'^        \"[a-z]{3,5}\_time\"\: \"2019\-04\-29 [0-9]{2}\:[0-9]{2}\:[0-9]{2}\"\, $',
        ]
        substrings = [
            'bartok.local',
            'njr',
            'time": "2019-04-29 ',
            'time": "2019-04-29 ',
        ]
        self.assertFileCorrect(os.path.join(CWD, 'output/accounts1k.tdda'),
                               os.path.join(REFDIR, 'accounts1k.tdda'),
                               ignore_patterns=patterns,
                               ignore_substrings=substrings)

if __name__ == '__main__':
    ReferenceTestCase.main()
