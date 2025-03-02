# -*- coding: utf-8 -*-

"""
Test Suite
"""

import datetime
import json
import math
import os
import re
import time
import shutil
import subprocess
import sys
import tempfile
import unittest

from collections import OrderedDict, namedtuple
from distutils.spawn import find_executable

import pandas as pd
import numpy as np

try:
    import pmmif
except ImportError:
    pmmif = None

try:
    import feather
except ImportError:
    feather = None

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
    NativeDefiniteObject,
    fuzzy_less_than,
    fuzzy_greater_than,
)
from tdda.constraints.console import main_with_argv

from tdda.constraints.pd import constraints as pdc
from tdda.constraints.pd.constraints import (load_df, verify_df,
                                             discover_df, detect_df)
from tdda.constraints.pd.discover import discover_df_from_file
from tdda.constraints.pd.verify import verify_df_from_file#, detect_df_from_file
from tdda.constraints.pd.detect import detect_df_from_file


from tdda.examples import copy_accounts_data_unzipped

from tdda.referencetest import ReferenceTestCase, tag
from tdda.referencetest.pddates import (
    infer_date_format,
    DateRE,
    Separators,
    get_date_separators
)
from tdda.referencetest.checkpandas import default_csv_loader


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

    def testDiscoverDataframeDates(self):
        df = pd.DataFrame({'a': [datetime.date(1987, 1, 1),
                                 datetime.date(2019, 1, 2)]})
        c = discover_df(df)
        ac = c.fields['a'].constraints
        self.assertEqual(ac['type'].value, 'date')
        self.assertEqual(ac['min'].value, datetime.date(1987, 1, 1))
        self.assertEqual(ac['max'].value, datetime.date(2019, 1, 2))
        self.assertEqual(ac['max_nulls'].value, 0)

    def testDiscoverDataframeDateTimes(self):
        df = pd.DataFrame({'a': [datetime.datetime(1987, 1, 1),
                                 datetime.datetime(2019, 1, 2)]})
        c = discover_df(df)
        ac = c.fields['a'].constraints
        self.assertEqual(ac['type'].value, 'date')
        self.assertEqual(ac['min'].value, datetime.datetime(1987, 1, 1))
        self.assertEqual(ac['max'].value, datetime.datetime(2019, 1, 2))
        self.assertEqual(ac['max_nulls'].value, 0)

    def testVerifySignWithWrongType(self):
        df = pd.DataFrame({'a': ['one', 'two', 'three']})
        cdict = {
            'fields': {
                'a': {
                    'type': 'int',
                    'sign': 'positive',
                }
            }
        }
        constraints = DatasetConstraints()
        constraints.initialize_from_dict(native_definite(cdict))
        v = verify_df(df, cdict, repair=False)
        self.assertFalse(v.fields['a']['type'])
        self.assertFalse(v.fields['a']['sign'])

    def testVerifyStringLengthWithWrongType(self):
        df = pd.DataFrame({'a': [1, 2, -1]})
        cdict = {
            'fields': {
                'a': {
                    'type': 'string',
                    'min_length': 2,
                    'max_length': 3,
                }
            }
        }
        constraints = DatasetConstraints()
        constraints.initialize_from_dict(native_definite(cdict))
        v = verify_df(df, cdict, repair=False)
        self.assertFalse(v.fields['a']['type'])
        self.assertFalse(v.fields['a']['min_length'])
        self.assertFalse(v.fields['a']['max_length'])

    def testDetectWithWrongTypes(self):
        df = pd.DataFrame({'a': [1, 2, 3], 'b': ['one', 'two', 'three']})
        cdict = {
            'fields': {
                'a': {
                    'type': 'string',
                    'min_length': 2,
                    'max_length': 3,
                },
                'b': {
                    'type': 'int',
                    'min': 1,
                    'max': 3,
                    'sign': 'positive',
                }
            }
        }
        constraints = DatasetConstraints()
        constraints.initialize_from_dict(native_definite(cdict))
        v = detect_df(df, cdict, per_constraint=True, output_fields=[],
                      interleave=True, repair=False)
        d = v.detected()
        self.assertTrue(not d['a_type_ok'].any())
        self.assertTrue(not d['b_type_ok'].any())
        self.assertTrue(not d['b_min_ok'].any())
        self.assertTrue(not d['b_max_ok'].any())

    def testVerifyWithMalformedInMemoryConstraintDict(self):
        df = pd.DataFrame({'a': [1, 2, 3], 'b': ['one', 'two', 'three']})
        cdicts = [
            [],
            {},
            {'fields': 'a'},
            {'fields': 22},
            {'fields': {
                    'a': 33,
                    'b': 'b',
                }
            }
        ]
        for cdict in cdicts:
            constraints = DatasetConstraints()
            with self.assertRaises(Exception):
                constraints.initialize_from_dict(native_definite(cdict))
                v = verify_df(df, cdict, repair=False)


