import os

import polars as pl

from rich import print as rprint
from rich.console import Console

from tdda.abstractdf import col_names
from tdda.config import Config
from tdda.referencetest import ReferenceTestCase, tag
from tdda.referencetest.utils import diff_parquet_pattern, normalise_rich_table
from tdda.referencetest.referencetest import ReferenceTest
from tdda.referencetest.basecomparison import (
    DataFrameDiffs,
    create_row_diffs_mask,
)
from tdda.referencetest.checkpolars import (
    PolarsComparison,
    same_structure_dataframe_diffs,
)
from tdda.referencetest.diffutils import (
    check_is_usable_key,
    create_row_diff_counts,
    find_common_key,
    single_col_diffs,
)


TESTDATA = os.path.join(os.path.dirname(__file__), 'testdata')
PQ_REF4_PATH = os.path.join(TESTDATA, 'four-squares.parquet')
CSV_REF4_PATH = os.path.join(TESTDATA, 'four-squares.csv')


class TestPolarsDataFrameComparisons(ReferenceTestCase):
    norm_paths = True
    f, t = False, True
    m10000000 = pl.Series([t, f, f, f, f, f, f, f])
    m01000000 = pl.Series([f, t, f, f, f, f, f, f])
    m00100000 = pl.Series([f, f, t, f, f, f, f, f])
    m00010000 = pl.Series([f, f, f, t, f, f, f, f])
    m00001000 = pl.Series([f, f, f, f, t, f, f, f])
    m00000100 = pl.Series([f, f, f, f, f, t, f, f])
    m00000010 = pl.Series([f, f, f, f, f, f, t, f])
    m00000001 = pl.Series([f, f, f, f, f, f, f, t])

    expected1 = pl.Series([t, f, f, f, f, f, f, f])
    expected2 = pl.Series([t, t, f, f, f, f, f, f])
    expected3 = pl.Series([t, t, t, f, f, f, f, f])
    expected4 = pl.Series([t, t, t, t, f, f, f, f])
    expected5 = pl.Series([t, t, t, t, t, f, f, f])
    expected6 = pl.Series([t, t, t, t, t, t, f, f])
    expected7 = pl.Series([t, t, t, t, t, t, t, f])
    expected8 = pl.Series([t, t, t, t, t, t, t, t])

    expected1r = pl.Series(reversed([t, f, f, f, f, f, f, f]))
    expected2r = pl.Series(reversed([t, t, f, f, f, f, f, f]))
    expected3r = pl.Series(reversed([t, t, t, f, f, f, f, f]))
    expected4r = pl.Series(reversed([t, t, t, t, f, f, f, f]))
    expected5r = pl.Series(reversed([t, t, t, t, t, f, f, f]))
    expected6r = pl.Series(reversed([t, t, t, t, t, t, f, f]))
    expected7r = pl.Series(reversed([t, t, t, t, t, t, t, f]))

    def testNoDiffsInMem(self):
        self.assertDataFramesEqual(four_squares(), four_squares())

    def testNoDiffsMemParquet(self):
        self.assertDataFrameCorrect(four_squares(), PQ_REF4_PATH)

    def testNoDiffsMemCSV(self):
        self.assertDataFrameCorrect(four_squares(), CSV_REF4_PATH)

    def testNoDiffsParquetParquet(self):
        self.assertOnDiskDataFrameCorrect(
            PQ_REF4_PATH, PQ_REF4_PATH, engine='polars'
        )

    def testNoDiffsParquetCSV(self):
        self.assertOnDiskDataFrameCorrect(
            PQ_REF4_PATH, CSV_REF4_PATH, engine='polars'
        )

    def testNoDiffsCSVParquet(self):
        self.assertOnDiskDataFrameCorrect(
            CSV_REF4_PATH, PQ_REF4_PATH, engine='polars'
        )

    def testNoDiffsCSVCSV(self):
        self.assertOnDiskDataFrameCorrect(
            CSV_REF4_PATH, CSV_REF4_PATH, engine='polars'
        )

    def testOneDiffInMem(self):
        c = PolarsComparison(verbose=False)
        ref = four_squares()
        actual = four_squares_and_ten()
        c.verbose = False
        r = c.check_dataframe(actual, ref)
        self.assertEqual(r.failures, 1)
        self.assertStringCorrect(
            str(r.diffs),
            fp('one-diff-in-mem.txt'),
            ignore_patterns=[
                diff_parquet_pattern()
            ],
        )

    def testDiffColTypeInMemIntStr(self):
        c = PolarsComparison(verbose=False)
        actual = four_squares()
        actual = actual.with_columns(
            pl.Series([str(sq) for sq in actual['nsq']]).alias('nsq')
        )
        expected = four_squares()
        r = c.check_dataframe(actual, expected)
        self.assertEqual(r.failures, 1)
        self.assertStringCorrect(
            str(r.diffs),
            fp('diff-col-types-int-str.txt'),
            ignore_patterns=[
                diff_parquet_pattern(),
                r'(object|String)',
                r'[Ii]nt64',
            ],
        )
        self.assertStringCorrect(
            str(r.diffs.dfd),
            fp('ddiff-col-types-int-str.txt'),
            ignore_patterns=[
                r'(object|String)',
                r'[Ii]nt64',
            ],
        )

    def testDiffColTypeInMemIntFloat(self):
        c = PolarsComparison(verbose=False)
        actual = four_squares()
        actual = actual.with_columns(
            pl.Series([float(sq) for sq in actual['nsq']]).alias('nsq')
        )

        expected = four_squares()
        r = c.check_dataframe(actual, expected)
        self.assertEqual(r.failures, 1)
        self.assertStringCorrect(
            str(r.diffs),
            fp('diff-col-types-int-float.txt'),
            ignore_patterns=[
                diff_parquet_pattern(),
                r'[Ff]loat64',
                r'[Ii]nt64',
            ],
        )
        self.assertStringCorrect(
            str(r.diffs.dfd),
            fp('ddiff-col-types-int-float.txt'),
            ignore_patterns=[
                r'[Ff]loat64',
                r'[Ii]nt64',
            ],
        )

    def testDiffColOrderInMem(self):
        c = PolarsComparison(verbose=False)
        ref = four_squares()
        actual = pl.DataFrame(
            {
                'nsq': ref['nsq'],
                'n': ref['n'],
            }
        )
        self.assertEqual(list(reversed(col_names(actual))), col_names(ref))
        r = c.check_dataframe(actual, ref)
        self.assertEqual(r.failures, 1)
        self.assertStringCorrect(
            str(r.diffs),
            fp('diff-col-order.txt'),
            ignore_patterns=[
                diff_parquet_pattern()
            ],
        )

        self.assertStringCorrect(str(r.diffs.dfd), fp('ddiff-col-order.txt'))

    def testSingleColDiffs(self):
        df = pl.DataFrame(
            {
                'a': pl.Series([0, 1, None, None], dtype=pl.Int64),
                'b': pl.Series([0, None, 2, None], dtype=pl.Int64),
                'A': [0, 1, None, None],
                'B': [0, None, 2, None],
                'm': [False, True, True, False],
            }
        )
        diffs = single_col_diffs(df['A'], df['B'])
        self.assertTrue(diffs.mask.eq(df['m']).all())
        self.assertEqual(diffs.n, 2)

        diffs = single_col_diffs(df['b'], df['a'])
        self.assertTrue(diffs.mask.eq(df['m']).all())
        self.assertEqual(diffs.n, 2)

    def testCreateRowDiffsMaskAndCounts(self):
        f, t = False, True

        masks = [
            self.m10000000,
            self.m01000000,
            self.m00100000,
            self.m00010000,
            self.m00001000,
            self.m00000100,
            self.m00000010,
            self.m00000001,
        ]

        combined = create_row_diffs_mask(masks[:1])
        counts = create_row_diff_counts(masks[:1])
        self.assertEqual(combined.eq(self.expected1).sum(), 8)
        self.assertEqual(counts.eq(pl.Series([1] + [0] * 7)).sum(), 8)

        combined = create_row_diffs_mask(masks[:2])
        counts = create_row_diff_counts(masks[:2])
        self.assertEqual(combined.eq(self.expected2).sum(), 8)
        self.assertEqual(counts.eq(pl.Series([1] * 2 + [0] * 6)).sum(), 8)

        combined = create_row_diffs_mask(masks[:3])
        counts = create_row_diff_counts(masks[:3])
        self.assertEqual(combined.eq(self.expected3).sum(), 8)
        self.assertEqual(counts.eq(pl.Series([1] * 3 + [0] * 5)).sum(), 8)

        combined = create_row_diffs_mask(masks[:4])
        counts = create_row_diff_counts(masks[:4])
        self.assertEqual(combined.eq(self.expected4).sum(), 8)
        self.assertEqual(counts.eq(pl.Series([1] * 4 + [0] * 4)).sum(), 8)

        combined = create_row_diffs_mask(masks[:5])
        counts = create_row_diff_counts(masks[:5])
        self.assertEqual(combined.eq(self.expected5).sum(), 8)
        self.assertEqual(counts.eq(pl.Series([1] * 5 + [0] * 3)).sum(), 8)

        combined = create_row_diffs_mask(masks[:6])
        counts = create_row_diff_counts(masks[:6])
        self.assertEqual(combined.eq(self.expected6).sum(), 8)
        self.assertEqual(counts.eq(pl.Series([1] * 6 + [0] * 2)).sum(), 8)

        combined = create_row_diffs_mask(masks[:7])
        counts = create_row_diff_counts(masks[:7])
        self.assertEqual(combined.eq(self.expected7).sum(), 8)
        self.assertEqual(counts.eq(pl.Series([1] * 7 + [0])).sum(), 8)

        combined = create_row_diffs_mask(masks)
        counts = create_row_diff_counts(masks)
        self.assertEqual(combined.eq(self.expected8).sum(), 8)
        self.assertEqual(counts.eq(pl.Series([1] * 8)).sum(), 8)

        expecteds = [
            self.expected1,
            self.expected2,
            self.expected3,
            self.expected4,
            self.expected5,
            self.expected6,
            self.expected7,
            self.expected8,
        ]
        counts = create_row_diff_counts(expecteds)
        c87654321 = pl.Series([8, 7, 6, 5, 4, 3, 2, 1])
        self.assertEqual(counts.eq(c87654321).sum(), 8)

        m_evens = pl.Series([t, f, t, f, t, f, t, f])
        m_odds = pl.Series([f, t, f, t, f, t, f, t])
        m11111111 = pl.Series([t, t, t, t, t, t, t, t])
        c11111111 = pl.Series([1] * 8)

        odd_even = [m_odds, m_evens]
        combined = create_row_diffs_mask(odd_even)
        counts = create_row_diff_counts(odd_even)
        self.assertEqual(combined.eq(m11111111).sum(), 8)
        self.assertEqual(counts.eq(pl.Series(c11111111)).sum(), 8)

    def testSameStructureDataFrameDiffs1(self):
        ref_df = pl.DataFrame(
            {
                f'c{i}': [1 << n if n != i else 0 for n in range(8)]
                for i in range(8)
            }
        )
        # ref_df
        # c0   c1   c2   c3   c4   c5   c6  c7
        # 0    0    1    1    1    1    1    1   1
        # 1    2    0    2    2    2    2    2   2
        # 2    4    4    0    4    4    4    4   4
        # 3    8    8    8    0    8    8    8   8
        # 4   16   16   16   16    0   16   16  16
        # 5   32   32   32   32   32    0   32  32
        # 6   64   64   64   64   64   64    0  64
        # 7  128  128  128  128  128  128  128   0

        dfa = pl.DataFrame(
            {
                f'c{i}': [
                    1 << n if n != i and 7 - n != i else 0 for n in range(8)
                ]
                for i in range(8)
            }
        )

        # dfa
        #    c0   c1   c2   c3   c4   c5   c6  c7
        # 0   0    1    1    1    1    1    1   0
        # 1   2    0    2    2    2    2    0   2
        # 2   4    4    0    4    4    0    4   4
        # 3   8    8    8    0    0    8    8   8
        # 4  16   16   16    0    0   16   16  16
        # 5  32   32    0   32   32    0   32  32
        # 6  64    0   64   64   64   64    0  64
        # 7   0  128  128  128  128  128  128   0

        dfb = pl.DataFrame(
            {
                f'c{i}': [1 << n if n <= i else 0 for n in range(8)]
                for i in range(8)
            }
        )
        # dfb
        #    c0  c1  c2  c3  c4  c5  c6   c7
        # 0   1   1   1   1   1   1   1    1
        # 1   0   2   2   2   2   2   2    2
        # 2   0   0   4   4   4   4   4    4
        # 3   0   0   0   8   8   8   8    8
        # 4   0   0   0   0  16  16  16   16
        # 5   0   0   0   0   0  32  32   32
        # 6   0   0   0   0   0   0  64   64
        # 7   0   0   0   0   0   0   0  128

        # First test: dfa vs ref_df

        config = Config(testing=True)
        ddiff = same_structure_dataframe_diffs(dfa, ref_df, config=Config())
        self.assertEqual(ddiff.n_diff_values, 8)  # 8 diff values in total
        self.assertEqual(ddiff.n_diff_cols, 8)  # 8 diff cols in total
        self.assertEqual(ddiff.n_diff_rows, 8)  # 8 diff cols in total
        rdc = ddiff.row_diff_counts

        # Check every row has one differnce
        ones = pl.Series([1] * 8)
        self.assertEqual((rdc.rowdiffs == ones).sum(), 8)

        expected = pl.DataFrame(
            {
                'c0': self.m00000001,
                'c1': self.m00000010,
                'c2': self.m00000100,
                'c3': self.m00001000,
                'c4': self.m00010000,
                'c5': self.m00100000,
                'c6': self.m01000000,
                'c7': self.m10000000,
            }
        )
        self.assertTrue(ddiff.diff_df.equals(expected))

        # First test: dfb vs ref_df
        config = Config(testing=True)
        ddiff = same_structure_dataframe_diffs(dfb, ref_df, config=config)
        self.assertEqual(ddiff.n_diff_values, 36)  # UR different
        self.assertEqual(ddiff.n_diff_cols, 8)  # 8 diff cols in total
        self.assertEqual(ddiff.n_diff_rows, 8)  # 8 diff cols in total
        rdc = ddiff.row_diff_counts

        s18 = pl.Series(range(1, 9))
        self.assertEqual((rdc.rowdiffs == s18).sum(), 8)
        expected = pl.DataFrame(
            {
                'c0': self.expected8,
                'c1': self.expected7r,
                'c2': self.expected6r,
                'c3': self.expected5r,
                'c4': self.expected4r,
                'c5': self.expected3r,
                'c6': self.expected2r,
                'c7': self.expected1r,
            }
        )
        self.assertTrue(ddiff.diff_df.equals(expected))

    def testSameStructureDataFrameDiffs2(self):
        ref_df = pl.DataFrame(
            {
                'a': [1, 2, 3],
                'b': ['one', 'two', 'three'],
                'c': [1.0, 2.0, 3.0],
                'd': [False, True, False],
            }
        )

        df = pl.DataFrame(
            {
                'a': [3, 2, 1],  # two diffs
                'b': ['one', 'two', 'three'],  # same
                'c': [1.0, None, 3.0],  # one diff
                'd': [True, True, False],  # one diff
            }
        )

        config = Config(testing=True)
        ddiff = same_structure_dataframe_diffs(df, ref_df, config=config)
        self.assertEqual(ddiff.n_diff_values, 4)
        self.assertEqual(ddiff.n_diff_cols, 3)
        self.assertEqual(ddiff.n_diff_rows, 3)
        rdc = ddiff.row_diff_counts
        self.assertEqual((rdc.rowdiffs == pl.Series([2, 1, 1])).sum(), 3)
        expected = pl.DataFrame(
            {
                'a': pl.Series([True, False, True]),
                'c': pl.Series([False, True, False]),
                'd': pl.Series([True, False, False]),
            }
        )
        self.assertTrue(ddiff.diff_df.equals(expected))

    def test_ddiff_values_output(self):
        df = four_squares()
        rdf = four_squares_and_ten()
        config = Config(testing=True)
        diff = same_structure_dataframe_diffs(df, rdf, config=config)
        table = diff.details_table(df, rdf)
        result = rich_capture(table)
        self.assertStringCorrect(
            str(diff), fp('ddiff-1-details.txt'), ignore_patterns=[r'[iI]nt64']
        )
        self.assertStringCorrect(
            result, fp('ddiff-1-rich-table.txt'), ignore_patterns=[r'[iI]nt64'],
            preprocess=normalise_rich_table,
        )


def four_squares():
    return pl.DataFrame(
        {
            'n': [0, 1, 2, 3],
            'nsq': [0, 1, 4, 9],
        }
    )


def four_squares_and_ten():
    return pl.DataFrame(
        {
            'n': [0, 1, 2, 3],
            'nsq': [0, 1, 10, 9],
        }
    )


def write_ref():
    df = four_squares()
    df.to_parquet(PQ_REF4_PATH, index=False)
    df.to_csv(CSV_REF4_PATH, index=False)


def fp(path):
    return os.path.join(TESTDATA, path)


def rich_capture(content):
    console = Console(force_terminal=True)
    with console.capture() as capture:
        console.print(content)
    return capture.get()


if __name__ == '__main__':
    # write_ref()              # generate test files
    ReferenceTestCase.main(testtdda=1)
