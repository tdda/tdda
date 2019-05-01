# -*- coding: utf-8 -*-

"""
test_discover1k.py: Automatically generated test code from tdda gentest.

Generation command:

  tdda gentest 'tdda discover -r INPUTS/testdata/accounts1k.csv $TMPDIR/accounts1k.tdda' 'test_discover1k.py' '.' STDOUT STDERR
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import os
import sys
import tempfile

from tdda.referencetest import ReferenceTestCase
from tdda.referencetest.gentest import exec_command

COMMAND = 'tdda discover -r INPUTS/testdata/accounts1k.csv $TMPDIR/accounts1k.tdda'
CWD = os.path.abspath(os.path.dirname(__file__))
REFDIR = os.path.join(CWD, 'ref', 'discover1k')
ORIG_TMPDIR = '/var/folders/zv/3xvhmvpj0216687_pk__2f5h0000gn/T/tmp8WCsfV'
TMPDIR = tempfile.mkdtemp()
os.environ['TMPDIR'] = TMPDIR

GENERATED_FILES = [
    '/var/folders/zv/3xvhmvpj0216687_pk__2f5h0000gn/T/tmp8WCsfV/accounts1k.tdda'
]


class TestAnalysis(ReferenceTestCase):
    @classmethod
    def setUpClass(cls):
        (cls.output,
         cls.error,
         cls.exc,
         cls.exit_code,
         cls.duration) = exec_command(COMMAND, CWD)
        for path in GENERATED_FILES:
            if os.path.exists(path):
                os.unlink(path)

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
            r'^        \"[a-z]{3,5}\_time\"\: \"2019\-05\-01 [0-9]{2}\:[0-9]{2}\:[0-9]{2}\"\, $',
        ]
        substrings = [
            'bartok.local',
            'njr',
            'time": "2019-05-01 ',
            ORIG_TMPDIR,
        ]
        self.assertFileCorrect(os.path.join(TMPDIR, 'accounts1k.tdda'),
                               os.path.join(REFDIR, 'accounts1k.tdda'),
                               ignore_patterns=patterns,
                               ignore_substrings=substrings)

if __name__ == '__main__':
    ReferenceTestCase.main()
