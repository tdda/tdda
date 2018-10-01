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

from tdda.referencetest import ReferenceTestCase, tag
from tdda.referencetest.gentest import TestGenerator

D1 = '/home/auser/python/tdda/tdda/referencetest/gentest'
HOST = 'ahost.local'
ALTHOST = 'ahost'
HOME = '/home/auser'
LOCALHOST = '127.0.0.1'   # not used
USER = 'auser'


def set_test_attributes(t):
    t.host = HOST
    t.user = USER
    t.ip = LOCALHOST
    t.homedir = HOME
    t.start_time = datetime.datetime(2020,7,1,16,30,00)
    t.stop_time = datetime.datetime(2020,7,1,16,30,02)
    t.set_min_max_time()
    t.reference_files[1] = os.path.join(t.refdir, 'STDOUT')
    t.reference_files[2] = os.path.join(t.refdir, '2', 'STDOUT')
    t.iterations = 2


class TestGenTest(ReferenceTestCase):
    @tag
    def test1_exclusions(self):
        name = 'test_gentest1'
        # Create a test generator that doesn't actually run the tests
        # (bcause of iterations=0)
        t = TestGenerator(cwd=D1, command='', script=name,
                          reference_files=['STDOUT'],
                          check_stdout=True,
                          check_stderr=False, require_zero_exit_code=True,
                          iterations=0, verbose=False)

        # Point the reference directory to the right place, which
        # the ref directory next to this file.
        t.refdir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'ref', name)

        # Fix everything else to be as if the modified Miro script output
        # had been on the host HOST, with the cwd as D1
        # and had run between 16:30:00 and 16:30:02 on 1st July 2020,
        # and iterations had actually been 2.

        set_test_attributes(t)
        t.generate_exclusions()

        expected = {
r'^\d{2}$',
r'^Seed\: \d{10}$',
r'^Job completed after a total of 0\.\d{4} seconds\.$',
r'^Logging to \/home\/auser\/miro\/log\/2020\/07\/01\/[a-z]{7}\d{3}\.$',
r'^Logs [a-z]{6,7} at 2020\/07\/01 16\:30\:\d{2} host ahost\.local\.$',
r'^Logs written to \/home\/auser\/miro\/log\/2020\/07\/01\/[a-z]{7}\d{3}\.$',
#r'ahost\.local',
#r'2020\/07\/01',
#r'2020\/07\/01\ 16\:30\:48'
        }
        self.assertEqual(set(t.exclusions['STDOUT'][0]), expected)
        self.assertEqual(set(t.exclusions['STDOUT'][1]), {'ODD'})

    def test2_simple_date_exclusions(self):
        name = 'test_gentest2'

        # Create a test generator that doesn't actually run the tests
        # (bcause of iterations=0)
        t = TestGenerator(cwd=D1, command='', script=name,
                          reference_files=['STDOUT'],
                          check_stdout=True,
                          check_stderr=False, require_zero_exit_code=True,
                          iterations=0, verbose=False)

        # Point the reference directory to the right place, which
        # the ref directory next to this file.
        t.refdir = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'ref', name)

        # Fix everything else to be as if the modified Miro script output
        # had been on the host HOST, with the cwd as D1
        # and had run between 16:30:00 and 16:30:02 on 1st July 2020,
        # and iterations had actually been 2.

        set_test_attributes(t)
        t.generate_exclusions()

        expected = {
r'^Plausible date 2020\-07\-01 12\:00\:\d{2} and the hostname ahost  \# diff$',
        # ^ should be in because the line is different between the two files
r'2020\-07\-01\ 12\:00\:13',  # should be in because it's a plausible date
r'2020\-07\-02',              # should be in because it's a plausible date
r'auser',                     # should be in because it's the user
# r'ahost',                   # host, but only in variable line; not needed.
# 2018-09-02                  # out of range date
# 2018-09-02 03:00:00         # out of range datetime
# ENDS                        # common; no reason to include
        }
        self.assertEqual(set(t.exclusions['STDOUT'][0]), expected)
        self.assertEqual(set(t.exclusions['STDOUT'][1]), set())


if __name__ == '__main__':
    ReferenceTestCase.main()
