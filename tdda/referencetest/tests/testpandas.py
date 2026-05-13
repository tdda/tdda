#
# Unit tests for functions from tdda.referencetest.checkpandas
#

import os
import unittest

import numpy as np
import pandas as pd

from tdda.referencetest.checkpandas import (
    PandasComparison,
    pandas_types_match,
)
from tdda.pdutils import loosen_pandas_type
from tdda.referencetest.basecomparison import diffcmd
from tdda.referencetest import tag, ReferenceTestCase
from tdda.referencetest.tests.dftesthelpers import PYTHON_DATA


def refloc(filename):
    return os.path.join(os.path.dirname(__file__), 'testdata', filename)


def PandasDataFrame(n):
    return pd.DataFrame(getattr(PYTHON_DATA, f'df{n}'))


class TestPandasDataFrames(ReferenceTestCase):
    def test_frames_ok(self):
        compare = PandasComparison(verbose=False)
        df1 = PandasDataFrame(1)
        df2 = PandasDataFrame(2)
        df3 = PandasDataFrame(3)
        self.assertFalse(compare.check_dataframe(df1, df1))
        self.assertFalse(compare.check_dataframe(df1, df2, precision=3))
        self.assertFalse(
            compare.check_dataframe(
                df1, df3, check_types=['a'], check_data=['a']
            )
        )

    def test_frames_fail(self):
        compare = PandasComparison(verbose=False)
        df1 = PandasDataFrame(1)
        df2 = PandasDataFrame(2)
        df3 = PandasDataFrame(3)

        self.assertFalse(compare.check_dataframe(df1, df2, precision=3))

        n1, s1 = compare.check_dataframe(df1, df2, precision=6)
        self.assertEqual(n1, 1)
        self.assertStringCorrect(
            '\n'.join(s1), refloc('frames_fail1.txt'), ignore_lines=['diff ']
        )

        n3, s3 = compare.check_dataframe(df1, df3, precision=3)
        self.assertEqual(n3, 1)
        self.assertStringCorrect(
            '\n'.join(s3),
            refloc('pd_frames_fail3.txt'),
            ignore_lines=['diff '],
        )

        n3m, s3m = compare.check_dataframe(
            df1, df3, precision=3, type_matching='medium'
        )
        self.assertEqual(n3m, 1)
        self.assertStringCorrect(
            '\n'.join(s3m),
            refloc('pd_frames_fail3m.txt'),
            ignore_lines=['diff '],
        )

        self.assertFalse(
            compare.check_dataframe(
                df1, df3, precision=3, type_matching='loose'
            )
        )
        self.assertFalse(
            compare.check_dataframe(
                df1, df3, precision=3, type_matching='permissive'
            )
        )

    def test_pandas_csv_ok(self):
        compare = PandasComparison(verbose=False)
        r = compare.check_csv_file(
            refloc('colours.txt'), refloc('colours.txt')
        )
        self.assertFalse(r)

    def test_pandas_csv_fail(self):
        compare = PandasComparison(verbose=False)
        (code, errs) = compare.check_csv_file(
            refloc('single.txt'), refloc('colours.txt')
        )
        errs = [
            e
            for e in errs
            if not e.startswith('Compare with:')
            and not e.startswith('    ' + diffcmd())
        ]
        self.assertEqual(code, 1)
        self.assertEqual(
            errs,
            [
                'Data frames have different column structure.',
                'Missing columns: [%s]'
                % ', '.join(
                    [
                        "'%s'" % s
                        for s in ['Name', 'RGB', 'Hue', 'Saturation', 'Value']
                    ]
                ),
                "Extra columns: ['a single line']",
                'Data frames have different numbers of rows.',
                'Actual records: 0; Expected records: 147',
            ],
        )

    def test_types_match(self):
        b = np.dtype('bool')
        B = pd.core.arrays.boolean.BooleanDtype

        i64 = np.dtype('int64')
        i32 = np.dtype('int32')
        I = pd.core.arrays.integer.Int64Dtype

        f64 = np.dtype('float64')
        f32 = np.dtype('float32')

        dms = np.dtype('datetime64[ms]')
        dus = np.dtype('datetime64[us]')
        dns = np.dtype('datetime64[ns]')

        S = pd.core.arrays.string_.StringDtype

        o = np.dtype('O')

        dtypes = (i64, i32, I, f64, f32, dms, dus, dns, b, B, S, o)
        ndtypes = (i64, i32, I, f64, f32, b, B, S, o)
        ltypes = (
            'int',
            'int',
            'int',
            'float',
            'float',
            'datetime',
            'datetime',
            'datetime',
            'bool',
            'bool',
            'string',
            'object',
        )

        for d, L in zip(dtypes, ltypes):
            self.assertEqual(loosen_pandas_type(d), L)

        for level in ('strict', 'medium', 'permissive'):
            for t in dtypes:
                self.assertTrue(pandas_types_match(t, t, level))
        for t1 in ndtypes:
            for t2 in dtypes:
                if t1 != t2:
                    self.assertFalse(pandas_types_match(t1, t2))

        for t in (S, B, b, dms, dns):
            for level in ('medium', 'loose'):
                self.assertTrue(pandas_types_match(t, o, level))
                self.assertTrue(pandas_types_match(o, t, level))

        # Change from ns to us in Pandas3.
        # Probably best to allow ns, us, ms to match
        # even at strict
        self.assertTrue(pandas_types_match(dms, dns, 'strict'))
        self.assertTrue(pandas_types_match(dus, dns, 'strict'))
        self.assertTrue(pandas_types_match(dus, dms, 'strict'))

        for t1 in (I, i64, i32):
            for t2 in (I, i64, i32):
                for level in ('medium', 'permissive'):
                    self.assertTrue(pandas_types_match(t1, t2, level))

        for level in ('medium', 'loose'):
            self.assertTrue(pandas_types_match(f64, f32, level))
            self.assertTrue(pandas_types_match(f32, f64, level))
            self.assertTrue(pandas_types_match(b, B, level))
            self.assertTrue(pandas_types_match(B, b, level))
            self.assertTrue(pandas_types_match(dms, dns, level))
            self.assertTrue(pandas_types_match(dns, dms, level))

        # medium
        for t1 in (I, i64, i32):
            for t2 in (f64, f32, dms, dns, b, B, S, o):
                self.assertFalse(pandas_types_match(t1, t2, 'medium'))
                self.assertFalse(pandas_types_match(t2, t1, 'medium'))

        for t1 in (f64, f32):
            for t2 in (dms, dns, b, B, S, o):
                self.assertFalse(pandas_types_match(t1, t2, 'medium'))
                self.assertFalse(pandas_types_match(t2, t1, 'medium'))

        for t1 in (dms, dns):
            for t2 in (b, B, S):
                self.assertFalse(pandas_types_match(t1, t2, 'medium'))
                self.assertFalse(pandas_types_match(t2, t1, 'medium'))

        # permissive

        for t1 in (I, i64, i32, f64, f32, b, B):
            for t2 in (I, i64, i32, f64, f32, b, B):
                self.assertTrue(pandas_types_match(t1, t2, 'permissive'))
                self.assertTrue(pandas_types_match(t2, t1, 'loose'))

        for t1 in (I, i64, i32, f64, f32):
            for t2 in (o, S, dms, dns):
                self.assertFalse(pandas_types_match(t1, t2, 'loose'))
                self.assertFalse(pandas_types_match(t2, t1, 'permissive'))

        for t1 in (b, B):
            for t2 in (S, dms, dns):
                self.assertFalse(pandas_types_match(t1, t2, 'permissive'))
                self.assertFalse(pandas_types_match(t2, t1, 'loose'))


class TestHighLevelPandas(ReferenceTestCase):
    def setUp(self):
        super().setUp()
        self._pandas_verbose = self.pandas.verbose

    def tearDown(self):
        self.pandas.verbose = self._pandas_verbose
        super().tearDown()

    def test_hl_assert_equivalent_ok(self):
        df1 = PandasDataFrame(1)
        self.assertDataFramesEquivalent(df1, df1)

    def test_hl_assert_equivalent_fail(self):
        df1 = PandasDataFrame(1)
        df2 = PandasDataFrame(2)
        self.pandas.verbose = False
        with self.assertRaises(AssertionError):
            self.assertDataFramesEquivalent(df1, df2)


if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
