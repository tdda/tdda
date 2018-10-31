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
from tdda.referencetest.gentest import *

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
        }
        self.assertEqual(set(t.exclusions['STDOUT'][0]), expected)
        self.assertEqual(set(t.exclusions['STDOUT'][1]), {'ODD'})

#    @tag
    def test2_simple_date_exclusions(self):
        name = 'test_gentest2'

        # Create a test generator that doesn't actually run the tests
        # (beqcause of iterations=0)
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
        rexes, removals, substrings = t.exclusions['STDOUT']

        expected_rexes = {
            r'^Plausible date 2020\-07\-01 12\:00\:\d{2} '
            r'and the hostname ahost  \# diff$'
            # ^ should be in because the line is different between
            # the two files
        }
        expected_removals = set()
        expected_substrings = {
            r'2020-07-01 12:00:13',    # should be in: it's a plausible date
            r'2020-07-01 12:00:00',    # should be in: it's a plausible date
                                       # (albeit only in a variable line)
            r'2020-07-02',             # should be in: it's a plausible date
            r'auser',                  # should be in: it's the user
        }

        # others
        # r'ahost',                   # host, but only in variable line;
                                      # not needed.
        # 2018-09-02                  # out of range date
        # 2018-09-02 03:00:00         # out of range datetime
        # ENDS                        # common; no reason to include

        self.assertEqual(set(rexes), expected_rexes)
        self.assertEqual(set(removals), expected_removals)
        self.assertEqual(set(substrings), expected_substrings)

    def test_date_finding_non_num_dates(self):
        bads = [
            '',
            'a',
            '111/22/3333',
            '3333-33-11',
            'lemons',
        ]
        for k in bads:
            self.assertIsNone(is_date_like(k))

    def test_date_finding_num_dates(self):
        goods = [
            '2018-10-22',
            '22-10-2018',
            '10-22-2018',
        ]
        for k in goods:
            self.assertIsNotNone(is_date_like(k))


    def test_date_finding_num_datetimes(self):
        goods = [
            '2018-10-22T01:23:45',
            '2018-10-22 01:23:45',
        ]
        for k in goods:
            self.assertIsNotNone(is_date_like(k))

    def test_date_finding_plausible_num_dates(self):
        goods = [
            '2018-10-22',
            '22-10-2018',
            '10-22-2018',
            '2018-10-22',
        ]
        bads = [
            '2019-10-22',
            '22-11-2018',
            '10-05-2018',
        ]
        alphas = [
            '22 October 2018',
            'October 22, 2018',
        ]
        d10 = datetime.datetime(2018,10,10)
        d21 = datetime.datetime(2018,10,21)
        d22 = datetime.datetime(2018,10,22)
        d23 = datetime.datetime(2018,10,23)
        d30 = datetime.datetime(2018,10,30)
        for k in goods:
            self.assertIsNotNone(is_date_like(k, min_time=d22, max_time=d22))
            self.assertIsNotNone(is_date_like(k, min_time=d21, max_time=d22))
            self.assertIsNotNone(is_date_like(k, min_time=d22, max_time=d23))
            self.assertIsNone(is_date_like(k, min_time=d10, max_time=d21))
            self.assertIsNone(is_date_like(k, min_time=d23, max_time=d30))

        for k in bads + alphas:
            self.assertIsNone(is_date_like(k, inc_alpha=False,
                             min_time=d22, max_time=d22))
            self.assertIsNone(is_date_like(k, inc_alpha=False,
                             min_time=d21, max_time=d22))
            self.assertIsNone(is_date_like(k, inc_alpha=False,
                             min_time=d22, max_time=d23))
            self.assertIsNone(is_date_like(k, inc_alpha=False,
                             min_time=d10, max_time=d21))
            self.assertIsNone(is_date_like(k, inc_alpha=False,
                             min_time=d23, max_time=d30))

        for k in alphas:
            self.assertIsNotNone(is_date_like(k, inc_alpha=True, min_time=d22,
                                          max_time=d22))
            self.assertIsNotNone(is_date_like(k, inc_alpha=True, min_time=d21,
                                          max_time=d22))
            self.assertIsNotNone(is_date_like(k, inc_alpha=True, min_time=d22,
                                          max_time=d23))
            self.assertIsNone(is_date_like(k, inc_alpha=True, min_time=d10,
                                          max_time=d21))
            self.assertIsNone(is_date_like(k, inc_alpha=True, min_time=d23,
                                          max_time=d30))

        self.assertIsNotNone(is_date_like('Tue 30 Oct 2018 18:05:20 GMT',
                                     inc_alpha=True,
                                     min_time=datetime.datetime(2018,10,29),
                                     max_time=datetime.datetime(2018,11,1)))

    def test_datetime_like(self):
        m = datetime.datetime(2020,6, 30)
        M = datetime.datetime(2020, 7, 2)

        for s in ('2020-07-02', '2020-07-01 12:00:13', '2020-07-01 12:00:00',
                  'Wed 2 Jul 2020 09:14:14 GMT'):
            self.assertIsNotNone(is_date_like(s, inc_alpha=True,
                                         min_time=m, max_time=M))
        for s in (
            '2020-07-01 12:00:13',
            '2020-07-01 12:00:00',
            'Wed 2 Jul 2020 09:14:14 GMT'
        ):
            self.assertIsNotNone(is_datetime_like(s))
        self.assertIsNone(is_datetime_like('2020-07-02'))


if __name__ == '__main__':
    ReferenceTestCase.main()
