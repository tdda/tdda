# -*- coding: utf-8 -*-

"""
test_detect.py: Automatically generated test code from tdda gentest.

Generation command:

  tdda gentest 'tdda detect -7 INPUTS/testdata/accounts25k.csv INPUTS/testdata/accounts1kedited.tdda $TMPDIR/bads.csv' 'test_detect.py' '.' STDOUT STDERR
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import os
import sys
import tempfile

from tdda.referencetest import ReferenceTestCase
from tdda.referencetest.gentest import exec_command



class TestDETECT(ReferenceTestCase):
    command = 'tdda detect -7 INPUTS/testdata/accounts25k.csv INPUTS/testdata/accounts1kedited.tdda $TMPDIR/bads.csv'
    cwd = os.path.abspath(os.path.dirname(__file__))
    refdir = os.path.join(cwd, 'ref', 'detect')
    orig_tmpdir = '/var/folders/zv/3xvhmvpj0216687_pk__2f5h0000gn/T/tmp7iuuFj'
    if not os.environ.get('TMPDIR_SET_BY_GENTEST'):
        tmpdir = tempfile.mkdtemp()
        os.environ['TMPDIR'] = tmpdir
        os.environ['TMPDIR_SET_BY_GENTEST'] = 'true'
    else:
        tmpdir = os.environ['TMPDIR']
    
    generated_files = [
        os.path.join(tmpdir, 'bads.csv')
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

    def test_bads_csv(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'bads.csv'),
                               os.path.join(self.refdir, 'bads.csv'))

if __name__ == '__main__':
    ReferenceTestCase.main()
