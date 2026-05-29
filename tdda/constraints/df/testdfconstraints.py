# -*- coding: utf-8 -*-

"""
Test Suite — individual constraint verifier and utility function tests.

The bulk of the DataFrame constraint tests have been split out into:
  testpdconstraints.py  — concrete pandas classes
  testplconstraints.py  — concrete polars classes
with shared mixin bases in dftestbase.py.
"""

import datetime
import math
import time

import numpy as np
import pandas as pd

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
    fuzzy_less_than,
    fuzzy_greater_than,
)

from tdda.constraints.df import constraints as dfc

from tdda.referencetest import ReferenceTestCase
from tdda.referencetest.pddates import infer_date_format


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
DATES = (
    datetime.datetime(1970, 1, 1),
    datetime.datetime(1, 1, 1),
    datetime.datetime(9999, 12, 31, 23, 59, 59),
    datetime.datetime.now(),
    datetime.datetime.now(datetime.timezone.utc),
)
OTHERS = (3 + 4j, lambda x: 1, [], (), {}, Exception) + ((b'u',))


class ConstraintVerificationTester:
    """
    Delegate class for checking constraint verifications.

    This exists so that when there are test failures,
    useful information about failing inputs and outputs can be shown.
    """

    outstandingAssertions = 0

    def __init__(self, tester, *args, **kwargs):
        self.tester = tester
        self.verifier = dfc.DFConstraintVerifier(*args, **kwargs)

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
    """ """

    def __init__(self, cvt, satisfied, method, args, kwargs):
        self.cvt = cvt
        self.satisfied = satisfied
        self.method = method
        self.args = args
        self.kwargs = kwargs

    def isTrue(self):
        self.cvt.decOutstanding()
        v = getattr(self.satisfied, 'ok', self.satisfied)
        self.cvt.tester.assertTrue(v, self.diagnostic(True))

    def isFalse(self):
        self.cvt.decOutstanding()
        v = getattr(self.satisfied, 'ok', self.satisfied)
        self.cvt.tester.assertFalse(v, self.diagnostic(False))

    def diagnostic(self, expected):
        return 'Verifier: %s Inputs: %s %s: Assertion: %s' % (
            self.method,
            str(self.args),
            str(self.kwargs) if self.kwargs else '',
            'satisified'
            if expected is True
            else 'not satisfied'
            if expected is False
            else expected,
        )


