import os

import pandas as pd

from rich import print as rprint
from rich.console import Console

from tdda.config import Config
from tdda.referencetest import ReferenceTestCase, tag
from tdda.referencetest.referencetest import ReferenceTest
from tdda.referencetest.checkpandas import (
    PandasComparison,
    same_structure_dataframe_diffs,
)
from tdda.referencetest.basecomparison import (
    DataFrameDiffs,
    create_row_diffs_mask,
)
from tdda.referencetest.diffutils import (
    check_is_usable_key,
    create_row_diff_counts,
    find_common_key,
    single_col_diffs,
)
from tdda.serial import csv_to_pandas
from tdda.utils import nvl


TESTDATA = os.path.join(os.path.dirname(__file__), 'testdata')
PQ_REF4_PATH = os.path.join(TESTDATA, 'four-squares.parquet')
CSV_REF4_PATH = os.path.join(TESTDATA, 'four-squares.csv')
TDDADIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
CTESTDATA = os.path.join(TDDADIR, 'constraints', 'testdata')

E92PATH = os.path.join(CTESTDATA, 'elements92.csv')
E118PATH = os.path.join(CTESTDATA, 'elements118.csv')


class TestPandasDataFrameComparisons(ReferenceTestCase):
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

    expected1r = pd.Series(reversed([t, f, f, f, f, f, f, f]))
    expected2r = pd.Series(reversed([t, t, f, f, f, f, f, f]))
    expected3r = pd.Series(reversed([t, t, t, f, f, f, f, f]))
    expected4r = pd.Series(reversed([t, t, t, t, f, f, f, f]))
    expected5r = pd.Series(reversed([t, t, t, t, t, f, f, f]))
    expected6r = pd.Series(reversed([t, t, t, t, t, t, f, f]))
    expected7r = pd.Series(reversed([t, t, t, t, t, t, t, f]))

    def testNoDiffsInMem(self):
        self.assertDataFramesEqual(four_squares(), four_squares())

    def testNoDiffsMemParquet(self):
        self.assertDataFrameCorrect(
            four_squares(), PQ_REF4_PATH, type_matching='medium'
        )

    def testNoDiffsMemCSV(self):
        self.assertDataFrameCorrect(four_squares(), CSV_REF4_PATH, backend='o')

    def testNoDiffsParquetParquet(self):
        self.assertOnDiskDataFrameCorrect(
            PQ_REF4_PATH, PQ_REF4_PATH, engine='pandas'
        )

    def testNoDiffsParquetCSV(self):
        self.assertOnDiskDataFrameCorrect(
            PQ_REF4_PATH,
            CSV_REF4_PATH,
            engine='pandas',
            type_matching='medium',
        )

    def testNoDiffsCSVParquet(self):
        self.assertOnDiskDataFrameCorrect(
            CSV_REF4_PATH,
            PQ_REF4_PATH,
            engine='pandas',
            type_matching='medium',
        )

    def testNoDiffsCSVCSV(self):
        self.assertOnDiskDataFrameCorrect(
            CSV_REF4_PATH, CSV_REF4_PATH, engine='pandas'
        )

    def testOneDiffInMem(self):
        c = PandasComparison(verbose=False)
        ref = four_squares()
        actual = four_squares_and_ten()
        c.verbose = False
        r = c.check_dataframe(actual, ref)
        self.assertEqual(r.failures, 1)
        self.assertStringCorrect(
            str(r.diffs),
            fp('one-diff-in-mem.txt'),
            ignore_patterns=[
                r'diff .*/actual-df\d{3}.parquet .*/expected-df\d{3}.parquet'
            ],
        )

    def testDiffColTypeInMemIntStr(self):
        c = PandasComparison(verbose=False)
        actual = four_squares()
        actual['nsq'] = [str(sq) for sq in actual['nsq']]
        expected = four_squares()
        r = c.check_dataframe(actual, expected)
        self.assertEqual(r.failures, 1)
        self.assertStringCorrect(
            str(r.diffs),
            fp('diff-col-types-int-str.txt'),
            ignore_patterns=[
                r'diff .*/actual-df\d{3}.parquet .*/expected-df\d{3}.parquet',
                r'(str|object)',
            ],
        )
        self.assertStringCorrect(
            str(r.diffs.dfd),
            fp('ddiff-col-types-int-str.txt'),
            ignore_patterns=[r'(str|object)'],
        )

    def testDiffColTypeInMemIntFloat(self):
        c = PandasComparison(verbose=False)
        actual = four_squares()
        actual['nsq'] = [float(sq) for sq in actual['nsq']]
        expected = four_squares()
        r = c.check_dataframe(actual, expected)
        self.assertEqual(r.failures, 1)
        self.assertStringCorrect(
            str(r.diffs),
            fp('diff-col-types-int-float.txt'),
            ignore_patterns=[
                r'diff .*/actual-df\d{3}.parquet .*/expected-df\d{3}.parquet'
            ],
        )
        self.assertStringCorrect(
            str(r.diffs.dfd), fp('ddiff-col-types-int-float.txt')
        )

    def testDiffColOrderInMem(self):
        c = PandasComparison(verbose=False)
        ref = four_squares()
        actual = pd.DataFrame(
            {
                'nsq': ref['nsq'],
                'n': ref['n'],
            }
        )
        self.assertEqual(list(reversed(list(actual))), list(ref))
        r = c.check_dataframe(actual, ref)
        self.assertEqual(r.failures, 1)
        self.assertStringCorrect(
            str(r.diffs),
            fp('diff-col-order.txt'),
            ignore_patterns=[
                r'diff .*/actual-df\d{3}.parquet .*/expected-df\d{3}.parquet'
            ],
        )

        self.assertStringCorrect(str(r.diffs.dfd), fp('ddiff-col-order.txt'))

    def testSingleColDiffs(self):
        df = pd.DataFrame(
            {
                'a': pd.Series([0, 1, None, None], dtype=pd.Int64Dtype()),
                'b': pd.Series([0, None, 2, None], dtype=pd.Int64Dtype()),
                'A': [0, 1, None, None],
                'B': [0, None, 2, None],
                'm': [False, True, True, False],
            }
        )
        diffs = single_col_diffs(df.A, df.B)
        self.assertTrue(diffs.mask.eq(df.m).all())
        self.assertEqual(diffs.n, 2)

        diffs = single_col_diffs(df.b, df.a)
        self.assertTrue(diffs.mask.eq(df.m).all())
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
        self.assertEqual(counts.eq(pd.Series([1] + [0] * 7)).sum(), 8)

        combined = create_row_diffs_mask(masks[:2])
        counts = create_row_diff_counts(masks[:2])
        self.assertEqual(combined.eq(self.expected2).sum(), 8)
        self.assertEqual(counts.eq(pd.Series([1] * 2 + [0] * 6)).sum(), 8)

        combined = create_row_diffs_mask(masks[:3])
        counts = create_row_diff_counts(masks[:3])
        self.assertEqual(combined.eq(self.expected3).sum(), 8)
        self.assertEqual(counts.eq(pd.Series([1] * 3 + [0] * 5)).sum(), 8)

        combined = create_row_diffs_mask(masks[:4])
        counts = create_row_diff_counts(masks[:4])
        self.assertEqual(combined.eq(self.expected4).sum(), 8)
        self.assertEqual(counts.eq(pd.Series([1] * 4 + [0] * 4)).sum(), 8)

        combined = create_row_diffs_mask(masks[:5])
        counts = create_row_diff_counts(masks[:5])
        self.assertEqual(combined.eq(self.expected5).sum(), 8)
        self.assertEqual(counts.eq(pd.Series([1] * 5 + [0] * 3)).sum(), 8)

        combined = create_row_diffs_mask(masks[:6])
        counts = create_row_diff_counts(masks[:6])
        self.assertEqual(combined.eq(self.expected6).sum(), 8)
        self.assertEqual(counts.eq(pd.Series([1] * 6 + [0] * 2)).sum(), 8)

        combined = create_row_diffs_mask(masks[:7])
        counts = create_row_diff_counts(masks[:7])
        self.assertEqual(combined.eq(self.expected7).sum(), 8)
        self.assertEqual(counts.eq(pd.Series([1] * 7 + [0])).sum(), 8)

        combined = create_row_diffs_mask(masks)
        counts = create_row_diff_counts(masks)
        self.assertEqual(combined.eq(self.expected8).sum(), 8)
        self.assertEqual(counts.eq(pd.Series([1] * 8)).sum(), 8)

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
        c87654321 = pd.Series([8, 7, 6, 5, 4, 3, 2, 1])
        self.assertEqual(counts.eq(c87654321).sum(), 8)

        m_evens = pd.Series([t, f, t, f, t, f, t, f])
        m_odds = pd.Series([f, t, f, t, f, t, f, t])
        m11111111 = pd.Series([t, t, t, t, t, t, t, t])
        c11111111 = pd.Series([1] * 8)

        odd_even = [m_odds, m_evens]
        combined = create_row_diffs_mask(odd_even)
        counts = create_row_diff_counts(odd_even)
        self.assertEqual(combined.eq(m11111111).sum(), 8)
        self.assertEqual(counts.eq(pd.Series(c11111111)).sum(), 8)

    def testSameStructureDataFrameDiffs1(self):
        ref_df = pd.DataFrame(
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

        dfa = pd.DataFrame(
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

        dfb = pd.DataFrame(
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
        ddiff = same_structure_dataframe_diffs(dfa, ref_df, config=config)
        self.assertEqual(ddiff.n_diff_values, 8)  # 8 diff values in total
        self.assertEqual(ddiff.n_diff_cols, 8)  # 8 diff cols in total
        self.assertEqual(ddiff.n_diff_rows, 8)  # 8 diff cols in total
        rdc = ddiff.row_diff_counts

        # Check every row has one differnce
        ones = pd.Series([1] * 8)
        self.assertEqual((rdc.rowdiffs == ones).sum().item(), 8)

        expected = pd.DataFrame(
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

        ddiff = same_structure_dataframe_diffs(dfb, ref_df)
        self.assertEqual(ddiff.n_diff_values, 36)  # UR different
        self.assertEqual(ddiff.n_diff_cols, 8)  # 8 diff cols in total
        self.assertEqual(ddiff.n_diff_rows, 8)  # 8 diff cols in total
        rdc = ddiff.row_diff_counts

        s18 = pd.Series(range(1, 9))
        self.assertEqual((rdc.rowdiffs == s18).sum().item(), 8)
        expected = pd.DataFrame(
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
        ref_df = pd.DataFrame(
            {
                'a': [1, 2, 3],
                'b': ['one', 'two', 'three'],
                'c': [1.0, 2.0, 3.0],
                'd': [False, True, False],
            }
        )

        df = pd.DataFrame(
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
        self.assertEqual(
            (rdc.rowdiffs == pd.Series([2, 1, 1])).sum().item(), 3
        )
        expected = pd.DataFrame(
            {
                'a': pd.Series([True, False, True]),
                'c': pd.Series([False, True, False]),
                'd': pd.Series([True, False, False]),
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
        self.assertStringCorrect(str(diff), fp('ddiff-1-details.txt'))
        self.assertStringCorrect(result, fp('ddiff-1-rich-table.txt'))

    def test_find_common_single_key45(self):
        n4 = n_squares(4)
        n5 = n_squares(5)
        # Different sizes, 'n' (first col) good in each
        self.assertEqual(find_common_key(n4, n5), 'n')
        self.assertEqual(find_common_key(n5, n4), 'n')

    def test_find_common_single_key35(self):
        n4 = n_squares(4)
        n3 = n_squares(5, lambda n: n % 2)

        # Different sizes, 'n' (first col) good in each
        # Some missing in n3

        self.assertEqual(find_common_key(n4, n3), 'n')
        self.assertEqual(find_common_key(n3, n4), 'n')

    def test_find_common_single_key4_dup_str(self):
        # k no good in n4a. Use n.

        n4a = n_squares(4)
        n4a.insert(0, 'k', ['a', 'b', 'c', 'a'])
        n3k = n_squares(3)
        n3k.insert(0, 'k', ['b', 'c', 'd'])

        self.assertEqual(find_common_key(n3k, n4a), 'n')
        self.assertEqual(find_common_key(n4a, n3k), 'n')

    def test_find_common_single_key4_null(self):
        n3k = n_squares(3)
        n3k.insert(0, 'k', ['b', 'c', 'd'])

        # # k is None in n4n
        n4n = n_squares(4)
        n4n.insert(0, 'k', ['a', 'b', 'c', None])

        self.assertEqual(find_common_key(n3k, n4n), 'n')
        self.assertEqual(find_common_key(n4n, n3k), 'n')

    def test_find_common_single_key4_str(self):
        # String key k is usable in both
        n3k = n_squares(3)
        n3k.insert(0, 'k', ['b', 'c', 'z'])
        n4k = n_squares(4)
        n4k.insert(0, 'k', ['a', 'b', 'c', 'd'])

        self.assertEqual(find_common_key(n3k, n4k), 'k')
        self.assertEqual(find_common_key(n4k, n3k), 'k')

    def test_find_common_single_key4_str_dups(self):
        # n has dups; fall back to nsq
        n4 = n_squares(4)
        n4dup = n_squares(4)
        n4dup['n'] = [1, 1, 2, 3]
        self.assertEqual(find_common_key(n4, n4dup), 'nsq')

    def test_find_common_single_elements(self):
        e92 = csv_to_pandas(E92PATH)
        e118 = csv_to_pandas(E118PATH)
        self.assertEqual(find_common_key(e92, e118), 'Z')

        del e92['Z']
        self.assertEqual(find_common_key(e92, e118), 'Name')
        del e118['Name']
        self.assertEqual(find_common_key(e92, e118), 'Symbol')
        del e92['Symbol']
        self.assertIsNone(find_common_key(e92, e118, verbosity=0))

    def test_find_common_dual_key(self):
        e92 = csv_to_pandas(E92PATH)
        e118 = csv_to_pandas(E118PATH)
        e92['Group'] = e92['Group'].fillna(e92['Z'])
        e118['Group'] = e118['Group'].fillna(e118['Z'])
        for k in ('Z', 'Name', 'Symbol'):
            del e92[k]
        self.assertEqual(find_common_key(e92, e118), ['Group', 'Period'])

        del e92['Period']
        del e118['Group']
        self.assertEqual(find_common_key(e92, e118, verbosity=0), None)

        e92 = e92.query('Density > 0').reset_index()
        e118 = e118.query('Density > 0').reset_index()
        self.assertEqual(find_common_key(e92, e118, verbosity=0), 'index')

        del e92['index']
        del e118['index']
        self.assertEqual(
            find_common_key(e92, e118), ['Density', 'AtomicWeight']
        )
        del e118['AtomicWeight']
        self.assertEqual(
            find_common_key(e92, e118), ['Density', 'RelativeAtomicMass']
        )

        del e92['Density']
        self.assertEqual(
            find_common_key(e92, e118), ['RelativeAtomicMass', 'Etymology']
        )
        del e118['Etymology']
        self.assertEqual(find_common_key(e92, e118, verbosity=0), None)

    def test_check_is_usable_key(self):
        e92 = csv_to_pandas(E92PATH)
        e118 = csv_to_pandas(E118PATH)
        self.assertTrue(check_is_usable_key(e92, e118, 'Z'))
        self.assertTrue(check_is_usable_key(e92, e118, 'Name'))
        self.assertTrue(check_is_usable_key(e92, e118, 'Symbol'))

        self.assertFalse(check_is_usable_key(e92, e118, ['Period', 'Group']))
        self.assertFalse(
            check_is_usable_key(e92, e118, ['RelativeAtomicMass', 'Density'])
        )


def n_squares(n=4, filter_fn=None):
    all_true = lambda x: True
    filter_fn = nvl(filter_fn, all_true)

    return pd.DataFrame(
        {
            'n': list(i for i in range(n) if filter_fn(i)),
            'nsq': list(i ^ 2 for i in range(n) if filter_fn(i)),
        }
    )


def four_squares():
    return pd.DataFrame(
        {
            'n': [0, 1, 2, 3],
            'nsq': [0, 1, 4, 9],
        }
    )


def four_squares_and_ten():
    return pd.DataFrame(
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
