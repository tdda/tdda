# -*- coding: utf-8 -*-

#
# Unit tests for functions from tdda.referencetest.checkpandas
#

import os
import unittest

import numpy as np
import pandas as pd

from tdda.referencetest.checkpandas import (
    PandasComparison,
    types_match,
    loosen_type,
)
from tdda.referencetest.basecomparison import diffcmd
from tdda.referencetest import tag, ReferenceTestCase


def refloc(filename):
    return os.path.join(os.path.dirname(__file__), 'testdata', filename)


@unittest.skipIf(pd is None, 'no pandas')
class TestPandasDataFrames(ReferenceTestCase):
    def test_frames_ok(self):
        compare = PandasComparison(verbose=False)
        df1 = pd.DataFrame(
            {
                'a': [1, 2, 3, 4, 5],
                'b': [1.0001, 2.0001, 3.0001, 4.0001, 5.0001],
            }
        )
        df2 = pd.DataFrame(
            {
                'a': [1, 2, 3, 4, 5],
                'b': [1.0002, 2.0002, 3.0002, 4.0002, 5.0002],
            }
        )
        df3 = pd.DataFrame({'a': [1, 2, 3, 4, 5], 'b': [1, 2, 3, 4, 5]})
        self.assertEqual(compare.check_dataframe(df1, df1), (0, []))
        self.assertEqual(
            compare.check_dataframe(df1, df2, precision=3), (0, [])
        )
        self.assertEqual(
            compare.check_dataframe(
                df1, df3, check_types=['a'], check_data=['a']
            ),
            (0, []),
        )

    def test_frames_fail(self):
        compare = PandasComparison(verbose=False)
        df1 = pd.DataFrame(
            {
                'a': [1, 2, 3, 4, 5],
                'b': [1.0001, 2.0001, 3.0001, 4.0001, 5.0001],
            }
        )
        df2 = pd.DataFrame(
            {
                'a': [1, 2, 3, 4, 5],
                'b': [1.0002, 2.0002, 3.0002, 4.0002, 5.0002],
            }
        )
        df3 = pd.DataFrame({'a': [1, 2, 3, 4, 5], 'b': [1, 2, 3, 4, 5]})

        self.assertEqual(
            compare.check_dataframe(df1, df2, precision=3), (0, [])
        )

        n1, s1 = compare.check_dataframe(df1, df2, precision=6)
        self.assertEqual(n1, 1)
        self.assertStringCorrect('\n'.join(s1), refloc('frames_fail1.txt'),
                                 ignore_lines=['diff '])

        n3, s3 = compare.check_dataframe(df1, df3, precision=3)
        self.assertEqual(n3, 1)
        self.assertStringCorrect('\n'.join(s3), refloc('frames_fail3.txt'),
                                 ignore_lines=['diff '])

    def test_pandas_csv_ok(self):
        compare = PandasComparison(verbose=False)
        r = compare.check_csv_file(
            refloc('colours.txt'), refloc('colours.txt')
        )
        self.assertEqual(r, (0, []))

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
                'Extra columns: [\'a single line\']',
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
        dns = np.dtype('datetime64[ns]')

        S = pd.core.arrays.string_.StringDtype

        o = np.dtype('O')

        dtypes = (i64, i32, I, f64, f32, dms, dns, b, B, S, o)
        ltypes = (
            'int',
            'int',
            'int',
            'float',
            'float',
            'datetime',
            'datetime',
            'bool',
            'bool',
            'string',
            'object',
        )

        for d, L in zip(dtypes, ltypes):
            self.assertEqual(loosen_type(d.name), L)

        for level in ('strict', 'medium', 'permissive'):
            for t in dtypes:
                self.assertTrue(types_match(t, t, level))
        for t1 in dtypes:
            for t2 in dtypes:
                if t1 != t2:
                    self.assertFalse(types_match(t1, t2))

        for t in (S, B, b, dms, dns):
            for level in ('medium', 'permissive'):
                self.assertTrue(types_match(t, o, level))
                self.assertTrue(types_match(o, t, level))

        for t1 in (I, i64, i32):
            for t1 in (I, i64, i32):
                for level in ('medium', 'permissive'):
                    self.assertTrue(types_match(t, o, level))
                    self.assertTrue(types_match(o, t, level))

        for level in ('medium', 'permissive'):
            self.assertTrue(types_match(f64, f32, level))
            self.assertTrue(types_match(f32, f64, level))
            self.assertTrue(types_match(b, B, level))
            self.assertTrue(types_match(B, b, level))
            self.assertTrue(types_match(dms, dns, level))
            self.assertTrue(types_match(dns, dms, level))

        # medium
        for t1 in (I, i64, i32):
            for t2 in (f64, f32, dms, dns, b, B, S, o):
                self.assertFalse(types_match(t1, t2, 'medium'))
                self.assertFalse(types_match(t2, t1, 'medium'))

        for t1 in (f64, f32):
            for t2 in (dms, dns, b, B, S, o):
                self.assertFalse(types_match(t1, t2, 'medium'))
                self.assertFalse(types_match(t2, t1, 'medium'))

        for t1 in (dms, dns):
            for t2 in (b, B, S):
                self.assertFalse(types_match(t1, t2, 'medium'))
                self.assertFalse(types_match(t2, t1, 'medium'))

        # permissive

        for t1 in (I, i64, i32, f64, f32, b, B):
            for t2 in (I, i64, i32, f64, f32, b, B):
                self.assertTrue(types_match(t1, t2, 'permissive'))
                self.assertTrue(types_match(t2, t1, 'permissive'))

        for t1 in (I, i64, i32, f64, f32):
            for t2 in (o, S, dms, dns):
                self.assertFalse(types_match(t1, t2, 'permissive'))
                self.assertFalse(types_match(t2, t1, 'permissive'))

        for t1 in (b, B):
            for t2 in (S, dms, dns):
                self.assertFalse(types_match(t1, t2, 'permissive'))
                self.assertFalse(types_match(t2, t1, 'permissive'))


if __name__ == '__main__':
    ReferenceTestCase.main()
