import pandas as pd

from tdda.referencetest import ReferenceTestCase, tag
from tdda.referencetest.referencetest import ReferenceTest
from tdda.referencetest.checkpandas import (
    PandasComparison,
    types_match,
    loosen_type,
    single_col_diffs,
    create_row_diffs_mask,
    create_row_diff_counts,
)
from tdda.referencetest.basecomparison import DataFrameDiffs


import os

TESTDATA = os.path.join(os.path.dirname(__file__), 'testdata')
PQ_REF4_PATH = os.path.join(TESTDATA, 'four-squares.parquet')
CSV_REF4_PATH = os.path.join(TESTDATA, 'four-squares.csv')

class TestOne(ReferenceTestCase):

    def testNoDiffsInMem(self):
        self.assertDataFramesEqual(four_squares(), four_squares())

    def testNoDiffsMemParquet(self):
        self.assertDataFrameCorrect(four_squares(), PQ_REF4_PATH)

    def testNoDiffsMemCSV(self):
        self.assertDataFrameCorrect(four_squares(), CSV_REF4_PATH)

    def testNoDiffsParquetParquet(self):
        self.assertOnDiskDataFrameCorrect(PQ_REF4_PATH, PQ_REF4_PATH)

    def testNoDiffsParquetCSV(self):
        self.assertOnDiskDataFrameCorrect(PQ_REF4_PATH, CSV_REF4_PATH)

    def testNoDiffsCSVParquet(self):
        self.assertOnDiskDataFrameCorrect(CSV_REF4_PATH, PQ_REF4_PATH)

    def testNoDiffsCSVCSV(self):
        self.assertOnDiskDataFrameCorrect(CSV_REF4_PATH, CSV_REF4_PATH)

    def testOneDiffInMem(self):
        c = PandasComparison()
        ref = four_squares()
        actual = four_squares_and_ten()
        c.verbose = False
        r = c.check_dataframe(actual, ref)
        self.assertEqual(r.failures, 1)
        self.assertStringCorrect(str(r.diffs), fp('one-diff-in-mem.txt'),
            ignore_patterns=[
                r'diff .*/actual-df001.parquet .*/expected-df001.parquet'
            ])
        self.assertEqual(str(r.diffs.df), str(DataFrameDiffs()))

    def testDiffColTypeInMemIntStr(self):
        c = PandasComparison()
        actual = four_squares()
        actual['squares'] = [str(sq) for sq in actual['squares']]
        expected = four_squares()
        r = c.check_dataframe(actual, expected)
        self.assertEqual(r.failures, 1)
        self.assertStringCorrect(str(r.diffs), fp('diff-col-types-int-str.txt'),
            ignore_patterns=[
                r'diff .*/actual-df001.parquet .*/expected-df001.parquet'
            ])
        self.assertStringCorrect(str(r.diffs.df),
            fp('ddiff-col-types-int-str.txt'))

    def testDiffColTypeInMemIntFloat(self):
        c = PandasComparison()
        actual = four_squares()
        actual['squares'] = [float(sq) for sq in actual['squares']]
        expected = four_squares()
        r = c.check_dataframe(actual, expected)
        self.assertEqual(r.failures, 1)
        self.assertStringCorrect(
            str(r.diffs),
            fp('diff-col-types-int-float.txt'),
            ignore_patterns=[
                'diff .*/actual-df001.parquet .*/expected-df001.parquet'
            ]
        )
        self.assertStringCorrect(
            str(r.diffs.df),
            fp('ddiff-col-types-int-float.txt')
        )

    def testDiffColOrderInMem(self):
        c = PandasComparison()
        ref = four_squares()
        actual = pd.DataFrame({
            'squares': ref['squares'],
            'row': ref['row'],
        })
        self.assertEqual(list(reversed(list(actual))), list(ref))
        r = c.check_dataframe(actual, ref)
        self.assertEqual(r.failures, 1)
        self.assertStringCorrect(
            str(r.diffs),
            fp('diff-col-order.txt'),
            ignore_patterns=[
                'diff .*/actual-df001.parquet .*/expected-df001.parquet'
            ]
        )

        self.assertStringCorrect(
            str(r.diffs.df),
            fp('ddiff-col-order.txt')
        )

    def testSingleColDiffs(self):
        df = pd.DataFrame({
            'a': pd.Series([0, 1, None, None], dtype=pd.Int64Dtype()),
            'b': pd.Series([0, None, 2, None], dtype=pd.Int64Dtype()),
            'A': [0, 1, None, None],
            'B': [0, None, 2, None],
            'm': [False, True, True, False],
        })
        diffs = single_col_diffs(df.A, df.B)
        self.assertTrue(diffs.mask.eq(df.m).all())
        self.assertEqual(diffs.n, 2)


        diffs = single_col_diffs(df.b, df.a)
        self.assertTrue(diffs.mask.eq(df.m).all())
        self.assertEqual(diffs.n, 2)

    def testCreateRowDiffsMaskAndCounts(self):
        f, t = False, True

        m10000000 = pd.Series([t, f, f, f, f, f, f, f])
        m01000000 = pd.Series([f, t, f, f, f, f, f, f])
        m00100000 = pd.Series([f, f, t, f, f, f, f, f])
        m00010000 = pd.Series([f, f, f, t, f, f, f, f])
        m00001000 = pd.Series([f, f, f, f, t, f, f, f])
        m00000100 = pd.Series([f, f, f, f, f, t, f, f])
        m00000010 = pd.Series([f, f, f, f, f, f, t, f])
        m00000001 = pd.Series([f, f, f, f, f, f, f, t])

        expected1 = pd.Series([t, f, f, f, f, f, f, f])
        expected2 = pd.Series([t, t, f, f, f, f, f, f])
        expected3 = pd.Series([t, t, t, f, f, f, f, f])
        expected4 = pd.Series([t, t, t, t, f, f, f, f])
        expected5 = pd.Series([t, t, t, t, t, f, f, f])
        expected6 = pd.Series([t, t, t, t, t, t, f, f])
        expected7 = pd.Series([t, t, t, t, t, t, t, f])
        expected8 = pd.Series([t, t, t, t, t, t, t, t])

        masks = [
            m10000000, m01000000, m00100000, m00010000,
            m00001000, m00000100, m00000010, m00000001
        ]

        combined = create_row_diffs_mask(masks[:1])
        counts = create_row_diff_counts(masks[:1])
        self.assertEqual(combined.eq(expected1).sum(), 8)
        self.assertEqual(counts.eq(pd.Series([1] + [0] * 7)).sum(), 8)

        combined = create_row_diffs_mask(masks[:2])
        counts = create_row_diff_counts(masks[:2])
        self.assertEqual(combined.eq(expected2).sum(), 8)
        self.assertEqual(counts.eq(pd.Series([1] * 2 + [0] * 6)).sum(), 8)

        combined = create_row_diffs_mask(masks[:3])
        counts = create_row_diff_counts(masks[:3])
        self.assertEqual(combined.eq(expected3).sum(), 8)
        self.assertEqual(counts.eq(pd.Series([1] * 3 + [0] * 5)).sum(), 8)

        combined = create_row_diffs_mask(masks[:4])
        counts = create_row_diff_counts(masks[:4])
        self.assertEqual(combined.eq(expected4).sum(), 8)
        self.assertEqual(counts.eq(pd.Series([1] * 4 + [0] * 4)).sum(), 8)

        combined = create_row_diffs_mask(masks[:5])
        counts = create_row_diff_counts(masks[:5])
        self.assertEqual(combined.eq(expected5).sum(), 8)
        self.assertEqual(counts.eq(pd.Series([1] * 5 + [0] * 3)).sum(), 8)

        combined = create_row_diffs_mask(masks[:6])
        counts = create_row_diff_counts(masks[:6])
        self.assertEqual(combined.eq(expected6).sum(), 8)
        self.assertEqual(counts.eq(pd.Series([1] * 6 + [0] * 2)).sum(), 8)

        combined = create_row_diffs_mask(masks[:7])
        counts = create_row_diff_counts(masks[:7])
        self.assertEqual(combined.eq(expected7).sum(), 8)
        self.assertEqual(counts.eq(pd.Series([1] * 7 + [0])).sum(), 8)

        combined = create_row_diffs_mask(masks)
        counts = create_row_diff_counts(masks)
        self.assertEqual(combined.eq(expected8).sum(), 8)
        self.assertEqual(counts.eq(pd.Series([1] * 8)).sum(), 8)

        expecteds = [
            expected1, expected2, expected3, expected4,
            expected5, expected6, expected7, expected8
        ]
        counts = create_row_diff_counts(expecteds)
        c87654321 = pd.Series([8, 7, 6, 5, 4, 3, 2, 1])
        self.assertEqual(counts.eq(c87654321).sum(), 8)

        m_evens = pd.Series([t, f, t, f, t, f, t, f])
        m_odds  = pd.Series([f, t, f, t, f, t, f, t])
        m11111111 = pd.Series([t, t, t, t, t, t, t, t])
        c11111111 = pd.Series([1] * 8)

        odd_even = [m_odds, m_evens]
        combined = create_row_diffs_mask(odd_even)
        counts = create_row_diff_counts(odd_even)
        self.assertEqual(combined.eq(m11111111).sum(), 8)
        self.assertEqual(counts.eq(pd.Series(c11111111)).sum(), 8)


def four_squares():
    return pd.DataFrame({
        'row': [0, 1, 2, 3],
        'squares': [0, 1, 4, 9],
    })


def four_squares_and_ten():
    return pd.DataFrame({
        'row': [0, 1, 2, 3],
        'squares': [0, 1, 10, 9],
    })

def write_ref():
    df = four_squares()
    df.to_parquet(PQ_REF4_PATH, index=False)
    df.to_csv(CSV_REF4_PATH, index=False)

def fp(path):
    return os.path.join(TESTDATA, path)


if __name__ == '__main__':
    # write_ref()              # generate test files
    ReferenceTestCase.main()
