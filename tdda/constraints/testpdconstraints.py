# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import datetime
import json
import math
import os
import time
import sys
import unittest

from collections import OrderedDict

import pandas as pd
import numpy as np

from tdda.constraints import pdconstraints as pdc
from tdda.constraints.pdconstraints import verify_df, discover_constraints
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
    sanitize,
)

isPython2 = sys.version_info.major < 3

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


TESTDATA_DIR = os.path.join(os.path.split(os.path.abspath(__file__))[0],
                            'testdata')


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



class TestPandasConstraintVerifiers(unittest.TestCase):

    @classmethod
    def tearDownClass(cls):
        assert ConstraintVerificationTester.outstandingAssertions == 0

    def test_tdda_types_of_base_types(self):
        self.assertEqual(pdc.tdda_type(None), 'null')
        for v in BOOLS:
            self.assertEqual(pdc.tdda_type(v), 'bool')
        for v in INTS:
            self.assertEqual(pdc.tdda_type(v), 'int')
        for v in REALS:
            self.assertEqual(pdc.tdda_type(v), 'real')
        for v in STRINGS:
            self.assertEqual(pdc.tdda_type(v), 'string')
        for v in DATES:
            self.assertEqual(pdc.tdda_type(v), 'date')
        for v in OTHERS:
            self.assertEqual(pdc.tdda_type(v), 'other')

    def test_coarse_types_of_base_types(self):
        self.assertEqual(pdc.tdda_type(None), 'null')
        for v in BOOLS:
            self.assertEqual(pdc.coarse_type(v), 'number')
        for v in INTS:
            self.assertEqual(pdc.coarse_type(v), 'number')
        for v in REALS:
            self.assertEqual(pdc.coarse_type(v), 'number')
        for v in STRINGS:
            self.assertEqual(pdc.coarse_type(v), 'string')
        for v in DATES:
            self.assertEqual(pdc.coarse_type(v), 'date')
        for v in OTHERS:
            self.assertEqual(pdc.coarse_type(v), 'other')

    def test_compatibility(self):
        for kind in (NUMBERS, STRINGS, DATES):
            x = kind[0]
            y = kind[-1]
            self.assertTrue(pdc.types_compatible(x, y))
            self.assertTrue(pdc.types_compatible(x, x))

    def test_incompatibility(self):
        for X in (NUMBERS, STRINGS, DATES, OTHERS, NULLS):
            for Y in (NUMBERS, STRINGS, DATES, OTHERS, NULLS):
                if X is not Y:
                    self.assertFalse(pdc.types_compatible(X[0], Y[0]))
                    self.assertFalse(pdc.types_compatible(Y[0], X[0]))

    def test_fuzzy_less_than_zero(self):
        verifier = pdc.PandasConstraintVerifier(df=None)
        for x in NEG_REALS:
            self.assertTrue(verifier.fuzzy_less_than(x, 0.0))
            self.assertFalse(verifier.fuzzy_less_than(0.0, x))
        for x in POS_REALS:
            self.assertFalse(verifier.fuzzy_less_than(x, 0.0))
            self.assertTrue(verifier.fuzzy_less_than(0.0, x))

        self.assertTrue(verifier.fuzzy_less_than(0.0, 0.0))
        self.assertTrue(verifier.fuzzy_less_than(0.0, SMALL / 2))  # == 0.0
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
        for (x, y) in goods + bad_goods:
            cvt.fuzzy_less_than(x, y).isTrue()
        for (x, y) in bads:
            cvt.fuzzy_less_than(x, y).isFalse()

    def test_fuzzy_greater_than_zero(self):
        cvt = ConstraintVerificationTester(self, df=None)
        for x in POS_REALS:
            cvt.fuzzy_greater_than(x, 0.0).isTrue()
            cvt.fuzzy_greater_than(0.0, x).isFalse()
        for x in NEG_REALS:
            cvt.fuzzy_greater_than(x, 0.0).isFalse()
            cvt.fuzzy_greater_than(0.0, x).isTrue()

        cvt.fuzzy_greater_than(0.0, 0.0).isTrue()
        cvt.fuzzy_greater_than(0.0, SMALL / 2).isTrue()  # == 0.0
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
        for (x, y) in goods + bad_goods:
            cvt.fuzzy_greater_than(x, y).isTrue()
        for (x, y) in bads:
            cvt.fuzzy_greater_than(x, y).isFalse()

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
            'one': ['a', 'b', 'c', None],
            'oneTwo': ['a', 'aa', 'bb', None],
            'two': ['aa', 'aa', 'bb', 'bb'],
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

            ('bn', 'bool', 'sloppy'), # Fails strict because promoted to object
            ('in', 'int', 'sloppy'),  # Fails strict because promoted to real
            ('rn', 'real', 'strict'),
            ('sn', 'string', 'strict'),
            ('dn', 'date', 'strict'),

            ('bn', ['bool', 'string'], 'strict'),   # promotion to object
            ('in', ['int', 'real'], 'strict'),      # promotion to real
            ('rn', ['int', 'real'], 'strict'),      # just a looser constraint
        ]
        bads = [
            ('bn', 'bool', 'strict'),
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
        results1 = verify(dsc1, pdcv1.verifiers())
        expected = ('FIELDS:\n\n'
                    'i: 0 failures  6 passes  '
                    'type ✓  min ✓  max ✓  sign ✓  '
                    'max_nulls ✓  no_duplicates ✓\n\n'
                    'SUMMARY:\n\nPasses: 6\nFailures: 0')
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
        self.assertTrue(pdc.verification_to_dataframe(results1)
                           .equals(expected))

        df2 = pd.DataFrame({'i': [1, 2, 2, 6, np.nan]})
        dfc2 = [ic2]
        dsc2 = DatasetConstraints(dfc2)
        pdcv2 = pdc.PandasConstraintVerifier(df2)
        results2 = verify(dsc2, pdcv2.verifiers())
        expected = ('FIELDS:\n\n'
                    'i: 6 failures  0 passes  '
                    'type ✗  min ✗  max ✗  sign ✗  '
                    'max_nulls ✗  no_duplicates ✗\n\n'
                    'SUMMARY:\n\nPasses: 0\nFailures: 6')
        self.assertEqual(str(results2), expected)
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
        self.assertTrue(pdc.verification_to_dataframe(results2)
                           .equals(expected))

        ic3 = FieldConstraints('i', [TypeConstraint('int')])
        df3 = df1
        dfc3 = [ic3]
        dsc3 = DatasetConstraints(dfc3)
        pdcv3 = pdc.PandasConstraintVerifier(df3)
        results3 = verify(dsc3, pdcv3.verifiers())
        expected = ('FIELDS:\n\n'
                    'i: 0 failures  1 pass  type ✓\n\n'
                    'SUMMARY:\n\nPasses: 1\nFailures: 0')
        self.assertEqual(str(results3), expected)
        expected = pd.DataFrame(OrderedDict((
                        ('field', ['i']),
                        ('failures', [0]),
                        ('passes', [1]),
                        ('type', [True]),
                   )))
        self.assertTrue(pdc.verification_to_dataframe(results3)
                           .equals(expected))

    def testElements92(self):
        csv_path = os.path.join(TESTDATA_DIR, 'elements92.csv')
        df = pd.read_csv(csv_path)
        constraints_path = os.path.join(TESTDATA_DIR, 'elements92.tdda')
        v = verify_df(df, constraints_path)
        self.assertEqual(v.passes, 72)
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
        # Check dataframe!

    def testConstraintGeneration(self):
        csv_path = os.path.join(TESTDATA_DIR, 'elements92.csv')
        df = pd.read_csv(csv_path)
        ref_constraints_path = os.path.join(TESTDATA_DIR, 'elements92.tdda')
        with open(ref_constraints_path) as f:
            refjson = f.read()
        ref = sanitize(json.loads(refjson))
        constraints = discover_constraints(df)
        discovered = sanitize(json.loads(constraints.to_json()))
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


if __name__ == '__main__':
    unittest.main()
