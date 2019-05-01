# -*- coding: utf-8 -*-

"""
test_verify_fail2.py: Automatically generated test code from tdda gentest.

Generation command:

  tdda gentest 'tdda verify -7 INPUTS/testdata/accounts25k.csv INPUTS/testdata/accounts1kedited.tdda' 'test_verify_fail2.py' '.' STDOUT STDERR
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import os
import sys
import tempfile

from tdda.referencetest import ReferenceTestCase
from tdda.referencetest.gentest import exec_command



class TestVERIFY_FAIL2(ReferenceTestCase):
    command = 'tdda verify -7 INPUTS/testdata/accounts25k.csv INPUTS/testdata/accounts1kedited.tdda'
    cwd = os.path.abspath(os.path.dirname(__file__))
    refdir = os.path.join(cwd, 'ref', 'verify_fail2')
    
    
    @classmethod
    def setUpClass(cls):
        
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

if __name__ == '__main__':
    ReferenceTestCase.main()
