# -*- coding: utf-8 -*-

"""
test_discover25k.py: Automatically generated test code from tdda gentest.

Generation command:

  tdda gentest 'tdda discover INPUTS/testdata/accounts25k.csv $TMPDIR/accounts25k.tdda' 'test_discover25k.py' '.' STDOUT STDERR
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import os
import sys
import tempfile

from tdda.referencetest import ReferenceTestCase
from tdda.referencetest.gentest import exec_command



class TestDISCOVER25K(ReferenceTestCase):
    command = 'tdda discover INPUTS/testdata/accounts25k.csv $TMPDIR/accounts25k.tdda'
    cwd = os.path.abspath(os.path.dirname(__file__))
    refdir = os.path.join(cwd, 'ref', 'discover25k')
    orig_tmpdir = '/var/folders/zv/3xvhmvpj0216687_pk__2f5h0000gn/T/tmp9wX6S5'
    if not os.environ.get('TMPDIR_SET_BY_GENTEST'):
        tmpdir = tempfile.mkdtemp()
        os.environ['TMPDIR'] = tmpdir
        os.environ['TMPDIR_SET_BY_GENTEST'] = 'true'
    else:
        tmpdir = os.environ['TMPDIR']
    
    generated_files = [
        os.path.join(tmpdir, 'accounts25k.tdda')
    ]
    @classmethod
    def setUpClass(cls):
        for path in cls.generated_files:
            if os.path.exists(path):
                os.unlink(path)
        (cls.output,
         cls.error,
         cls.exc,
         cls.exit_code,
         cls.duration) = exec_command(cls.command, cls.cwd)

    def test_no_exception(self):
        msg = 'No exception should be generated'
        self.assertEqual((str(self.exc), msg), ('None', msg))

    def test_exit_code(self):
        self.assertEqual(self.exit_code, 0)

    def test_stdout(self):
        self.assertStringCorrect(self.output,
                                 os.path.join(self.refdir, 'STDOUT'))

    def test_stderr(self):
        self.assertStringCorrect(self.error,
                                 os.path.join(self.refdir, 'STDERR'))

    def test_accounts25k_tdda(self):
        patterns = [
            r'^        \"[a-z]{3,5}\_time\"\: \"2019\-05\-01 [0-9]{2}\:[0-9]{2}\:[0-9]{2}\"\, $',
        ]
        substrings = [
            'bartok.local',
            'njr',
            'time": "2019-05-01 ',
            self.orig_tmpdir,
        ]
        self.assertFileCorrect(os.path.join(self.tmpdir, 'accounts25k.tdda'),
                               os.path.join(self.refdir, 'accounts25k.tdda'),
                               ignore_patterns=patterns,
                               ignore_substrings=substrings)

if __name__ == '__main__':
    ReferenceTestCase.main()
