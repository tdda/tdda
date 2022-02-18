HEADER = '''# -*- coding: utf-8 -*-
"""
%(SCRIPT)s: Automatically generated test code from tdda gentest.

Generation command:

%(GEN_COMMAND)s
"""

import os
import sys
import tempfile

from tdda.referencetest import ReferenceTestCase
from tdda.referencetest.gentest import exec_command


class Test%(CLASSNAME)s(ReferenceTestCase):
    command = %(COMMAND)s
    cwd = os.path.abspath(os.path.dirname(__file__))
    refdir = os.path.join(cwd, 'ref', %(NAME)s)
%(SET_TMPDIR)s
%(GENERATED_FILES)s
    @classmethod
    def setUpClass(cls):
        %(REMOVE_PREVIOUS_OUTPUTS)s
        (cls.output,
         cls.error,
         cls.exception,
         cls.exit_code,
         cls.duration) = exec_command(cls.command, cls.cwd)

    def test_no_exception(self):
        self.assertIsNone(self.exception)

    def test_exit_code(self):
        self.assertEqual(self.exit_code, %(EXIT_CODE)d)
'''


TAIL = '''
if __name__ == '__main__':
    ReferenceTestCase.main()
'''
