# -*- coding: utf-8 -*-

"""
test_discover1k.py: Automatically generated test code from tdda gentest.

Generation command:

  tdda gentest 'tdda discover -r INPUTS/testdata/accounts1k.csv $TMPDIR/accounts1k.tdda' 'test_discover1k.py' '.' STDOUT STDERR
"""


import os
import sys
import tempfile

from tdda.referencetest import ReferenceTestCase
from tdda.referencetest.gentest import exec_command



class TestDISCOVER1K(ReferenceTestCase):
    command = 'tdda discover -r INPUTS/testdata/accounts1k.csv $TMPDIR/accounts1k.tdda'
    cwd = os.path.abspath(os.path.dirname(__file__))
    refdir = os.path.join(cwd, 'ref', 'discover1k')
    orig_tmpdir = '/var/folders/zv/3xvhmvpj0216687_pk__2f5h0000gn/T/tmprDbo5u'
    if not os.environ.get('TMPDIR_SET_BY_GENTEST'):
        tmpdir = tempfile.mkdtemp()
        os.environ['TMPDIR'] = tmpdir
        os.environ['TMPDIR_SET_BY_GENTEST'] = 'true'
    else:
        tmpdir = os.environ['TMPDIR']
    generated_files = [
        os.path.join(tmpdir, 'accounts1k.tdda')
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

    def test_accounts1k_tdda(self):
        patterns = [
            r'^        \"[a-z]{3,5}\_time\"\: \"2019\-05\-01 [0-9]{2}\:[0-9]{2}\:[0-9]{2}\"\, $',
        ]
        substrings = [
            'bartok.local',
            'njr',
            'time": "2019-05-01 ',
            self.orig_tmpdir,
        ]
        self.assertFileCorrect(os.path.join(self.tmpdir, 'accounts1k.tdda'),
                               os.path.join(self.refdir, 'accounts1k.tdda'),
                               ignore_patterns=patterns,
                               ignore_substrings=substrings)

if __name__ == '__main__':
    ReferenceTestCase.main()