class TestPandasIndividualConstraintVerifier(ReferenceTestCase):
    @classmethod
    def tearDownClass(cls):
        assert ConstraintVerificationTester.outstandingAssertions == 0

    def test_tdda_types_of_base_types(self):
        self.assertEqual(dfc.scalar_to_tdda_type(None), 'null')
        for v in BOOLS:
            self.assertEqual(dfc.scalar_to_tdda_type(v), 'bool')
        for v in INTS:
            self.assertEqual(dfc.scalar_to_tdda_type(v), 'int')
        for v in REALS:
            self.assertEqual(dfc.scalar_to_tdda_type(v), 'real')
        for v in STRINGS:
            self.assertEqual(dfc.scalar_to_tdda_type(v), 'string')
        for v in DATES:
            self.assertEqual(dfc.scalar_to_tdda_type(v), 'date')
        for v in OTHERS:
            self.assertEqual(dfc.scalar_to_tdda_type(v), 'other')

    def test_coarse_types_of_base_types(self):
        self.assertEqual(dfc.scalar_to_tdda_type(None), 'null')
        for v in BOOLS:
            self.assertEqual(dfc.coarse_type(v), 'number')
        for v in INTS:
            self.assertEqual(dfc.coarse_type(v), 'number')
        for v in REALS:
            self.assertEqual(dfc.coarse_type(v), 'number')
        for v in STRINGS:
            self.assertEqual(dfc.coarse_type(v), 'string')
        for v in DATES:
            self.assertEqual(dfc.coarse_type(v), 'date')
        for v in OTHERS:
            self.assertEqual(dfc.coarse_type(v), 'other')

    def test_compatibility(self):
        for kind in (NUMBERS, STRINGS, DATES):
            x = kind[0]
            y = kind[-1]
            self.assertTrue(dfc.types_compatible(x, y))
            self.assertTrue(dfc.types_compatible(x, x))

    def test_incompatibility(self):
        for X in (NUMBERS, STRINGS, DATES, OTHERS, NULLS):
            for Y in (NUMBERS, STRINGS, DATES, OTHERS, NULLS):
                if X is not Y:
                    self.assertFalse(dfc.types_compatible(X[0], Y[0]))
                    self.assertFalse(dfc.types_compatible(Y[0], X[0]))

    def test_fuzzy_less_than_zero(self):
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
            (-0.990001, -1.0),
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

        self.assertEqual(MILLION + 10000 + SMALL, MILLION + 10000)
        epsilon = 0.01
        for x, y in goods + bad_goods:
            self.assertTrue(fuzzy_less_than(x, y, epsilon))
        for x, y in bads:
            self.assertFalse(fuzzy_less_than(x, y, epsilon))

    def test_fuzzy_greater_than_zero(self):
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
            (0.9900001, 1.0),
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
            (0.989999 - 100, 1.0e-100),
            (-1.01001, -1.0),
            (-MILLION - 10001, -MILLION),
            (-MILLION - 10000.0000000001, -MILLION),
            (-1.0100001e-100, -1.0e-100),
        )
        self.assertEqual(999900 - SMALL, 999900)
        epsilon = 0.01
        for x, y in goods + bad_goods:
            self.assertTrue(fuzzy_greater_than(x, y, epsilon))
        for x, y in bads:
            self.assertFalse(fuzzy_greater_than(x, y, epsilon))

    def test_caching(self):
        df = pd.DataFrame(
            {
                'a': range(3),
            }
        )
        v = dfc.DFConstraintVerifier(df)

        # First check the max gets computed and cached correctly
        self.assertEqual(v.get_max('a'), 2)
        self.assertEqual(v.cache['a']['max'], 2)

        # write new results (which are obviously wrong, but no matter)
        v.cache['a']['max'] = -3

        # Now check the new (wrong) values are returned, and remain cached
        self.assertEqual(v.get_max('a'), -3)
        self.assertEqual(v.cache['a']['max'], -3)

    def test_verify_min_constraint(self):
        df = pd.DataFrame(
            {
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
            }
        )
        goods0 = [
            (col, v, p)
            for p in (None, 'closed', 'fuzzy')
            for v in (0, 0.0)
            for col in (
                'intzero',
                'intzeron',
                'intzeronn',
                'realzero',
                'realzeron',
                'realzeronn',
            )
        ]
        bads0 = [
            (col, v, 'open')
            for v in (0, 0.0)
            for col in (
                'intzero',
                'intzeron',
                'intzeronn',
                'realzero',
                'realzeron',
                'realzeronn',
            )
        ]

        goods1 = [
            (col, v, p)
            for p in (None, 'closed', 'fuzzy')
            for v in (1, 1.0)
            for col in ('int1', 'real1')
        ]
        bads1 = [
            (col, v, 'open') for v in (1, 1.0) for col in ('int1', 'real1')
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
        for col, value, precision in goods:
            c = MinConstraint(value, precision=precision)
            cvt.verify_min_constraint(col, c).isTrue()
        for col, value, precision in bads:
            c = MinConstraint(value, precision=precision)
            cvt.verify_min_constraint(col, c).isFalse()

    def test_verify_max_constraint(self):
        df = pd.DataFrame(
            {
                'intzero': range(-2, 1),
                'intzeron': [0, None, -1],
                'intzeronn': [0, np.nan, -1],
                'realzero': [-float(i) for i in range(3)],
                'realzeron': [0.0, None, -1.0],
                'realzeronn': [0.0, np.nan, -1.0],
                'int1': range(-1, 2),
                'real1': [float(i) for i in range(-1, 2)],
            }
        )
        goods0 = [
            (col, v, p)
            for p in (None, 'closed', 'fuzzy')
            for v in (0, 0.0)
            for col in (
                'intzero',
                'intzeron',
                'intzeronn',
                'realzero',
                'realzeron',
                'realzeronn',
            )
        ]
        bads0 = [
            (col, v, 'open')
            for v in (0, 0.0)
            for col in (
                'intzero',
                'intzeron',
                'intzeronn',
                'realzero',
                'realzeron',
                'realzeronn',
            )
        ]
        goods1 = [
            (col, v, p)
            for p in (None, 'closed', 'fuzzy')
            for v in (1, 1.0)
            for col in ('int1', 'real1')
        ]
        bads1 = [
            (col, v, 'open') for v in (1, 1.0) for col in ('int1', 'real1')
        ]

        goods = goods0 + goods1
        bads = bads0 + bads1

        cvt = ConstraintVerificationTester(self, df)
        for col, value, precision in goods:
            c = MaxConstraint(value, precision=precision)
            cvt.verify_max_constraint(col, c).isTrue()
        for col, value, precision in bads:
            c = MaxConstraint(value, precision=precision)
            cvt.verify_max_constraint(col, c).isFalse()

    def test_verify_min_max_length_constraints(self):
        df = pd.DataFrame(
            {
                'zero': [''] * 4,
                'zeroOne': ['', 'a', '1', None],
                'one': ['α', 'b', 'c', None],  # Note unicode; min max len 1
                'oneTwo': ['a', 'aa', 'bb', None],
                'two': ['αα', 'αα', 'ββ', 'ββ'],  # Note unicode; min max len 2
            }
        )
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
        for col, m, M in goods:
            c = MinLengthConstraint(m)
            cvt.verify_min_length_constraint(col, c).isTrue()
            c = MaxLengthConstraint(M)
            cvt.verify_max_length_constraint(col, c).isTrue()
        for col, m, M in bads:
            c = MinLengthConstraint(m)
            cvt.verify_min_length_constraint(col, c).isFalse()
            if M is not None:
                c = MaxLengthConstraint(M)
                cvt.verify_max_length_constraint(col, c).isFalse()

    def test_verify_tdda_type_constraint(self):
        df = pd.DataFrame(
            {
                'b': [True, False],
                'i': [1, 0],
                'r': [1.0, 1.1],
                's': ['1', 'a'],
                'd': [
                    datetime.datetime(2000, 1, 1),
                    datetime.datetime(2000, 1, 2),
                ],
                'bn': [True, None],
                'in': [1, None],
                'rn': [1.1, None],
                'sn': [None, 'a'],
                'dn': [datetime.datetime(2000, 1, 1), None],
            }
        )
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
            ('bn', ['bool', 'string'], 'strict'),  # promotion to object
            ('in', ['int', 'real'], 'strict'),  # promotion to real
            ('rn', ['int', 'real'], 'strict'),  # just a looser constraint
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
        strict_cvt = ConstraintVerificationTester(
            self, df, type_checking='strict'
        )
        sloppy_cvt = ConstraintVerificationTester(
            self, df, type_checking='sloppy'
        )
        for col, value, strictness in goods:
            c = TypeConstraint(value)
            if strictness == 'strict':
                strict_cvt.verify_tdda_type_constraint(col, c).isTrue()
            # Any field that satisfies the strict checker should
            # also satisfy the sloppy checker
            sloppy_cvt.verify_tdda_type_constraint(col, c).isTrue()

        for col, value, strictness in bads:
            c = TypeConstraint(value)
            if strictness == 'sloppy':
                sloppy_cvt.verify_tdda_type_constraint(col, c).isFalse()
            # Any field that fails to satisfy the sloppy checker should
            # also fail to satisfy the strict checker
            strict_cvt.verify_tdda_type_constraint(col, c).isFalse()

    def test_verify_tdda_sign_constraint(self):
        df = pd.DataFrame(
            {
                'ipos': [1, 2, 3],
                'inonneg': [0, 1, 2],
                'izero': [0, 0, 0],
                'inonpos': [0, -1, -2],
                'ineg': [-1, -2, -3],
                'imixed': [1, 0, -1],
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
            }
        )
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
        df = pd.DataFrame(
            {
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
            }
        )
        cvt = ConstraintVerificationTester(self, df)
        c = MaxNullsConstraint(0)
        for col in df:
            if col.endswith('n'):
                cvt.verify_max_nulls_constraint(col, c).isFalse()
            else:
                cvt.verify_max_nulls_constraint(col, c).isTrue()

    def test_verify_no_duplicates_constraint(self):
        df = pd.DataFrame(
            {
                'bu': [True, False, None, None],  # Note two nulls
                'iu': [1, -1, 0, 2],
                'ru': [1.0, -1.0, 0.0, 3.0],
                'su': ['a', 'b', 'c', ''],
                'du': [
                    datetime.datetime(2000, 1, 1),
                    datetime.datetime(2000, 1, 2),
                    datetime.datetime(2000, 1, 3),
                    datetime.datetime(2000, 1, 4),
                ],
                'bd': [True, True, False, None],
                'id': [1, 2, 2, 3],
                'rd': [1.0, 2.0, 2.0, 3.0],
                'sd': ['a', 'a', 'a', 'a'],
                'dd': [datetime.datetime(2000, 1, 1)] * 4,
                'IU': [1, -1, None, None],
                'RU': [1.0, -1.0, None, None],
                'SU': [None, None, 'c', ''],
                'DU': [
                    datetime.datetime(2000, 1, 1),
                    None,
                    None,
                    datetime.datetime(2000, 1, 4),
                ],
                'BD': [True, True, False, None],
                'ID': [1, 2, 2, None],
                'RD': [None, 2.0, 2.0, None],
                'SD': ['a', 'a', None, 'b'],
                'DD': [datetime.datetime(2000, 1, 1)] * 2 + [None] * 2,
                'nu': [None, None, None, None],
            }
        )
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
        df = pd.DataFrame(
            {
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
            }
        )
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
        cvt.verify_allowed_values_constraint(
            'eitherorn', c_empties
        ).isFalse()

        cvt.verify_allowed_values_constraint('digits', c_primes).isFalse()
        cvt.verify_allowed_values_constraint('digitsn', c_primes).isFalse()
        cvt.verify_allowed_values_constraint('primes1', c_empties).isFalse()
        cvt.verify_allowed_values_constraint('primes1n', c_andor).isFalse()
        cvt.verify_allowed_values_constraint('primes2', c_andor).isFalse()
        cvt.verify_allowed_values_constraint(
            'primes2n', c_empties
        ).isFalse()
        cvt.verify_allowed_values_constraint('empties', c_primes).isFalse()
        cvt.verify_allowed_values_constraint('emptiesn', c_digits).isFalse()

        for col in df:
            if col == 'null':
                cvt.verify_allowed_values_constraint(
                    col, c_nothing
                ).isTrue()
            else:
                cvt.verify_allowed_values_constraint(
                    col, c_nothing
                ).isFalse()


class TestUtilityFunctions(ReferenceTestCase):
    def testVerificationFieldIdentifier(self):
        for name in (
            'a_type_ok',
            'a_min_ok',
            'a_min_length_ok',
            'a_max_ok',
            'a_max_length_ok',
            'a_sign_ok',
            'a_nonnull_ok',
            'a_nodups_ok',
            'a_values_ok',
            'a_rex_ok',
            'a_min_ok',
            'a_values_ok_68',
        ):
            self.assertTrue(dfc.is_ver_field(name, 'a'))

        for name in (
            'a_b',
            'a_b_ok',
            'a_b_min_ok',
            'a_b_min_ok_68',
            'a_min_ok68',
            'a_transform_ok',
        ):
            self.assertFalse(dfc.is_ver_field(name, 'a'))


class TestUtilityFunctions2(ReferenceTestCase):
    def testDateInferrer(self):
        df = pd.DataFrame(
            {
                'isod': ['2024-01-01', None, '2024-01-20', None],
                'isodt': [
                    '2024-01-01T12:34:56',
                    None,
                    '2024-01-20T21:22:23',
                    None,
                ],
                'eurod': ['01-01-2024', None, '20-01-2024', None],
                'eurodt': [
                    '01-01-2024:12:34:56',
                    None,
                    '20-01-2024:21:22:23',
                    None,
                ],
                'usd': ['01-01-2024', None, '01-20-2024', None],
                'usdt': [
                    '01-01-2024:12:34:56',
                    None,
                    '01-20-2024:21:22:23',
                    None,
                ],
                'nodate': ['foo', None, 'bar', None],
            }
        )
        expected_fmt = {
            'isod': '%Y-%m-%d',
            'isodt': 'ISO8601',
            'eurod': '%d-%m-%Y',
            'eurodt': '%d-%m-%Y:%H:%M:%S',
            'usd': '%m-%d-%Y',
            'usdt': '%m-%d-%Y:%H:%M:%S',
            'nodate': None,
        }

        dtdt = datetime.datetime
        date_col = [dtdt(2024, 1, 1), None, dtdt(2024, 1, 20), None]
        dt_col = [
            dtdt(2024, 1, 1, 12, 34, 56),
            None,
            dtdt(2024, 1, 20, 21, 22, 23),
            None,
        ]

        expected_df = pd.DataFrame(
            {
                'isod': date_col,
                'isodt': dt_col,
                'eurod': date_col,
                'eurodt': dt_col,
                'usd': date_col,
                'usdt': dt_col,
                'nodate': df['nodate'],
            }
        )

        for k in df:
            f = infer_date_format(df[k])
            if f is None:
                self.assertIs(f, expected_fmt[k])
            else:
                self.assertEqual((k, f), (k, expected_fmt[k]))
                c = pd.to_datetime(df[k], format=f)
                same = (c.dropna() == expected_df[k].dropna()).sum()
                if same != 2:
                    print(k)
                    print(c.dropna())
                    print(expected_df[k].dropna())
                    print()
                self.assertEqual(same, 2)
                self.assertEqual(c.dtype, expected_df[k].dtype)


if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
