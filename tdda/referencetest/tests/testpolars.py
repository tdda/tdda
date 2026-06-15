#
# Unit tests for functions from tdda.referencetest.checkpolars
#

import os
import unittest

import pandas as pd
import polars as pl


from tdda.plutils import loosen_polars_type
from tdda.referencetest.checkpolars import (
    PolarsComparison,
    polars_types_match,
    round_df,
)
from tdda.referencetest.basecomparison import diffcmd
from tdda.referencetest import tag, ReferenceTestCase
from tdda.referencetest.tests.dftesthelpers import PYTHON_DATA


def refloc(filename):
    return os.path.join(os.path.dirname(__file__), 'testdata', filename)


def PandasDataFrame(n):
    return pd.DataFrame(getattr(PYTHON_DATA, f'df{n}'))


def PolarsDataFrame(n):
    return pl.DataFrame(getattr(PYTHON_DATA, f'df{n}'))


class TestPolarsDataFrames(ReferenceTestCase):
    def test_frames_ok(self):
        compare = PolarsComparison(verbose=False)
        df1 = PolarsDataFrame(1)
        df2 = PolarsDataFrame(2)
        df3 = PolarsDataFrame(3)
        self.assertFalse(compare.check_dataframe(df1, df1))
        self.assertFalse(compare.check_dataframe(df1, df2, precision=3))
        self.assertFalse(
            compare.check_dataframe(
                df1, df3, check_types=['a'], check_data=['a']
            )
        )

    def test_frames_fail(self):
        compare = PolarsComparison(verbose=False)
        df1 = PolarsDataFrame(1)
        df2 = PolarsDataFrame(2)
        df3 = PolarsDataFrame(3)

        self.assertFalse(compare.check_dataframe(df1, df2, precision=3))

        n1, s1 = compare.check_dataframe(df1, df2, precision=6)
        self.assertEqual(n1, 1)
        self.assertStringCorrect(
            '\n'.join(s1), refloc('frames_fail1.txt'), ignore_lines=self._diff_cmds
        )

        n3, s3 = compare.check_dataframe(df1, df3, precision=3)
        self.assertEqual(n3, 1)
        self.assertStringCorrect(
            '\n'.join(s3),
            refloc('pl_frames_fail3.txt'),
            ignore_lines=self._diff_cmds,
        )

        n3m, s3m = compare.check_dataframe(
            df1, df3, precision=3, type_matching='medium'
        )
        self.assertEqual(n3m, 1)
        self.assertStringCorrect(
            '\n'.join(s3m),
            refloc('pl_frames_fail3m.txt'),
            ignore_lines=self._diff_cmds,
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

    def test_polars_csv_ok(self):
        compare = PolarsComparison(verbose=False)
        r = compare.check_csv_file(
            refloc('colours.txt'), refloc('colours.txt')
        )
        self.assertFalse(r)

    def test_polars_csv_fail(self):
        compare = PolarsComparison(verbose=False)
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
        b = pl.Boolean

        i128 = pl.Int128
        i64 = pl.Int64
        i32 = pl.Int32
        i16 = pl.Int16
        i8 = pl.Int8

        u64 = pl.UInt64
        u32 = pl.UInt32
        u16 = pl.UInt16
        u8 = pl.UInt8

        f64 = pl.Float64
        f32 = pl.Float32
        f128 = pl.Decimal

        d = pl.Datetime

        S = pl.String
        Sc = pl.Categorical
        Se = pl.Enum
        Su = pl.Utf8

        ints = (
            i128,
            i64,
            i32,
            i16,
            i8,
            u64,
            u32,
            u16,
            u8,
        )
        floats = (
            f64,
            f32,
            f128,
        )
        strings = (
            S,
            Sc,
            Se,
            Su,
        )
        dtypes = (
            b,
            *ints,
            *floats,
            d,
            *strings,
        )
        ltypes = (
            'Boolean',
            'Int',
            'Int',
            'Int',
            'Int',
            'Int',
            'Int',
            'Int',
            'Int',
            'Int',
            'Float',
            'Float',
            'Float',
            'Date',
            'String',
            'String',
            'String',
            'String',
        )

        for D, L in zip(dtypes, ltypes):
            self.assertEqual(loosen_polars_type(D, 'medium'), L)

        for level in ('strict', 'medium', 'loose'):
            for t in dtypes:
                self.assertTrue(polars_types_match(t, t, level))

        for t1 in dtypes:
            for t2 in dtypes:
                if t1 != t2:
                    self.assertEqual(
                        polars_types_match(t1, t2),
                        t1 in {'String', 'Utf8'} and t1 in {'String', 'Utf8'},
                    )

        for t1 in ints:
            for t2 in ints:
                for level in ('medium', 'permissive'):
                    self.assertTrue(polars_types_match(t1, t2, level))

        for t1 in floats:
            for t2 in floats:
                for level in ('medium', 'permissive'):
                    self.assertTrue(polars_types_match(t1, t2, level))

        for t1 in strings:
            for t2 in strings:
                for level in ('medium', 'permissive'):
                    self.assertTrue(polars_types_match(t1, t2, level))

        for i in ints:
            for f in floats:
                self.assertFalse(polars_types_match(i, f, 'medium'))
                self.assertTrue(polars_types_match(i, f, 'permissive'))

        for level in ('medium', 'loose'):
            self.assertTrue(polars_types_match(f64, f32, level))
            self.assertTrue(polars_types_match(f32, f64, level))

            self.assertTrue(polars_types_match(i64, i32, level))
            self.assertTrue(polars_types_match(f32, f64, level))

        # medium
        for t1 in ints:
            for t2 in (*floats, f32, d, b, *strings):
                self.assertFalse(polars_types_match(t1, t2, 'medium'))
                self.assertFalse(polars_types_match(t2, t1, 'medium'))

        for t1 in floats:
            for t2 in (d, b, *strings):
                self.assertFalse(polars_types_match(t1, t2, 'medium'))
                self.assertFalse(polars_types_match(t2, t1, 'medium'))

        self.assertFalse(polars_types_match(pl.Boolean, pl.String, 'medium'))
        self.assertFalse(polars_types_match(pl.Boolean, pl.Datetime, 'medium'))

        # permissive

        for t1 in (*ints, *floats, b):
            for t2 in (*ints, *floats, b):
                self.assertTrue(polars_types_match(t1, t2, 'permissive'))
                self.assertTrue(polars_types_match(t2, t1, 'loose'))

        for t1 in (*ints, *floats, b):
            for t2 in (d, *strings):
                self.assertFalse(polars_types_match(t1, t2, 'loose'))
                self.assertFalse(polars_types_match(t2, t1, 'permissive'))

        for t1 in strings:
            for t2 in (b, d):
                self.assertFalse(polars_types_match(t1, t2, 'permissive'))
                self.assertFalse(polars_types_match(t2, t1, 'loose'))


class TestHighLevelPolars(ReferenceTestCase):
    def setUp(self):
        super().setUp()
        self._polars_verbose = self.polars.verbose

    def tearDown(self):
        self.polars.verbose = self._polars_verbose
        super().tearDown()

    def test_hl_assert_equivalent_ok(self):
        df1 = PolarsDataFrame(1)
        self.assertDataFramesEquivalent(df1, df1)

    def test_hl_assert_equivalent_fail(self):
        df1 = PolarsDataFrame(1)
        df2 = PolarsDataFrame(2)
        self.polars.verbose = False
        with self.assertRaises(AssertionError):
            self.assertDataFramesEquivalent(df1, df2)


class TestCrossEngine(ReferenceTestCase):
    def test_pandas_actual_polars_ref(self):
        pdf = PandasDataFrame(1)
        pldf = PolarsDataFrame(1)
        self.assertDataFramesEquivalent(pdf, pldf, engine='pandas')

    def test_polars_actual_pandas_ref(self):
        pdf = PandasDataFrame(1)
        pldf = PolarsDataFrame(1)
        self.assertDataFramesEquivalent(pldf, pdf, engine='polars')


class TestPolarsHelperFunctions(ReferenceTestCase):
    def testRound(self):
        df = pl.DataFrame({'f': [1.125, 1.25], 's': ['a', 'b'], 'i': [1, 2]})
        rdf3 = round_df(df, 3)
        self.assertEqual(rdf3['f'].to_list(), [1.125, 1.25])
        rdf2 = round_df(df, 2)
        self.assertEqual(
            rdf2['f'].to_list(), [1.12, 1.25]
        )  # Banker's rounding
        rdf1 = round_df(df, 1)
        self.assertEqual(rdf1['f'].to_list(), [1.1, 1.2])  # Banker's rounding
        rdf0 = round_df(df, 0)
        self.assertEqual(rdf0['f'].to_list(), [1.0, 1.0])  # Banker's rounding
        for rdf in (rdf3, rdf2, rdf1, rdf0):
            self.assertEqual(rdf['s'].to_list(), ['a', 'b'])
            self.assertEqual(rdf['i'].to_list(), [1, 2])


if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