class TestPandasExampleAccountsData(ReferenceTestCase):
    @classmethod
    def setUpClass(cls):
        copy_accounts_data_unzipped(TESTDATA_DIR)

    def testDiscover1k(self):
        csv_path = os.path.join(TESTDATA_DIR, 'accounts1k.csv')
        tddafile1k = os.path.join(self.tmp_dir, 'accounts1kgen.tdda')
        reftddafile1k = os.path.join(TESTDATA_DIR, 'ref-accounts1k.tdda')
        c = discover_df_from_file(csv_path, constraints_path=tddafile1k,
                                  verbose=False)
        self.assertTextFileCorrect(tddafile1k, reftddafile1k, rstrip=True,
                                   ignore_lines=[
                                       '"local_time":',
                                       '"utc_time":',
                                       '"creator":',
                                       '"source":',
                                       '"host":',
                                       '"user":',
                                       '"tddafile":',
                                   ])

    def testDiscover1k_parquet(self):
        pq_path = os.path.join(TESTDATA_DIR, 'accounts1k.parquet')
        tddafile1k = os.path.join(self.tmp_dir, 'accounts1kgen.tdda')
        reftddafile1k = os.path.join(TESTDATA_DIR, 'ref-accounts1k.tdda')
        c = discover_df_from_file(pq_path, constraints_path=tddafile1k,
                                  verbose=False)
        self.assertTextFileCorrect(tddafile1k, reftddafile1k, rstrip=True,
                                   ignore_lines=[
                                       '"local_time":',
                                       '"utc_time":',
                                       '"creator":',
                                       '"source":',
                                       '"host":',
                                       '"user":',
                                       '"tddafile":',
                                       '"dataset":'
                                   ])

    def testVerify1k(self):
        csv_path = os.path.join(TESTDATA_DIR, 'accounts1k.csv')
        reftddafile1k = os.path.join(TESTDATA_DIR, 'ref-accounts1k.tdda')
        v = verify_df_from_file(csv_path, constraints_path=reftddafile1k,
                                verbose=False)
        self.assertEqual(v.passes, 72)
        self.assertEqual(v.failures, 0)

    def testVerify1k_parquet(self):
        pq_path = os.path.join(TESTDATA_DIR, 'accounts1k.parquet')
        reftddafile1k = os.path.join(TESTDATA_DIR, 'ref-accounts1k.tdda')
        v = verify_df_from_file(pq_path, constraints_path=reftddafile1k,
                                verbose=False)
        self.assertEqual(v.passes, 72)
        self.assertEqual(v.failures, 0)

    def testVerify25kAgainst1k(self):
        csv_path = os.path.join(TESTDATA_DIR, 'accounts25k.csv')
        reftddafile1k = os.path.join(TESTDATA_DIR, 'ref-accounts1k.tdda')
        v = verify_df_from_file(csv_path, constraints_path=reftddafile1k,
                                  verbose=False)

        passingConstraints = 53
        failingConstraints = 19
        expected = (passingConstraints, failingConstraints)

        self.assertEqual(v.passes, passingConstraints)
        self.assertEqual(v.failures, failingConstraints)

        # !!! IF THIS FAILS, THE EXAMPLES README NEEDS TO BE UPDATED
        self.assertEqual(expected, (53, 19), "NUMBERS DIFFER FROM README!")
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    def testVerify25kAgainst1k_parquet(self):
        pq_path = os.path.join(TESTDATA_DIR, 'accounts25k.parquet')
        reftddafile1k = os.path.join(TESTDATA_DIR, 'ref-accounts1k.tdda')
        v = verify_df_from_file(pq_path, constraints_path=reftddafile1k,
                                verbose=False)

        # These are one different from CSV version because
        # the CSV reader reads the empty strings in account_type
        # as None values, whereas in the parquet file they are
        # empty strings. There's a philosophical question as to
        # which is "right", but the tests are checking the the
        # data as read by the CSV and Parquet readers is validated
        # correctly by TDDA.

        passingConstraints = 53
        failingConstraints = 19
        expected = (passingConstraints, failingConstraints)

        self.assertEqual(v.passes, passingConstraints)
        self.assertEqual(v.failures, failingConstraints)

    def testDetect25kAgainst1k(self):
        csv_path = os.path.join(TESTDATA_DIR, 'accounts25k.csv')
        reftddafile1k = os.path.join(TESTDATA_DIR, 'ref-accounts1k.tdda')
        refpath = os.path.join(TESTDATA_DIR, 'ref-detect25k-failures.txt')
        outfile = os.path.join(self.tmp_dir, 'accounts25kfailures.txt')
        v = detect_df_from_file(csv_path, constraints_path=reftddafile1k,
                                outpath=outfile, verbose=False)
        passingConstraints = 53
        failingConstraints = 19
        passingRecords = 24883
        failingRecords = 117
        expected = (passingConstraints, failingConstraints,
                    passingRecords, failingRecords)
        self.assertEqual(v.passes, passingConstraints)
        self.assertEqual(v.failures, failingConstraints)
        self.assertEqual(v.detection.n_passing_records,  passingRecords)
        self.assertEqual(v.detection.n_failing_records, failingRecords)

        # !!! IF THIS FAILS, THE EXAMPLES README NEEDS TO BE UPDATED
        self.assertEqual(expected, (53, 19, 24883, 117),
                         "NUMBERS DIFFER FROM README!")
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

        self.assertTextFileCorrect(outfile, refpath)

    def testDetect25kAgainst1k_parquet(self):
        pq_path = os.path.join(TESTDATA_DIR, 'accounts25k.parquet')
        reftddafile1k = os.path.join(TESTDATA_DIR, 'ref-accounts1k.tdda')
        refpath = os.path.join(TESTDATA_DIR, 'ref-detect25k-failures.parquet')
        refcsvpath = os.path.join(TESTDATA_DIR, 'ref-detect25k-failures.txt')
        outfile = os.path.join(self.tmp_dir, 'accounts25kfailures.parquet')
        v = detect_df_from_file(pq_path, constraints_path=reftddafile1k,
                                outpath=outfile, verbose=False)
        passingConstraints = 53
        failingConstraints = 19
        passingRecords = 24883
        failingRecords = 117
        expected = (passingConstraints, failingConstraints,
                    passingRecords, failingRecords)
        self.assertEqual(v.passes, passingConstraints)
        self.assertEqual(v.failures, failingConstraints)
        self.assertEqual(v.detection.n_passing_records,  passingRecords)
        self.assertEqual(v.detection.n_failing_records, failingRecords)


        actual_df = pd.read_parquet(outfile)
        expected_df = pd.read_parquet(refpath)

        # Check against saved reference parquet file
        self.assertDataFramesEqual(actual_df, expected_df, outfile, refpath)

        # Also check that's the same as the CSV equivalent,
        # appropriately read!
        from_csv_df = default_csv_loader(refcsvpath)
        self.assertDataFramesEqual(expected_df, from_csv_df,
                                   outfile, refcsvpath)


    def testDiscover25k(self):
        csv_path = os.path.join(TESTDATA_DIR, 'accounts25k.csv')
        tddafile = os.path.join(self.tmp_dir, 'accounts25kgen.tdda')
        reftddafile = os.path.join(TESTDATA_DIR, 'ref-accounts25k.tdda')
        c = discover_df_from_file(csv_path, constraints_path=tddafile,
                                  verbose=False)
        self.assertTextFileCorrect(tddafile, reftddafile, rstrip=True,
                                   ignore_lines=[
                                       '"local_time":',
                                       '"utc_time":',
                                       '"creator":',
                                       '"source":',
                                       '"host":',
                                       '"user":',
                                       '"tddafile":',
                                   ])


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
        self.assertTextFileCorrect(detectfile, 'elements118rex_detect.csv')

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
        self.assertTextFileCorrect(detectfile,
                                   'elements118rex_detect_perc.csv')

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

    @unittest.skipIf(pmmif is None or feather is None,
                     'pmmif/feather not installed')
    def testDetectElements118_csv_to_feather(self):
        self.detectElements('csv', 'feather')

    @unittest.skipIf(pmmif is None or feather is None,
                     'pmmif/feather not installed')
    def testDetectElements118_feather_to_csv(self):
        self.detectElements('feather', 'csv')

    @unittest.skipIf(pmmif is None or feather is None,
                     'pmmif/feather not installed')
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
            self.assertTextFileCorrect(detectfile, detect_name)

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
        if inc_rex:
            old_ref_name = 'elements92oldrex.tdda'
            new_ref_name = 'elements92rex.tdda'
            old_ref_constraints_path = os.path.join(TESTDATA_DIR, old_ref_name)
            new_ref_constraints_path = os.path.join(TESTDATA_DIR, new_ref_name)
        else:
            ref_name = 'elements92.tdda'
            old_ref_constraints_path = os.path.join(TESTDATA_DIR, ref_name)
            new_ref_constraints_path = os.path.join(TESTDATA_DIR, ref_name)
        with open(old_ref_constraints_path) as f:
            old_refjson = f.read()
        with open(new_ref_constraints_path) as f:
            new_refjson = f.read()
        old_ref = native_definite(json.loads(old_refjson))
        new_ref = native_definite(json.loads(new_refjson))
        constraints = discover_df(df, inc_rex=inc_rex)
        discovered = native_definite(json.loads(constraints.to_json()))
        discovered_fields = discovered['fields']
        old_ref_fields = old_ref['fields']
        new_ref_fields = new_ref['fields']
        self.assertEqual(set(discovered_fields.keys()),
                         set(new_ref_fields.keys()))
        for field, ref_field in new_ref_fields.items():
            old_ref_field = old_ref_fields[field]
            new_ref_field = new_ref_fields[field]
            discovered_field = discovered_fields[field]
            self.assertEqual((field, set(discovered_field.keys())),
                             (field, set(new_ref_field.keys())))
            for c, new_expected in new_ref_field.items():
                actual = discovered_field[c]
                old_expected = old_ref_field[c]
                if type(new_expected) == float:
                    self.assertAlmostEqual(actual, new_expected, 4)
                elif type(new_expected) == list:
                    self.assertIn(set(actual), [set(new_expected),
                                                set(old_expected)])
                elif new_expected in ('int', 'real'):  # pandas too broken to
                                                       # get this right for now
                    self.assertTrue(actual in ('int', 'real'))
                else:
                    # regular expressions must match either 'old' or 'new'
                    self.assertIn(actual, (old_expected, new_expected))


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
        cls.e92bads3 = os.path.join(cls.test_tmpdir, 'elements92bads3.csv')

        argv = ['tdda', 'examples', cls.test_tmpdir]
        cls.execute_command(argv)

    @classmethod
    def tearDownHelper(cls):
        rmdirs(cls.test_tmpdir, cls.test_dirs)

    def testDiscoverCmd(self):
        argv = ['tdda', 'discover', self.e92csv, self.e92tdda]
        self.execute_command(argv)
        self.assertTextFileCorrect(self.e92tdda, 'elements92_pandas.tdda',
                                   rstrip=True,
                                   ignore_substrings=[
                                       '"local_time":', '"utc_time":',
                                       '"source":', '"host":', '"user":',
                                       '"tddafile":', '"creator":',
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
        self.assertTextFileCorrect(self.e92bads1, 'detect-els-cmdline.csv')
        os.remove(self.e92bads1)

    def testDetectE118CmdInterleaved(self):
        argv = ['tdda', 'detect', self.e118csv, self.e92tdda_correct,
                self.e92bads3, '--per-constraint', '--output-fields',
                '--interleave']
        result = self.execute_command(argv)
        self.assertTrue(result.strip().endswith('SUMMARY:\n\n'
                                                'Records passing: 91\n'
                                                'Records failing: 27'))
        self.assertTrue(os.path.exists(self.e92bads3))
        self.assertTextFileCorrect(self.e92bads3,
                                   'detect-els-cmdline-interleaved.csv')
        os.remove(self.e92bads3)

    @unittest.skipIf(pmmif is None or feather is None,
                     'pmmif/feather not installed')
    def testDetectE118FeatherCmd(self):
        argv = ['tdda', 'detect', self.e118feather, self.e92tdda_correct,
                self.e92bads2, '--per-constraint', '--output-fields',
                '--index']
        result = self.execute_command(argv)
        self.assertTrue(result.strip().endswith('SUMMARY:\n\n'
                                                'Records passing: 91\n'
                                                'Records failing: 27'))
        self.assertTrue(os.path.exists(self.e92bads2))
        self.assertTextFileCorrect(self.e92bads2, 'detect-els-cmdline2.csv')
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
        cls.pythonioencoding = os.environ.get('PYTHONIOENCODING', None)
        os.environ['PYTHONIOENCODING'] = 'utf-8'
        cls.setUpHelper()

    @classmethod
    def tearDownClass(cls):
        cls.tearDownHelper()
        if cls.pythonioencoding is None:
            del os.environ['PYTHONIOENCODING']
        else:
            os.environ['PYTHONIOENCODING'] = cls.pythonioencoding

    @classmethod
    def execute_command(self, argv):
        try:
            result = check_shell_output(argv)
        except:
            print('\n\nIf this test fails, it often means you do not have a '
                  'working command-line\ninstallation of the tdda command.\n\n'
                  'To test this, try typing\n\n  tdda version\n\n')
            raise
        return result


class TestUtilityFunctions(ReferenceTestCase):
    def testVerificationFieldIdentifier(self):
        for name in ('a_type_ok',
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
                     'a_values_ok_68'):
            self.assertTrue(pdc.is_ver_field(name, 'a'))

        for name in ('a_b',
                     'a_b_ok',
                     'a_b_min_ok',
                     'a_b_min_ok_68',
                     'a_min_ok68',
                     'a_transform_ok'):
            self.assertFalse(pdc.is_ver_field(name, 'a'))


class TestUtilityFunctions(ReferenceTestCase):

    def testDateInferrer(self):
        df = pd.DataFrame({
            'isod': ['2024-01-01', None, '2024-01-20', None],
            'isodt': ['2024-01-01T12:34:56', None, '2024-01-20T21:22:23', None],
            'eurod': ['01-01-2024', None, '20-01-2024', None],
            'eurodt': ['01-01-2024:12:34:56', None, '20-01-2024:21:22:23',
                       None],
            'usd': ['01-01-2024', None, '01-20-2024', None],
            'usdt': ['01-01-2024:12:34:56', None, '01-20-2024:21:22:23',
                     None],
            'nodate': ['foo', None, 'bar', None]
        })
        expected_fmt = {
            'isod': '%Y-%m-%d',
            'isodt': 'ISO8601',
            'eurod': '%d-%m-%Y',
            'eurodt': '%d-%m-%Y:%H:%M:%S',
            'usd': '%m-%d-%Y',
            'usdt': '%m-%d-%Y:%H:%M:%S',
            'nodate': None
        }

        dtdt = datetime.datetime
        date_col = [dtdt(2024, 1, 1), None, dtdt(2024, 1, 20), None]
        dt_col = [dtdt(2024, 1, 1, 12, 34, 56), None,
                  dtdt(2024, 1, 20, 21, 22, 23), None]

        expected_df = pd.DataFrame({
            'isod': date_col,
            'isodt': dt_col,
            'eurod': date_col,
            'eurodt': dt_col,
            'usd': date_col,
            'usdt': dt_col,
            'nodate': df['nodate'],
        })

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

    def testDateRE(self):
        R = DateRE
        dates = {
            '2024-01-20': R.ISO_DATEISH,
            '2024/01/20': R.ISO_DATEISH,

            '2024-01-20T12:34:56': R.ISO_DATETIMEISH,
            '2024-01-20 12:34:56.12345': R.ISO_DATETIMEISH,
            '2024/01/20T12:34:56': R.ISO_DATETIMEISH,
            '2024/01/20 12:34:56.12345': R.ISO_DATETIMEISH,


            '20-01-2024': R.DATEISH4Y,
            '20/01/2024': R.DATEISH4Y,

            '01-20-2024': R.DATEISH4Y,
            '01/20/2024': R.DATEISH4Y,

            '20-01-2024': R.DATEISH4Y,
            '20/01/2024': R.DATEISH4Y,

            '01-20-2024': R.DATEISH4Y,
            '01/20/2024': R.DATEISH4Y,

            '20-01-2024T12:34:56': R.DATEISH4Y,
            '20-01-2024T12:34:56.123456': R.DATEISH4Y,


            '20-01-24': R.DATEISH2Y,
            '20/01/24': R.DATEISH2Y,

            '01-20-24': R.DATEISH2Y,
            '01/20/24': R.DATEISH2Y,

            '20-01-24': R.DATEISH2Y,
            '20/01/24': R.DATEISH2Y,

            '01-20-24': R.DATEISH2Y,
            '01/20/24': R.DATEISH2Y,

            '20-01-24T12:34:56': R.DATEISH2Y,
            '20-01-24T12:34:56.123456': R.DATEISH2Y,

        }

        for k, r in dates.items():
            m = re.match(r, k)
            if not m:
                print(f'Failing: {k} {r.pattern}')
            self.assertIsNotNone(m)

            m = re.match(R.DATEISH, k)
            if not m:
                print(f'Failing: {k} (not DATEISH)')
            self.assertIsNotNone(m)

        sep_dates = {
            '20-01-2024': (
                R.SEPS4Y,
                Separators('-', None, None, False, False, '')
            ),
            '20-01-2024T12:34:56': (
                R.SEPS4Y,
                Separators('-', 'T', ':', True, False, 'T%H:%M:%S')
            ),

            '20-01-2024T12:34:56.123': (
                R.SEPS4Y,
                Separators('-', 'T', ':', True, True, 'T%H:%M:%S.%f')
            ),
            '20/01/2024 12.34.56.123': (
                R.SEPS4Y,
                Separators('/', ' ', '.', True, True, ' %H.%M.%S.%f')
            ),
        }
        for k, (r, expected) in sep_dates.items():
            actual = get_date_separators(r, k)
            if actual != expected:
                print('-->   actual', actual)
                print('--> expected', expected)
                print()
            self.assertEqual(actual, expected)




TestPandasMultipleConstraintVerifier.set_default_data_location(TESTDATA_DIR)
TestPandasMultipleConstraintDetector.set_default_data_location(TESTDATA_DIR)
TestPandasCommandLine.set_default_data_location(TESTDATA_DIR)
TestPandasCommandAPI.set_default_data_location(TESTDATA_DIR)


def rmdirs(parent, dirs):
    for d in dirs:
        shutil.rmtree(os.path.join(parent, d), ignore_errors=True)


def check_shell_output(args):
    result = subprocess.check_output(NativeDefiniteObject(args))
    return native_definite(result).replace('\r', '')


if __name__ == '__main__':
    ReferenceTestCase.main()
