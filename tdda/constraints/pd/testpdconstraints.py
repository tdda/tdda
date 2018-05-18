# -*- coding: utf-8 -*-

"""
Test Suite
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import datetime
import json
import math
import os
import time
import shutil
import subprocess
import sys
import tempfile
import unittest

from collections import OrderedDict
from distutils.spawn import find_executable

import pandas as pd
import numpy as np

from tdda.constraints.base import (
    MinConstraint,
    MaxConstraint,
    SignConstraint,
    TypeConstraint,
    MaxNullsConstraint,
    NoDuplicatesConstraint,
    AllowedValuesConstraint,
    MinLengthConstraint,
    MaxLengthConstraint,
    DatasetConstraints,
    Fields,
    FieldConstraints,
    verify,
    native_definite,
    UTF8DefiniteObject,
    fuzzy_less_than,
    fuzzy_greater_than,
)
from tdda.constraints.console import main_with_argv

from tdda.constraints.pd import constraints as pdc
from tdda.constraints.pd.constraints import (load_df, verify_df,
                                             discover_df, detect_df)
from tdda.constraints.pd.discover import discover_df_from_file
from tdda.constraints.pd.verify import verify_df_from_file

from tdda.referencetest import ReferenceTestCase, tag

isPython2 = sys.version_info[0] < 3

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
TESTDATA_DIR = os.path.join(os.path.dirname(THIS_DIR), 'testdata')


SMALL = 2.48e-324
MILLION = 1000 * 1000
REAL_MILLION = 1000 * 1000.0
BOOLS = (True, False)
SMI = 9223372036854775807
POS_INTS = (1, SMI, SMI + 1)
NEG_INTS = (-1, -SMI - 1, -SMI - 2)
INTS = POS_INTS + (0,) + NEG_INTS
POS_REALS = (1.0, SMALL, SMI * math.pi, float('inf'), time.time())
NEG_REALS = (-1.0, -SMALL, -SMI * math.pi, -float('inf'), -time.time())
REALS = POS_REALS + (0.0,) + NEG_REALS
NUMBERS = BOOLS + INTS + REALS
STRINGS = ('', 'a', 'αβγδε')
NULLS = (None,)
DATES = (datetime.datetime(1970, 1, 1),
         datetime.datetime(1, 1, 1),
         datetime.datetime(9999, 12, 31, 23, 59, 59),
         datetime.datetime.now(),
         datetime.datetime.utcnow())
OTHERS = (3 + 4j, lambda x: 1, [], (), {}, Exception) + ((u'u',) if isPython2
                                                              else (b'u',))


THIS_DIR = os.path.dirname(os.path.abspath(__file__))
TESTDATA_DIR = os.path.join(os.path.dirname(THIS_DIR), 'testdata')


class ConstraintVerificationTester:
    """
    Delegate class for checking constraint verifications.

    This exists so that when there are test failures,
    useful information about failing inputs and outputs can be shown.
    """
    outstandingAssertions = 0
    def __init__(self, tester, *args, **kwargs):
        self.tester = tester
        self.verifier = pdc.PandasConstraintVerifier(*args, **kwargs)

    def __getattr__(self, k):
        if k == 'decOutstanding':
            return self.decOutstanding
        return lambda *args, **kwargs: self.invoke(k, *args, **kwargs)

    def invoke(self, method, *args, **kwargs):
        satisfied = getattr(self.verifier, method)(*args, **kwargs)
        ConstraintVerificationTester.outstandingAssertions += 1
        return Asserter(self, satisfied, method, args, kwargs)

    def decOutstanding(self):
        ConstraintVerificationTester.outstandingAssertions -= 1


class Asserter:
    """
    """
    def __init__(self, cvt, satisfied, method, args, kwargs):
        self.cvt = cvt
        self.satisfied = satisfied
        self.method = method
        self.args = args
        self.kwargs = kwargs

    def isTrue(self):
        self.cvt.decOutstanding()
        self.cvt.tester.assertTrue(self.satisfied, self.diagnostic(True))

    def isFalse(self):
        self.cvt.decOutstanding()
        self.cvt.tester.assertFalse(self.satisfied, self.diagnostic(False))

    def diagnostic(self, expected):
        return ('Verifier: %s Inputs: %s %s: Assertion: %s'
                % (self.method, str(self.args),
                   str(self.kwargs) if self.kwargs else '',
                   'satisified' if expected is True
                                else 'not satisfied' if expected is False
                                else expected))



class TestPandasIndividualConstraintVerifier(ReferenceTestCase):
    @classmethod
    def tearDownClass(cls):
        assert ConstraintVerificationTester.outstandingAssertions == 0

    def test_tdda_types_of_base_types(self):
        self.assertEqual(pdc.pandas_tdda_type(None), 'null')
        for v in BOOLS:
            self.assertEqual(pdc.pandas_tdda_type(v), 'bool')
        for v in INTS:
            self.assertEqual(pdc.pandas_tdda_type(v), 'int')
        for v in REALS:
            self.assertEqual(pdc.pandas_tdda_type(v), 'real')
        for v in STRINGS:
            self.assertEqual(pdc.pandas_tdda_type(v), 'string')
        for v in DATES:
            self.assertEqual(pdc.pandas_tdda_type(v), 'date')
        for v in OTHERS:
            self.assertEqual(pdc.pandas_tdda_type(v), 'other')

    def test_coarse_types_of_base_types(self):
        self.assertEqual(pdc.pandas_tdda_type(None), 'null')
        for v in BOOLS:
            self.assertEqual(pdc.pandas_coarse_type(v), 'number')
        for v in INTS:
            self.assertEqual(pdc.pandas_coarse_type(v), 'number')
        for v in REALS:
            self.assertEqual(pdc.pandas_coarse_type(v), 'number')
        for v in STRINGS:
            self.assertEqual(pdc.pandas_coarse_type(v), 'string')
        for v in DATES:
            self.assertEqual(pdc.pandas_coarse_type(v), 'date')
        for v in OTHERS:
            self.assertEqual(pdc.pandas_coarse_type(v), 'other')

    def test_compatibility(self):
        for kind in (NUMBERS, STRINGS, DATES):
            x = kind[0]
            y = kind[-1]
            self.assertTrue(pdc.pandas_types_compatible(x, y))
            self.assertTrue(pdc.pandas_types_compatible(x, x))

    def test_incompatibility(self):
        for X in (NUMBERS, STRINGS, DATES, OTHERS, NULLS):
            for Y in (NUMBERS, STRINGS, DATES, OTHERS, NULLS):
                if X is not Y:
                    self.assertFalse(pdc.pandas_types_compatible(X[0], Y[0]))
                    self.assertFalse(pdc.pandas_types_compatible(Y[0], X[0]))

    def test_fuzzy_less_than_zero(self):
        verifier = pdc.PandasConstraintVerifier(df=None)
        epsilon = 0.01
        for x in NEG_REALS:
            self.assertTrue(fuzzy_less_than(x, 0.0, epsilon))
            self.assertFalse(fuzzy_less_than(0.0, x, epsilon))
        for x in POS_REALS:
            self.assertFalse(fuzzy_less_than(x, 0.0, epsilon))
            self.assertTrue(fuzzy_less_than(0.0, x, epsilon))

        self.assertTrue(fuzzy_less_than(0.0, 0.0, epsilon))
        self.assertTrue(fuzzy_less_than(0.0, SMALL / 2, epsilon))  # == 0.0
        self.assertEqual(SMALL / 2, 0.0)

    def test_fuzzy_less_than(self):
        goods = (
            (1.0, 1.0),
            (1.00999, 1.0),

            (MILLION, MILLION),
            (MILLION + 9999, MILLION),
            (MILLION + 10000, MILLION),
            (REAL_MILLION, REAL_MILLION),
            (MILLION + 9999.0, REAL_MILLION),
            (MILLION + 10000.0, MILLION),

            (1e-100, 1e-100),
            (1.00999e-100, 1e-100),

            (-1.0, -1.0),
            (-.990001, -1.0),

            (-MILLION, -MILLION),
            (-MILLION + 9999, -MILLION),
            (-MILLION + 10000, -MILLION),
            (-REAL_MILLION, -REAL_MILLION),
            (-REAL_MILLION + 9999.0, -REAL_MILLION),
            (-REAL_MILLION + 10000.0, -MILLION),

            (-1e-100, -1e-100),
            (-0.999999e-100, -1e-100),
        )
        bad_goods = (
            (MILLION + 10000 + SMALL, MILLION),  # Should fail mathematically.
                                                 # But rounding
        )
        bads = (
            (1.01000001, 1.0),
            (MILLION + 10001, MILLION),
            (MILLION + 10000.0000000001, MILLION),
            (1.010001e-100, 1.0e-100),

            (-0.989999, -1.0),
            (-MILLION + 100001, -MILLION),
            (-MILLION + 10000.0000000001, -MILLION),
            (-0.98999e-100, -1.0e-100),
        )

        cvt = ConstraintVerificationTester(self, df=None)
        self.assertEqual(MILLION + 10000 + SMALL, MILLION + 10000)
        epsilon = 0.01
        for (x, y) in goods + bad_goods:
            self.assertTrue(fuzzy_less_than(x, y, epsilon))
        for (x, y) in bads:
            self.assertFalse(fuzzy_less_than(x, y, epsilon))

    def test_fuzzy_greater_than_zero(self):
        cvt = ConstraintVerificationTester(self, df=None)
        epsilon = 0.01
        for x in POS_REALS:
            self.assertTrue(fuzzy_greater_than(x, 0.0, epsilon))
            self.assertFalse(fuzzy_greater_than(0.0, x, epsilon))
        for x in NEG_REALS:
            self.assertFalse(fuzzy_greater_than(x, 0.0, epsilon))
            self.assertTrue(fuzzy_greater_than(0.0, x, epsilon))

        self.assertTrue(fuzzy_greater_than(0.0, 0.0, epsilon))
        self.assertTrue(fuzzy_greater_than(0.0, SMALL / 2, epsilon))  # == 0.0
        self.assertEqual(SMALL / 2, 0.0)

    def test_fuzzy_greater_than(self):
        goods = (
            (1.0, 1.0),
            (.9900001, 1.0),

            (MILLION, MILLION),
            (999900, MILLION),
            (999899, MILLION),
            (999899.999, REAL_MILLION),

            (1e-100, 1e-100),
            (0.99000001e-100, 1e-100),

            (-1.0, -1.0),
            (-1.009999, -1.0),

            (-MILLION, -MILLION),
            (-MILLION + 10000, -MILLION),
            (-REAL_MILLION, -REAL_MILLION),
            (-REAL_MILLION + 10000.0001, -REAL_MILLION),
            (-REAL_MILLION + 10000.0, -MILLION),

            (-1e-100, -1e-100),
            (-0.99001e-100, -1e-100),
        )
        bad_goods = (
            (999900 - SMALL, MILLION),  # Should fail mathematically.
                                        # But MILLION + SMALL == MILLION
        )
        bads = (
            (0.9899999, 1.0),
            (MILLION - 10001, MILLION),
            (MILLION - 10000.0000000001, MILLION),
            (0.989999-100, 1.0e-100),

            (-1.01001, -1.0),
            (-MILLION - 10001, -MILLION),
            (-MILLION - 10000.0000000001, -MILLION),
            (-1.0100001e-100, -1.0e-100),

        )
        cvt = ConstraintVerificationTester(self, df=None)
        self.assertEqual(999900 - SMALL, 999900)
        epsilon = 0.01
        for (x, y) in goods + bad_goods:
            self.assertTrue(fuzzy_greater_than(x, y, epsilon))
        for (x, y) in bads:
            self.assertFalse(fuzzy_greater_than(x, y, epsilon))

    def test_caching(self):
        df = pd.DataFrame({
            'a': range(3),
        })
        v = pdc.PandasConstraintVerifier(df)

        # First check the max gets computed and cached correctly
        self.assertEqual(v.get_max('a'), 2)
        self.assertEqual(v.cache['a']['max'], 2)

        # write new results (which are obviously wrong, but no matter)
        v.cache['a']['max'] = -3

        # Now check the new (wrong) values are returned, and remain cached
        self.assertEqual(v.get_max('a'), -3)
        self.assertEqual(v.cache['a']['max'], -3)

    def test_verify_min_constraint(self):
        df = pd.DataFrame({
            'intzero': range(3),
            'intzeron': [0, None, 1],
            'intzeronn': [0, np.nan, 1],

            'realzero': [float(i) for i in range(3)],
            'realzeron': [0.0, None, 1.0],
            'realzeronn': [0.0, np.nan, 1.0],

            'int1': range(1, 4),
            'real1': [float(i) for i in range(1, 4)],

            'sempty': [''] * 3,
            'semptyn': ['', '', None],

            'sabc': ['a', 'b', 'c'],
            'sacn': ['a', 'c', None],

        })
        goods0 = [
            (col, v, p)
            for p in (None, 'closed', 'fuzzy')
            for v in (0, 0.0)
            for col in ('intzero', 'intzeron', 'intzeronn',
                        'realzero', 'realzeron', 'realzeronn')
        ]
        bads0 = [
            (col, v, 'open')
            for v in (0, 0.0)
            for col in ('intzero', 'intzeron', 'intzeronn',
                        'realzero', 'realzeron', 'realzeronn')
        ]

        goods1 = [
            (col, v, p)
            for p in (None, 'closed', 'fuzzy')
            for v in (1, 1.0)
            for col in ('int1', 'real1')
        ]
        bads1 = [
            (col, v, 'open')
            for v in (1, 1.0)
            for col in ('int1', 'real1')
        ]

        good_strings = [
            ('sempty', '', 'closed'),
            ('semptyn', '', 'closed'),
            ('sabc', '', 'closed'),
            ('sacn', '', 'closed'),
            ('sabc', 'a', 'closed'),
            ('sacn', 'a', 'closed'),
            ('sabc', 'A', 'closed'),
            ('sacn', 'A', 'closed'),
        ]

        bad_strings = [
            ('sempty', 'a', 'closed'),
            ('semptyn', 'A', 'closed'),
            ('sabc', 'b', 'closed'),
            ('sacn', 'b', 'closed'),
            ('sabc', 'foo', 'closed'),
            ('sacn', 'bar', 'closed'),
        ]

        goods = goods0 + goods1 + good_strings
        bads = bads0 + bads1 + bad_strings
        cvt = ConstraintVerificationTester(self, df)
        for (col, value, precision) in goods:
            c = MinConstraint(value, precision=precision)
            cvt.verify_min_constraint(col, c).isTrue()
        for (col, value, precision) in bads:
            c = MinConstraint(value, precision=precision)
            cvt.verify_min_constraint(col, c).isFalse()

    def test_verify_max_constraint(self):
        df = pd.DataFrame({
            'intzero': range(-2, 1),
            'intzeron': [0, None, -1],
            'intzeronn': [0, np.nan, -1],

            'realzero': [-float(i) for i in range(3)],
            'realzeron': [0.0, None, -1.0],
            'realzeronn': [0.0, np.nan, -1.0],

            'int1': range(-1, 2),
            'real1': [float(i) for i in range(-1, 2)]

        })
        goods0 = [
            (col, v, p)
            for p in (None, 'closed', 'fuzzy')
            for v in (0, 0.0)
            for col in ('intzero', 'intzeron', 'intzeronn',
                        'realzero', 'realzeron', 'realzeronn')
        ]
        bads0 = [
            (col, v, 'open')
            for v in (0, 0.0)
            for col in ('intzero', 'intzeron', 'intzeronn',
                        'realzero', 'realzeron', 'realzeronn')
        ]
        goods1 = [
            (col, v, p)
            for p in (None, 'closed', 'fuzzy')
            for v in (1, 1.0)
            for col in ('int1', 'real1')
        ]
        bads1 = [
            (col, v, 'open')
            for v in (1, 1.0)
            for col in ('int1', 'real1')
        ]

        goods = goods0 + goods1
        bads = bads0 + bads1

        cvt = ConstraintVerificationTester(self, df)
        for (col, value, precision) in goods:
            c = MaxConstraint(value, precision=precision)
            cvt.verify_max_constraint(col, c).isTrue()
        for (col, value, precision) in bads:
            c = MaxConstraint(value, precision=precision)
            cvt.verify_max_constraint(col, c).isFalse()

    def test_verify_min_max_length_constraints(self):
        df = pd.DataFrame({
            'zero': [''] * 4,
            'zeroOne': ['', 'a', '1', None],
            'one': ['α', 'b', 'c', None],       # Note unicode; min max len 1
            'oneTwo': ['a', 'aa', 'bb', None],
            'two': ['αα', 'αα', 'ββ', 'ββ'],    # Note unicode; min max len 2
        })
        goods = [
            ('zero', 0, 0),
            ('zero', 0, 10),

            ('zeroOne', 0, 1),
            ('zeroOne', 0, 5),

            ('one', 1, 1),
            ('one', 0, 1),
            ('one', 1, 4),
            ('one', 0, 10),

            ('oneTwo', 1, 2),
            ('oneTwo', 0, 2),
            ('oneTwo', 1, 4),
            ('oneTwo', 0, 10),

            ('two', 2, 2),
            ('two', 0, 2),
            ('two', 2, 8),
            ('two', 0, 7),
        ]
        bads = [
            ('zero', 1, None),
            ('zeroOne', 2, 0),
            ('one', 2, 0),
            ('oneTwo', 3, 0),
            ('two', 3, 1),
        ]
        cvt = ConstraintVerificationTester(self, df)
        for (col, m, M) in goods:
            c = MinLengthConstraint(m)
            cvt.verify_min_length_constraint(col, c).isTrue()
            c = MaxLengthConstraint(M)
            cvt.verify_max_length_constraint(col, c).isTrue()
        for (col, m, M) in bads:
            c = MinLengthConstraint(m)
            cvt.verify_min_length_constraint(col, c).isFalse()
            if M is not None:
                c = MaxLengthConstraint(M)
                cvt.verify_max_length_constraint(col, c).isFalse()

    def test_verify_tdda_type_constraint(self):
        df = pd.DataFrame({
            'b': [True, False],
            'i': [1, 0],
            'r': [1.0, 1.1],
            's': ['1', 'a'],
            'd': [datetime.datetime(2000,1,1), datetime.datetime(2000,1,2)],

            'bn': [True, None],
            'in': [1, None],
            'rn': [1.1, None],
            'sn': [None, 'a'],
            'dn': [datetime.datetime(2000,1,1), None],
        })
        goods = [
            ('b', 'bool', 'strict'),
            ('i', 'int', 'strict'),
            ('r', 'real', 'strict'),
            ('s', 'string', 'strict'),
            ('d', 'date', 'strict'),

            ('bn', 'bool', 'strict'),
            ('in', 'int', 'sloppy'),  # Fails strict because promoted to real
            ('rn', 'real', 'strict'),
            ('sn', 'string', 'strict'),
            ('dn', 'date', 'strict'),

            ('bn', ['bool', 'string'], 'strict'),   # promotion to object
            ('in', ['int', 'real'], 'strict'),      # promotion to real
            ('rn', ['int', 'real'], 'strict'),      # just a looser constraint
        ]
        bads = [
            ('in', 'int', 'strict'),
            ('b', 'date', 'sloppy'),
            ('i', 'bool', 'sloppy'),
            ('r', 'int', 'sloppy'),
            ('s', 'real', 'sloppy'),
            ('d', 'string', 'sloppy'),

            ('s', ['real', 'int'], 'sloppy'),  # not sloppy enough for this
        ]
        strict_cvt = ConstraintVerificationTester(self, df,
                                                  type_checking='strict')
        sloppy_cvt = ConstraintVerificationTester(self, df,
                                                  type_checking='sloppy')
        for (col, value, strictness) in goods:
            cvt = strict_cvt if strictness == 'strict' else sloppy_cvt
            c = TypeConstraint(value)
            if strictness == 'strict':
                strict_cvt.verify_tdda_type_constraint(col, c).isTrue()
            # Any field that satisfies the strict checker should
            # also satisfy the sloppy checker
            sloppy_cvt.verify_tdda_type_constraint(col, c).isTrue()

        for (col, value, strictness) in bads:
            c = TypeConstraint(value)
            if strictness == 'sloppy':
                sloppy_cvt.verify_tdda_type_constraint(col, c).isFalse()
            # Any field that fails to satisfy the sloppy checker should
            # also fail to satisfy the strict checker
            strict_cvt.verify_tdda_type_constraint(col, c).isFalse()

    def test_verify_tdda_sign_constraint(self):
        df = pd.DataFrame({
            'ipos': [1, 2, 3],
            'inonneg': [0, 1, 2],
            'izero': [0, 0, 0],
            'inonpos': [0, -1, -2],
            'ineg': [-1, -2, -3],
            'imixed': [1,0,-1],

            'rpos': [1.0, 2.0, 3.0],
            'rnonneg': [0.0, 1.0, 1.0],
            'rzero': [0.0, 0.0, 0.0],
            'rnonpos': [0.0, -1.0, -1.0],
            'rneg': [-1.0, -2.0, -3.0],
            'rmixed': [-1.0, 0.0, 1.0],

            'iposn': [1, 2, np.nan],
            'inonnegn': [0, 1, np.nan],
            'izeron': [0, 0, np.nan],
            'inonposn': [0, -1, np.nan],
            'inegn': [-1, -2, np.nan],
            'inmixedn': [-1, 1, np.nan],

            'rposn': [1.0, 2.0, np.nan],
            'rnonnegn': [0.0, 1.0, np.nan],
            'rzeron': [0.0, 0.0, np.nan],
            'rnonposn': [0.0, -1.0, np.nan],
            'rnegn': [-1.0, -2.0, np.nan],
            'rnmixedn': [-1.0, 1.0, np.nan],

            'null': [np.nan, np.nan, np.nan],
        })
        cvt = ConstraintVerificationTester(self, df)
        for col in df:
            pos = SignConstraint('positive')
            nonneg = SignConstraint('non-negative')
            zero = SignConstraint('zero')
            nonpos = SignConstraint('non-positive')
            neg = SignConstraint('negative')
            null = SignConstraint('null')
            if 'nonpos' in col:
                cvt.verify_sign_constraint(col, pos).isFalse()
                cvt.verify_sign_constraint(col, nonneg).isFalse()
                cvt.verify_sign_constraint(col, zero).isFalse()
                cvt.verify_sign_constraint(col, nonpos).isTrue()
                cvt.verify_sign_constraint(col, neg).isFalse()
                cvt.verify_sign_constraint(col, null).isFalse()
            elif 'pos' in col:
                cvt.verify_sign_constraint(col, pos).isTrue()
                cvt.verify_sign_constraint(col, nonneg).isTrue()
                cvt.verify_sign_constraint(col, zero).isFalse()
                cvt.verify_sign_constraint(col, nonpos).isFalse()
                cvt.verify_sign_constraint(col, neg).isFalse()
                cvt.verify_sign_constraint(col, null).isFalse()
            elif 'nonneg' in col:
                cvt.verify_sign_constraint(col, pos).isFalse()
                cvt.verify_sign_constraint(col, nonneg).isTrue()
                cvt.verify_sign_constraint(col, zero).isFalse()
                cvt.verify_sign_constraint(col, nonpos).isFalse()
                cvt.verify_sign_constraint(col, neg).isFalse()
                cvt.verify_sign_constraint(col, null).isFalse()
            elif 'neg' in col:
                cvt.verify_sign_constraint(col, pos).isFalse()
                cvt.verify_sign_constraint(col, nonneg).isFalse()
                cvt.verify_sign_constraint(col, zero).isFalse()
                cvt.verify_sign_constraint(col, nonpos).isTrue()
                cvt.verify_sign_constraint(col, neg).isTrue()
                cvt.verify_sign_constraint(col, null).isFalse()
            elif 'zero' in col:
                cvt.verify_sign_constraint(col, pos).isFalse()
                cvt.verify_sign_constraint(col, nonneg).isTrue()
                cvt.verify_sign_constraint(col, zero).isTrue()
                cvt.verify_sign_constraint(col, nonpos).isTrue()
                cvt.verify_sign_constraint(col, neg).isFalse()
                cvt.verify_sign_constraint(col, null).isFalse()
            elif col == 'null':
                pass
                cvt.verify_sign_constraint(col, pos).isTrue()
                cvt.verify_sign_constraint(col, nonneg).isTrue()
                cvt.verify_sign_constraint(col, zero).isTrue()
                cvt.verify_sign_constraint(col, nonpos).isTrue()
                cvt.verify_sign_constraint(col, neg).isTrue()
                cvt.verify_sign_constraint(col, null).isTrue()
            elif 'mixed' in col:
                cvt.verify_sign_constraint(col, pos).isFalse()
                cvt.verify_sign_constraint(col, nonneg).isFalse()
                cvt.verify_sign_constraint(col, zero).isFalse()
                cvt.verify_sign_constraint(col, nonpos).isFalse()
                cvt.verify_sign_constraint(col, neg).isFalse()
                cvt.verify_sign_constraint(col, null).isFalse()
            else:
                raise Exception('Cannot get here: %s' % col)

    def test_verify_tdda_max_nulls_constraint(self):
        df = pd.DataFrame({
            'b': [True, False],
            'i': [1, -1],
            'r': [1.0, -1.0],
            's': ['a', 'a'],
            'd': [datetime.datetime.now()] * 2,

            'bn': [True, None],
            'in': [1, None],
            'rn': [None, 1.0],
            'sn': [None, 'a'],
            'dn': [datetime.datetime.now(), None],

            'n': [None, None],
        })
        cvt = ConstraintVerificationTester(self, df)
        c = MaxNullsConstraint(0)
        for col in df:
            if col.endswith('n'):
                 cvt.verify_max_nulls_constraint(col, c).isFalse()
            else:
                 cvt.verify_max_nulls_constraint(col, c).isTrue()

    def test_verify_no_duplicates_constraint(self):
        df = pd.DataFrame({
            'bu': [True, False, None, None],  # Note two nulls
            'iu': [1, -1, 0, 2],
            'ru': [1.0, -1.0, 0.0, 3.0],
            'su': ['a', 'b', 'c', ''],
            'du': [datetime.datetime(2000,1,1), datetime.datetime(2000,1,2),
                   datetime.datetime(2000,1,3), datetime.datetime(2000,1,4)],

            'bd': [True, True, False, None],
            'id': [1, 2, 2, 3],
            'rd': [1.0, 2.0, 2.0, 3.0],
            'sd': ['a', 'a', 'a', 'a'],
            'dd': [datetime.datetime(2000,1,1)] * 4,

            'IU': [1, -1, None, None],
            'RU': [1.0, -1.0, None, None],
            'SU': [None, None, 'c', ''],
            'DU': [datetime.datetime(2000,1,1), None,
                   None, datetime.datetime(2000,1,4)],

            'BD': [True, True, False, None],
            'ID': [1, 2, 2, None],
            'RD': [None, 2.0, 2.0, None],
            'SD': ['a', 'a', None, 'b'],
            'DD': [datetime.datetime(2000,1,1)] * 2 + [None] * 2,

            'nu': [None, None, None, None],
        })
        cvt = ConstraintVerificationTester(self, df)
        c = NoDuplicatesConstraint(True)
        for col in df:
            if col.lower().endswith('u'):
                 cvt.verify_no_duplicates_constraint(col, c).isTrue()
            else:
                 cvt.verify_no_duplicates_constraint(col, c).isFalse()

    def test_verify_allowed_values_constraint(self):
        DIGITS = list('1234567890')
        PRIMES = list('2357')
        EMPTIES = ['', ' ', '  ', '   ']
        ANDOR = ['and', 'or']
        df = pd.DataFrame({
            'digits': list('8275'),
            'primes1': PRIMES,
            'primes2': list('3355'),
            'empties': EMPTIES,
            'eitheror': ['and', 'not', 'either', 'or'],

            'digitsn': list('827') + [None],
            'primes1n': PRIMES[:-1] + [np.nan],
            'primes2n': [None, np.nan, '3', '5'],
            'emptiesn': [' ', None, '  ', '   '],
            'eitherorn': ['and', None, 'either', 'or'],

            'null': [None] * 4,
        })
        cvt = ConstraintVerificationTester(self, df)
        c_digits = AllowedValuesConstraint(DIGITS)
        c_primes = AllowedValuesConstraint(PRIMES)
        c_empties = AllowedValuesConstraint(EMPTIES)
        c_andor = AllowedValuesConstraint(ANDOR)
        c_nothing = AllowedValuesConstraint([])

        cvt.verify_allowed_values_constraint('digits', c_digits).isTrue()
        cvt.verify_allowed_values_constraint('digitsn', c_digits).isTrue()
        cvt.verify_allowed_values_constraint('primes1', c_primes).isTrue()
        cvt.verify_allowed_values_constraint('primes1n', c_primes).isTrue()
        cvt.verify_allowed_values_constraint('primes2', c_primes).isTrue()
        cvt.verify_allowed_values_constraint('primes2n', c_primes).isTrue()
        cvt.verify_allowed_values_constraint('primes1', c_digits).isTrue()
        cvt.verify_allowed_values_constraint('primes1n', c_digits).isTrue()
        cvt.verify_allowed_values_constraint('primes2', c_digits).isTrue()
        cvt.verify_allowed_values_constraint('primes2n', c_digits).isTrue()
        cvt.verify_allowed_values_constraint('empties', c_empties).isTrue()
        cvt.verify_allowed_values_constraint('emptiesn', c_empties).isTrue()

        cvt.verify_allowed_values_constraint('eitheror', c_empties).isFalse()
        cvt.verify_allowed_values_constraint('eitherorn', c_empties).isFalse()

        cvt.verify_allowed_values_constraint('digits', c_primes).isFalse()
        cvt.verify_allowed_values_constraint('digitsn', c_primes).isFalse()
        cvt.verify_allowed_values_constraint('primes1', c_empties).isFalse()
        cvt.verify_allowed_values_constraint('primes1n', c_andor).isFalse()
        cvt.verify_allowed_values_constraint('primes2', c_andor).isFalse()
        cvt.verify_allowed_values_constraint('primes2n', c_empties).isFalse()
        cvt.verify_allowed_values_constraint('empties', c_primes).isFalse()
        cvt.verify_allowed_values_constraint('emptiesn', c_digits).isFalse()

        for col in df:
            if col == 'null':
                cvt.verify_allowed_values_constraint(col, c_nothing).isTrue()
            else:
                cvt.verify_allowed_values_constraint(col, c_nothing).isFalse()


class TestPandasMultipleConstraintVerifier(ReferenceTestCase):
    def testFieldVerification(self):
        df1 = pd.DataFrame({
                'b': [True, False] * 2,
                'i': range(1, 5),
                'r': [float(x) for x in range(1, 5)],
                's': ['S%s' % x for x in range(1, 5)],
                'd': [datetime.datetime(2016,1,x) for x in range(1, 5)]
             })
        ic1 = FieldConstraints('i',
                               [TypeConstraint('int'),
                                MinConstraint(0),
                                MaxConstraint(10),
                                SignConstraint('positive'),
                                MaxNullsConstraint(0),
                                NoDuplicatesConstraint()])

        ic2 = FieldConstraints('i',
                               [TypeConstraint('bool'),
                                MinConstraint(2),
                                MaxConstraint(3),
                                SignConstraint('negative'),
                                MaxNullsConstraint(0),
                                NoDuplicatesConstraint()])

        dfc1 = [ic1]
        dsc1 = DatasetConstraints(dfc1)
        pdcv1 = pdc.PandasConstraintVerifier(df1)
        results1 = verify(dsc1, list(df1), pdcv1.verifiers())
        expected = ('FIELDS:\n\n'
                    'i: 0 failures  6 passes  '
                    'type ✓  min ✓  max ✓  sign ✓  '
                    'max_nulls ✓  no_duplicates ✓\n\n'
                    'SUMMARY:\n\nConstraints passing: 6\nConstraints failing: 0')
        self.assertEqual(str(results1), expected)
        expected = pd.DataFrame(OrderedDict((
                        ('field', ['i']),
                        ('failures', [0]),
                        ('passes', [6]),
                        ('type', [True]),
                        ('min', [True]),
                        ('max', [True]),
                        ('sign', [True]),
                        ('max_nulls', [True]),
                        ('no_duplicates', [True]),
                        )))
        vdf = pdc.PandasVerification.verification_to_dataframe(results1)
        self.assertTrue(vdf.equals(expected))

        df2 = pd.DataFrame({'i': [1, 2, 2, 6, np.nan]})
        dfc2 = [ic2]
        dsc2 = DatasetConstraints(dfc2)
        pdcv2 = pdc.PandasConstraintVerifier(df2)
        results2 = verify(dsc2, list(df2), pdcv2.verifiers())
        # expect the boolean->real type constraint to pass with sloppy types
        expected = ('FIELDS:\n\n'
                    'i: 5 failures  1 pass  '
                    'type ✓  min ✗  max ✗  sign ✗  '
                    'max_nulls ✗  no_duplicates ✗\n\n'
                    'SUMMARY:\n\nConstraints passing: 1\nConstraints failing: 5')
        self.assertEqual(str(results2), expected)
        expected = pd.DataFrame(OrderedDict((
                        ('field', ['i']),
                        ('failures', [5]),
                        ('passes', [1]),
                        ('type', [True]),
                        ('min', [False]),
                        ('max', [False]),
                        ('sign', [False]),
                        ('max_nulls', [False]),
                        ('no_duplicates', [False]),
                        )))
        vdf = pdc.PandasVerification.verification_to_dataframe(results2)
        self.assertTrue(vdf.equals(expected))

        pdcv2strict = pdc.PandasConstraintVerifier(df2, type_checking='strict')
        results2strict = verify(dsc2, list(df2), pdcv2strict.verifiers())
        # expect the boolean->real type constraint to fail with strict types
        expected = ('FIELDS:\n\n'
                    'i: 6 failures  0 passes  '
                    'type ✗  min ✗  max ✗  sign ✗  '
                    'max_nulls ✗  no_duplicates ✗\n\n'
                    'SUMMARY:\n\nConstraints passing: 0\nConstraints failing: 6')
        self.assertEqual(str(results2strict), expected)
        expected = pd.DataFrame(OrderedDict((
                        ('field', ['i']),
                        ('failures', [6]),
                        ('passes', [0]),
                        ('type', [False]),
                        ('min', [False]),
                        ('max', [False]),
                        ('sign', [False]),
                        ('max_nulls', [False]),
                        ('no_duplicates', [False]),
                        )))
        vdf = pdc.PandasVerification.verification_to_dataframe(results2strict)
        self.assertTrue(vdf.equals(expected))

        ic3 = FieldConstraints('i', [TypeConstraint('int')])
        df3 = df1
        dfc3 = [ic3]
        dsc3 = DatasetConstraints(dfc3)
        pdcv3 = pdc.PandasConstraintVerifier(df3)
        results3 = verify(dsc3, list(df3), pdcv3.verifiers())
        expected = ('FIELDS:\n\n'
                    'i: 0 failures  1 pass  type ✓\n\n'
                    'SUMMARY:\n\nConstraints passing: 1\nConstraints failing: 0')
        self.assertEqual(str(results3), expected)
        expected = pd.DataFrame(OrderedDict((
                        ('field', ['i']),
                        ('failures', [0]),
                        ('passes', [1]),
                        ('type', [True]),
                   )))
        vdf = pdc.PandasVerification.verification_to_dataframe(results3)
        self.assertTrue(vdf.equals(expected))

        pdcv3 = pdc.PandasConstraintVerifier(df3)
        results3 = verify(dsc3, list(df3), pdcv3.verifiers(), ascii=True)
        expected = ('FIELDS:\n\n'
                    'i: 0 failures  1 pass  type OK\n\n'
                    'SUMMARY:\n\nConstraints passing: 1\nConstraints failing: 0')
        self.assertEqual(str(results3), expected)

    def testElements92(self):
        csv_path = os.path.join(TESTDATA_DIR, 'elements92.csv')
        df = pd.read_csv(csv_path)
        constraints_path = os.path.join(TESTDATA_DIR, 'elements92.tdda')
        v = verify_df(df, constraints_path)
        self.assertEqual(v.passes, 72)
        self.assertEqual(v.failures, 0)

    def testElements92rex(self):
        csv_path = os.path.join(TESTDATA_DIR, 'elements92.csv')
        df = pd.read_csv(csv_path)
        constraints_path = os.path.join(TESTDATA_DIR, 'elements92rex.tdda')
        v = verify_df(df, constraints_path)
        self.assertEqual(v.passes, 78)
        self.assertEqual(v.failures, 0)

    def testElements118(self):
        csv_path = os.path.join(TESTDATA_DIR, 'elements118.csv')
        df = pd.read_csv(csv_path)
        constraints_path = os.path.join(TESTDATA_DIR, 'elements92.tdda')
        v = verify_df(df, constraints_path, report='fields')
        self.assertEqual(v.passes, 57)
        self.assertEqual(v.failures, 15)
        vdf = v.to_dataframe()
        vdf.sort_values('field', inplace=True)
        self.assertStringCorrect(vdf.to_string(), 'elements118.df')

    def testElements118rex(self):
        csv_path = os.path.join(TESTDATA_DIR, 'elements118.csv')
        df = pd.read_csv(csv_path)
        constraints_path = os.path.join(TESTDATA_DIR, 'elements92rex.tdda')
        v = verify_df(df, constraints_path, report='fields')
        self.assertEqual(v.passes, 61)
        self.assertEqual(v.failures, 17)
        vdf = v.to_dataframe()
        vdf.sort_values('field', inplace=True)
        self.assertStringCorrect(vdf.to_string(), 'elements118rex.df')


class TestPandasDataFrameConstraints(ReferenceTestCase):
    def testDDD_df(self):
        csv_path = os.path.join(TESTDATA_DIR, 'ddd.csv')
        df = pd.read_csv(csv_path)
        constraints_path = os.path.join(TESTDATA_DIR, 'ddd.tdda')
        v = verify_df(df, constraints_path)
        # expect 3 failures:
        #   - the pandas CSV reader will have read 'elevens' as an int
        #   - the pandas CSV reader will have read the date columns as strings
        self.assertEqual(v.passes, 58)
        self.assertEqual(v.failures, 3)

    def testDDD_csv(self):
        csv_path = os.path.join(TESTDATA_DIR, 'ddd.csv')
        constraints_path = os.path.join(TESTDATA_DIR, 'ddd.tdda')
        v = verify_df_from_file(csv_path, constraints_path, verbose=False)
        # expect 1 failure:
        #   - the enhanced CSV reader will have initially read 'elevens' as
        #     an int field and then (correctly) converted it to string, but
        #     it doesn't know that it would need to pad with initial zeros,
        #     so that means it will have computed its minimum as being '0'
        #     not '00', so the minimum string length won't be the same as
        #     Miro would compute (since Miro has the advantage of having
        #     additional metadata available when it read the CSV file, to
        #     tell it that 'elevens' is a string field.
        self.assertEqual(v.passes, 60)
        self.assertEqual(v.failures, 1)

    def testDDD_discover_and_verify(self):
        # both discovery and verification done using Pandas
        csv_path = os.path.join(TESTDATA_DIR, 'ddd.csv')
        c = discover_df_from_file(csv_path, constraints_path=None,
                                  verbose=False)
        tmpdir = tempfile.gettempdir()
        tmpfile = os.path.join(tmpdir, 'dddtestconstraints.tdda')
        with open(tmpfile, 'w') as f:
            f.write(c)
        v = verify_df_from_file(csv_path, tmpfile, report='fields',
                                verbose=False)
        self.assertEqual(v.passes, 61)
        self.assertEqual(v.failures, 0)

    def testDDD_df(self):
        csv_path = os.path.join(TESTDATA_DIR, 'ddd.csv')
        df = pd.read_csv(csv_path)
        constraints_path = os.path.join(TESTDATA_DIR, 'ddd.tdda')
        v = verify_df(df, constraints_path)
        # expect 3 failures:
        #   - the pandas CSV reader will have read 'elevens' as an int
        #   - the pandas CSV reader will have read the date columns as strings
        self.assertEqual(v.passes, 58)
        self.assertEqual(v.failures, 3)

    def testDDD_csv(self):
        csv_path = os.path.join(TESTDATA_DIR, 'ddd.csv')
        constraints_path = os.path.join(TESTDATA_DIR, 'ddd.tdda')
        v = verify_df_from_file(csv_path, constraints_path, verbose=False)
        # expect 1 failure:
        #   - the enhanced CSV reader will have initially read 'elevens' as
        #     an int field and then (correctly) converted it to string, but
        #     it doesn't know that it would need to pad with initial zeros,
        #     so that means it will have computed its minimum as being '0'
        #     not '00', so the minimum string length won't be the same as
        #     Miro would compute (since Miro has the advantage of having
        #     additional metadata available when it read the CSV file, to
        #     tell it that 'elevens' is a string field.
        self.assertEqual(v.passes, 60)
        self.assertEqual(v.failures, 1)

    def testDDD_discover_and_verify(self):
        # both discovery and verification done using Pandas
        csv_path = os.path.join(TESTDATA_DIR, 'ddd.csv')
        c = discover_df_from_file(csv_path, constraints_path=None,
                                  verbose=False)
        tmpdir = tempfile.gettempdir()
        tmpfile = os.path.join(tmpdir, 'dddtestconstraints.tdda')
        with open(tmpfile, 'w') as f:
            f.write(c)
        v = verify_df_from_file(csv_path, tmpfile, report='fields',
                                verbose=False)
        self.assertEqual(v.passes, 61)
        self.assertEqual(v.failures, 0)

    def testDDD_df(self):
        csv_path = os.path.join(TESTDATA_DIR, 'ddd.csv')
        df = pd.read_csv(csv_path)
        constraints_path = os.path.join(TESTDATA_DIR, 'ddd.tdda')
        v = verify_df(df, constraints_path)
        # expect 3 failures:
        #   - the pandas CSV reader will have read 'elevens' as an int
        #   - the pandas CSV reader will have read the date columns as strings
        self.assertEqual(v.passes, 58)
        self.assertEqual(v.failures, 3)

    def testDDD_csv(self):
        csv_path = os.path.join(TESTDATA_DIR, 'ddd.csv')
        constraints_path = os.path.join(TESTDATA_DIR, 'ddd.tdda')
        v = verify_df_from_file(csv_path, constraints_path, verbose=False)
        # expect 1 failure:
        #   - the enhanced CSV reader will have initially read 'elevens' as
        #     an int field and then (correctly) converted it to string, but
        #     it doesn't know that it would need to pad with initial zeros,
        #     so that means it will have computed its minimum as being '0'
        #     not '00', so the minimum string length won't be the same as
        #     Miro would compute (since Miro has the advantage of having
        #     additional metadata available when it read the CSV file, to
        #     tell it that 'elevens' is a string field.
        self.assertEqual(v.passes, 60)
        self.assertEqual(v.failures, 1)

    def testDDD_discover_and_verify(self):
        # both discovery and verification done using Pandas
        csv_path = os.path.join(TESTDATA_DIR, 'ddd.csv')
        c = discover_df_from_file(csv_path, constraints_path=None,
                                  verbose=False)
        tmpdir = tempfile.gettempdir()
        tmpfile = os.path.join(tmpdir, 'dddtestconstraints.tdda')
        with open(tmpfile, 'w') as f:
            f.write(c)
        v = verify_df_from_file(csv_path, tmpfile, report='fields',
                                verbose=False)
        self.assertEqual(v.passes, 61)
        self.assertEqual(v.failures, 0)


class TestPandasMultipleConstraintDetector(ReferenceTestCase):
    def testDetectElements118rexToFile(self):
        csv_path = os.path.join(TESTDATA_DIR, 'elements118.csv')
        df = pd.read_csv(csv_path)
        constraints_path = os.path.join(TESTDATA_DIR, 'elements92rex.tdda')
        detectfile = os.path.join(self.tmp_dir, 'elements118rex_detect.csv')
        v = detect_df(df, constraints_path, report='fields',
                      outpath=detectfile, output_fields=['Z'],
                      rowindex_is_index=False)
        self.assertEqual(v.passes, 61)
        self.assertEqual(v.failures, 17)
        self.assertFileCorrect(detectfile, 'elements118rex_detect.csv')

    def testDetectElements118rexToFilePerConstraint(self):
        csv_path = os.path.join(TESTDATA_DIR, 'elements118.csv')
        df = pd.read_csv(csv_path)
        constraints_path = os.path.join(TESTDATA_DIR, 'elements92rex.tdda')
        detectfile = os.path.join(self.tmp_dir,
                                  'elements118rex_detect_perc.csv')
        v = detect_df(df, constraints_path, report='fields',
                      outpath=detectfile, output_fields=['Z'],
                      per_constraint=True, rowindex_is_index=False)
        self.assertEqual(v.passes, 61)
        self.assertEqual(v.failures, 17)
        self.assertFileCorrect(detectfile, 'elements118rex_detect_perc.csv')

    def testDetectElements118rexToDataFrame(self):
        csv_path = os.path.join(TESTDATA_DIR, 'elements118.csv')
        df = pd.read_csv(csv_path)
        constraints_path = os.path.join(TESTDATA_DIR, 'elements92rex.tdda')
        v = detect_df(df, constraints_path, output_fields=['Z'],
                      rowindex_is_index=False)
        self.assertEqual(v.passes, 61)
        self.assertEqual(v.failures, 17)
        ddf = v.detected()
        self.assertStringCorrect(ddf.to_string(), 'elements118rex_detect.df')

    def testDetectElements118_csv_to_csv(self):
        self.detectElements('csv', 'csv')

    def testDetectElements118_csv_to_feather(self):
        self.detectElements('csv', 'feather')

    def testDetectElements118_feather_to_csv(self):
        self.detectElements('feather', 'csv')

    def testDetectElements118_feather_to_feather(self):
        self.detectElements('feather', 'feather')

    def detectElements(self, input, output):
        csv_path = os.path.join(TESTDATA_DIR, 'elements118.%s' % input)
        df = load_df(csv_path)
        constraints_path = os.path.join(TESTDATA_DIR, 'elements92.tdda')
        detect_name = 'elements118_detect_from_%s.%s' % (input, output)
        detectfile = os.path.join(self.tmp_dir, detect_name)
        v = detect_df(df, constraints_path, report='fields',
                      outpath=detectfile, output_fields=['Z'],
                      per_constraint=True, index=True,
                      rownumber_is_index=(input == 'feather'))
        self.assertEqual(v.detection.n_passing_records, 91)
        self.assertEqual(v.detection.n_failing_records, 27)
        if output == 'feather':
            # TODO: compare binary feather files and check they're the same
            pass
        else:
            self.assertFileCorrect(detectfile, detect_name)

    def testDetectDuplicates(self):
        iconstraints = FieldConstraints('i', [NoDuplicatesConstraint()])
        sconstraints = FieldConstraints('s', [NoDuplicatesConstraint()])
        constraints = DatasetConstraints([iconstraints, sconstraints])

        df1 = pd.DataFrame({'i': [1, 2, 3, 4, np.nan],
                            's': ['one', 'two', 'three', 'four', np.nan]})
        verifier1 = pdc.PandasConstraintVerifier(df1)
        v1 = verifier1.detect(constraints,
                              VerificationClass=pdc.PandasDetection)
        self.assertEqual(v1.passes, 2)
        self.assertEqual(v1.failures, 0)
        ddf1 = v1.detected()
        self.assertIsNone(ddf1)

        df2 = pd.DataFrame({'i': [1, 2, 3, 2, np.nan],
                            's': ['one', 'two', 'three', 'two', np.nan]})
        verifier2 = pdc.PandasConstraintVerifier(df2)
        v2 = verifier2.detect(constraints,
                              VerificationClass=pdc.PandasDetection,
                              per_constraint=True, output_fields=['i', 's'])
        self.assertEqual(v2.passes, 0)
        self.assertEqual(v2.failures, 2)
        ddf2 = v2.detected()
        self.assertStringCorrect(ddf2.to_string(), 'detect_dups.df')


class TestPandasMultipleConstraintGeneration(ReferenceTestCase):
    def testConstraintGenerationNoRex(self):
        self.constraintsGenerationTest(inc_rex=False)

    def testConstraintGenerationWithRex(self):
        self.constraintsGenerationTest(inc_rex=True)

    def constraintsGenerationTest(self, inc_rex=False):
        csv_path = os.path.join(TESTDATA_DIR, 'elements92.csv')
        df = pd.read_csv(csv_path)
        ref_name = 'elements92%s.tdda' % ('rex' if inc_rex else '')
        ref_constraints_path = os.path.join(TESTDATA_DIR, ref_name)
        with open(ref_constraints_path) as f:
            refjson = f.read()
        ref = native_definite(json.loads(refjson))
        constraints = discover_df(df, inc_rex=inc_rex)
        discovered = native_definite(json.loads(constraints.to_json()))
        discovered_fields = discovered['fields']
        ref_fields = ref['fields']
        self.assertEqual(set(discovered_fields.keys()),
                         set(ref_fields.keys()))
        for field, ref_field in ref_fields.items():
            ref_field = ref_fields[field]
            discovered_field = discovered_fields[field]
            self.assertEqual((field, set(discovered_field.keys())),
                             (field, set(ref_field.keys())))
            for c, expected in ref_field.items():
                actual = discovered_field[c]
                if type(expected) == float:
                    self.assertAlmostEqual(actual, expected, 4)
                elif type(expected) == list:
                    self.assertEqual(set(actual), set(expected))
                elif expected in ('int', 'real'):  # pandas too broken to
                                                   # get this right for now
                    self.assertTrue(actual in ('int', 'real'))
                else:
                    self.assertEqual(actual, expected)


class CommandLineHelper:
    @classmethod
    def setUpHelper(cls):
        cls.test_tmpdir = tempfile.gettempdir()
        cls.test_dirs = ['referencetest_examples', 'constraints_examples',
                         'rexpy_examples']
        cls.constraintsdir = os.path.abspath(os.path.dirname(__file__))
        cls.tddaTopDir = os.path.dirname(os.path.dirname(cls.constraintsdir))
        cls.testDataDir = os.path.join(cls.test_tmpdir,
                                       'constraints_examples', 'testdata')

        cls.e92csv = os.path.join(cls.testDataDir, 'elements92.csv')
        cls.e118csv = os.path.join(cls.testDataDir, 'elements118.csv')
        cls.e118feather = os.path.join(cls.testDataDir, 'elements118.feather')
        cls.e92tdda_correct = os.path.join(cls.testDataDir, 'elements92.tdda')
        cls.dddcsv = os.path.join(cls.testDataDir, 'ddd.csv')
        cls.dddtdda_correct = os.path.join(cls.testDataDir, 'ddd.tdda')

        cls.e92tdda = os.path.join(cls.test_tmpdir, 'elements92.tdda')
        cls.e92bads1 = os.path.join(cls.test_tmpdir, 'elements92bads1.csv')
        cls.e92bads2 = os.path.join(cls.test_tmpdir, 'elements92bads2.csv')

        argv = ['tdda', 'examples', cls.test_tmpdir]
        cls.execute_command(argv)

    @classmethod
    def tearDownHelper(cls):
        rmdirs(cls.test_tmpdir, cls.test_dirs)

    def testDiscoverCmd(self):
        argv = ['tdda', 'discover', self.e92csv, self.e92tdda]
        self.execute_command(argv)
        self.assertFileCorrect(self.e92tdda, 'elements92_pandas.tdda',
                               rstrip=True,
                               ignore_substrings=[
                                   '"as_at":', '"local_time":', '"utc_time":',
                                   '"source":', '"host":', '"user":',
                                   '"tddafile":',
                               ])
        os.remove(self.e92tdda)

    def testVerifyE92Cmd(self):
        argv = ['tdda', 'verify', self.e92csv, self.e92tdda_correct]
        result = self.execute_command(argv)
        self.assertTrue(result.strip().endswith('SUMMARY:\n\n'
                                                'Constraints passing: 72\n'
                                                'Constraints failing: 0'))

    def testVerifyE118Cmd(self):
        argv = ['tdda', 'verify', self.e118csv, self.e92tdda_correct]
        result = self.execute_command(argv)
        self.assertTrue(result.strip().endswith('SUMMARY:\n\n'
                                                'Constraints passing: 57\n'
                                                'Constraints failing: 15'))

    def testVerifyOptionFlags(self):
        argv = ['tdda', 'verify', self.e92csv, self.e92tdda_correct]
        result = self.execute_command(argv)
        self.assertEqual(len(result.splitlines()), 38)
        self.assertTrue('✓' in result)
        self.assertFalse('OK' in result)

        argv = ['tdda', 'verify', self.e92csv, self.e92tdda_correct,
                '--ascii']
        result = self.execute_command(argv)
        self.assertEqual(len(result.splitlines()), 38)
        self.assertTrue('OK' in result)

        argv = ['tdda', 'verify', self.e92csv, self.e92tdda_correct,
                '--fields']
        result = self.execute_command(argv)
        self.assertEqual(len(result.splitlines()), 4)

        argv = ['tdda', 'verify', self.e92csv, self.e92tdda_correct,
                '--all']
        result = self.execute_command(argv)
        self.assertEqual(len(result.splitlines()), 38)

        argv = ['tdda', 'verify', self.dddcsv, self.dddtdda_correct,
                '--fields', '--type_checking', 'strict']
        result = self.execute_command(argv)
        # 5 type-failures (plus min_length on elevens, considered as an int)
        self.assertTrue(result.strip().endswith('SUMMARY:\n\n'
                                                'Constraints passing: 55\n'
                                                'Constraints failing: 6'))

        argv = ['tdda', 'verify', self.dddcsv, self.dddtdda_correct,
                '--fields', '--type_checking', 'sloppy']
        result = self.execute_command(argv)
        # 1 failure, because elevens is treated as an int, so min_length fails
        self.assertTrue(result.strip().endswith('SUMMARY:\n\n'
                                                'Constraints passing: 60\n'
                                                'Constraints failing: 1'))

    def testVerifyEpsilon(self):
        argv = ['tdda', 'verify', self.e118csv, self.e92tdda_correct,
                '--fields']
        result = self.execute_command(argv)
        self.assertTrue(result.strip().endswith('SUMMARY:\n\n'
                                                'Constraints passing: 57\n'
                                                'Constraints failing: 15'))

        argv = ['tdda', 'verify', self.e118csv, self.e92tdda_correct,
                '--fields', '--epsilon', '0.5']
        result = self.execute_command(argv)
        # a few fewer failures, because of epsilon
        self.assertTrue(result.strip().endswith('SUMMARY:\n\n'
                                                'Constraints passing: 60\n'
                                                'Constraints failing: 12'))

        argv = ['tdda', 'verify', self.e118csv, self.e92tdda_correct,
                '--fields', '--epsilon', '10']
        result = self.execute_command(argv)
        # even fewer failures, because of massive epsilon
        self.assertTrue(result.strip().endswith('SUMMARY:\n\n'
                                                'Constraints passing: 61\n'
                                                'Constraints failing: 11'))

    def testDetectE118Cmd(self):
        argv = ['tdda', 'detect', self.e118csv, self.e92tdda_correct,
                self.e92bads1, '--per-constraint', '--output-fields',
                '--index']
        result = self.execute_command(argv)
        self.assertTrue(result.strip().endswith('SUMMARY:\n\n'
                                                'Records passing: 91\n'
                                                'Records failing: 27'))
        self.assertTrue(os.path.exists(self.e92bads1))
        self.assertFileCorrect(self.e92bads1, 'detect-els-cmdline.csv')
        os.remove(self.e92bads1)

    def testDetectE118FeatherCmd(self):
        argv = ['tdda', 'detect', self.e118feather, self.e92tdda_correct,
                self.e92bads2, '--per-constraint', '--output-fields',
                '--index']
        result = self.execute_command(argv)
        self.assertTrue(result.strip().endswith('SUMMARY:\n\n'
                                                'Records passing: 91\n'
                                                'Records failing: 27'))
        self.assertTrue(os.path.exists(self.e92bads2))
        self.assertFileCorrect(self.e92bads2, 'detect-els-cmdline2.csv')
        os.remove(self.e92bads2)


class TestPandasCommandAPI(ReferenceTestCase, CommandLineHelper):
    @classmethod
    def setUpClass(cls):
        cls.setUpHelper()

    @classmethod
    def tearDownClass(cls):
        cls.tearDownHelper()

    @classmethod
    def execute_command(self, argv):
        return str(main_with_argv(argv, verbose=False))


@unittest.skipIf(find_executable('tdda') is None, 'tdda not installed')
class TestPandasCommandLine(ReferenceTestCase, CommandLineHelper):
    @classmethod
    def setUpClass(cls):
        cls.setUpHelper()

    @classmethod
    def tearDownClass(cls):
        cls.tearDownHelper()

    @classmethod
    def execute_command(self, argv):
        return check_shell_output(argv)


TestPandasMultipleConstraintVerifier.set_default_data_location(TESTDATA_DIR)
TestPandasMultipleConstraintDetector.set_default_data_location(TESTDATA_DIR)
TestPandasCommandLine.set_default_data_location(TESTDATA_DIR)
TestPandasCommandAPI.set_default_data_location(TESTDATA_DIR)


def rmdirs(parent, dirs):
    for d in dirs:
        shutil.rmtree(os.path.join(parent, d), ignore_errors=True)


def check_shell_output(args):
    result = subprocess.check_output(UTF8DefiniteObject(args))
    return native_definite(result).replace('\r', '')


if __name__ == '__main__':
    ReferenceTestCase.main()

