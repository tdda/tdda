# -*- coding: utf-8 -*-

"""
test_gentest.py: Manually written tests of tdda gentest.
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import datetime
import os
import sys

from tdda.referencetest import ReferenceTestCase
from tdda.referencetest.gentest import TestGenerator

D1 = '/home/auser/python/tdda/tdda/referencetest/gentest'
HOST = 'ahost.local'
HOME = '/home/auser'
LOCALHOST = '127.0.0.1'   # not used
USER = 'auser'

class TestGenTest(ReferenceTestCase):
    def test1_date_exclusions(self):
        name = 'test_gentest1'
        t = TestGenerator(cwd=D1, command='', script=name,
                          reference_files=['STDOUT'],
                          check_stdout=True,
                          check_stderr=False, require_zero_exit_code=True,
                          iterations=0, verbose=False)

        t.refdir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'ref', name)
        t.host = HOST
        t.user = USER
        t.ip = LOCALHOST
        t.homedir = HOME
        t.min_time = datetime.datetime(2020,7,1,16,30,00)
        t.max_time = datetime.datetime(2020,7,1,16,30,02)
        t.reference_files[1] = os.path.join(t.refdir, 'STDOUT')
        t.reference_files[2] = os.path.join(t.refdir, '2', 'STDOUT')
        t.iterations = 2

        t.generate_exclusions()

        expected = {
r'^\d{2}$',
r'^Seed\: \d{10}$',
r'^Job completed after a total of 0\.\d{4} seconds\.$',
r'^Logging to \/home\/auser\/miro\/log\/2020\/07\/01\/[a-z]{7}\d{3}\.$',
r'^Logs [a-z]{6,7} at 2020\/07\/01 16\:30\:\d{2} host ahost\.local\.$',
r'^Logs written to \/home\/auser\/miro\/log\/2020\/07\/01\/[a-z]{7}\d{3}\.$',
r'ahost\.local',
        }
        self.assertEqual(set(t.exclusions['STDOUT'][0]), expected)
        self.assertEqual(set(t.exclusions['STDOUT'][1]), {'ODD'})


if __name__ == '__main__':
    ReferenceTestCase.main()
