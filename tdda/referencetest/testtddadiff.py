import os
import sys

import pandas as pd
import polars as pl

from rich.console import Console
from rich.terminal_theme import (
    MONOKAI,
    DIMMED_MONOKAI,
    SVG_EXPORT_THEME,
    DEFAULT_TERMINAL_THEME,
)

from tdda.abstractdf import col_names, df_add_named_col_with_values
from tdda.config import Config
from tdda.referencetest import ReferenceTestCase, tag
from tdda.referencetest.captureoutput import capture_output

from tdda.referencetest.ddiff import (
    ddiff_helper,
)
from tdda.referencetest.diffutils import (
    check_is_usable_key,
    find_common_key,
    find_usable_key,
)

from tdda.state import reset_config
from tdda.utils import swap_ext, rprint

from tdda.referencetest.test_diff_book_sd1 import *

REFTESTDIR = os.path.dirname(__file__)  # tdda.referencetest
TDDADIR = os.path.dirname(REFTESTDIR)  # tdda
EXDIR = os.path.join(
    REFTESTDIR, 'diffexamples'
)  # tdda/referencetest/diffexamples
REFDIR = os.path.join(
    REFTESTDIR, 'testdata', 'diff'
)  # tdda/referencetest/testdata/diff
BASEDIR = os.path.dirname(TDDADIR)  # parent of tdda (repo)
DOCDIR = os.path.join(BASEDIR, 'doc')  # tdda/doc
SVGDIR = os.path.join(DOCDIR, 'svg', 'diff')  # tdda/doc/svg/diff


# rich changed table title centering between versions; ignore the title line
RICH_TITLE_PAT = ['Value Differences (all rows with differences)']

GENSVG = 'GENSVG' in os.environ  # Set env var GENSVG to regenerate SVG output
if GENSVG:
    rprint(
        '\n[green]*** REGENERATING DOC SVGs for TDDA DIFF ***[/green]\n',
        file=sys.stderr,
    )


def inpath(filename):
    return os.path.join(EXDIR, filename)


def refpath(filename):
    return os.path.join(REFDIR, filename)


def svgpath(filename):
    return os.path.join(SVGDIR, swap_ext(filename, '.svg'))


class TestTDDADiff(ReferenceTestCase):
    # HELPERS

    def diff(self, args, console=None):
        """Helper for tdda diff tests"""
        with capture_output() as c:
            try:
                ddiff_helper(args, config=Config(testing=True), console=console)
                exit_code = 0
            except SystemExit as e:
                exit_code = e.code
            result = str(c)
        return result, exit_code

    def difftest(self, left, right, flags=None, flagpart=None, width=80):
        L, R = inpath(left), inpath(right)
        if flagpart is None and flags is not None:
            flagpart = '_'.join(f.replace(' ', '_') for f in flags)
        elif flags is not None:
            assert isinstance(flags, list) or isinstance(flags, tuple)
        suffix = f'_{flagpart}' if flagpart else ''
        filename = f'{left}_{right}{suffix}.txt'
        expected = refpath(filename)
        console = Console(
            highlight=False,
            soft_wrap=True,
            width=width,
            record=True,
            force_terminal=True,
        )
        args = [L, R] + (flags or [])
        targs = [left, right] + (flags or [])
        actual, exit_code = self.diff(args, console=console)
        title = ' '.join(['tdda diff'] + targs)
        if GENSVG:
            console.save_svg(
                svgpath(filename), title=title, theme=DIMMED_MONOKAI
            )
        self.assertStringCorrect(actual, expected, ignore_lines=RICH_TITLE_PAT)
        return actual

    # IDENTICAL FILES a vs a

    def test_a_csv_a_csv(self):
        """Diff aginst self: should be empty"""
        actual = self.difftest('a.csv', 'a.csv')

        # result should be empty!
        self.assertEqual(actual, '')

    def test_a_parquet_a_parquet(self):
        """Diff aginst self: should be empty"""
        actual = self.difftest('a.parquet', 'a.parquet')

        # result should be empty!
        self.assertEqual(actual, '')

    # VERY SIMPLE A vs B: two diffs

    def test_a_csv_b_csv(self):
        """Most basic diff of two CSV files with two diffs"""
        actual = self.difftest('a.csv', 'b.csv')
        self.assertIn(
            'Total number of different values: 2 of 24 (8.33%).', actual
        )

    def test_a_tsv_b_tsv(self):
        """Diff aginst self: should be empty"""
        actual = self.difftest('a.tsv', 'b.tsv')

        # Should also be same result as for csv
        self.assertStringCorrect(actual, refpath('a.csv_b.csv.txt'))

    def test_a_psv_b_psv(self):
        """Most basic diff of two CSV files with two diffs"""
        actual = self.difftest('a.psv', 'b.psv')

        # Should also be same result as for csv
        self.assertStringCorrect(actual, refpath('a.csv_b.csv.txt'))

    def test_a_parquet_b_parquet(self):
        """Most basic diff of two CSV files with two diffs"""
        actual = self.difftest('a.parquet', 'b.parquet')

        # Should also be same result as for csv
        self.assertStringCorrect(actual, refpath('a.csv_b.csv.txt'))

    # SINGLE COLUMN FILES

    def test_s1_csv_s2_csv(self):
        """Single column string data with 2 diffs"""
        actual = self.difftest('s1.csv', 's2.csv')
        self.assertIn(
            'Total number of different values: 2 of 3 (66.67%).', actual
        )

    # CROSS-TYPE

    def test_a_csv_b_parquet(self):
        """CSV against parquet"""
        actual = self.difftest('a.csv', 'b.parquet')

        # Should also be same result as for csv
        self.assertStringCorrect(actual, refpath('a.csv_b.csv.txt'))

    def test_a_parquet_b_csv(self):
        """Parquet against csv"""
        actual = self.difftest('a.parquet', 'b.csv')

        # Should also be same result as for csv
        self.assertStringCorrect(actual, refpath('a.csv_b.csv.txt'))

    # NUMERIC DIFFERENCES

    def test_a_csv_c_csv(self):
        """One different floating-point value: fails"""
        actual = self.difftest('a.csv', 'c.csv')

    def test_a_csv_c_csv_2dp_prec(self):
        """One different floating-point value: 2dp: passes"""
        actual = self.difftest('a.csv', 'c.csv', ['--precision', '2'])
        self.assertEqual(actual, '')

    # DATE DIFFERENCES

    def test_a_csv_d_csv(self):
        """One different date value: fails"""
        actual = self.difftest('a.csv', 'd.csv')
        self.assertIn(
            'Total number of different values: 1 of 24 (4.17%).', actual
        )

    # DIFFERENT NUMBER OF ROWS

    def test_a_csv_f5_tsv(self):
        """One extra row"""
        actual = self.difftest('a.csv', 'f5.tsv', width=154)

    def test_a_csv_f5_3f_tsv(self):
        """One extra row and 2 diffs"""
        actual = self.difftest('a.csv', 'f5-3d.tsv', width=164)

    def test_f5_3f_tsv_a_csv(self):
        """One extra row and 2 diffs, reversed"""
        actual = self.difftest('f5-3d.tsv', 'a.csv', width=164)

    def test_a_csv_f5_3f_tsv_vertical(self):
        """One extra row"""
        self.difftest('a.csv', 'f5-3d.tsv', ['--vertical'], width=82)
        # test against same file
        self.difftest('a.csv', 'f5-3d.tsv', ['-V'], '--vertical', width=82)

    def test_a_tsv_f5_tsv_join(self):
        """One extra row, with join key"""
        self.difftest('a.csv', 'f5.tsv', ['--key', 'row'], width=120)

    def test_a_tsv_f5_tsv_join_polars(self):
        """One extra row, with join key"""
        self.difftest(
            'a.csv', 'f5.tsv', ['--key', 'row', '--polars'], width=120
        )

    def test_f5_3d_tsv_a_tsv_join(self):
        """One extra row, with join key"""
        self.difftest('f5-3d.tsv', 'a.tsv', ['--key', 'row'], width=130)

    def test_f5_3d_tsv_f5_tsv_join_polars(self):
        """One extra row, with join key"""
        self.difftest(
            'f5-3d.tsv', 'a.tsv', ['--key', 'row', '--polars'], width=130
        )


class TestKeyFunctions:
    __test__ = False
    def testIsUsableKey(self):
        dfL = df_add_named_col_with_values(
            self.read_parquet(inpath('a.parquet')),
            'small',
            [i // 2 for i in range(4)],
        )
        dfR = df_add_named_col_with_values(
            self.read_parquet(inpath('b.parquet')),
            'small',
            [1 - (i // 2) for i in range(4)],
        )

        # All except even, small are usable
        for key in ('row', 'sq', 'recip', 'date'):
            self.assertEqual(
                (key, check_is_usable_key(dfL, dfR, key)), (key, True)
            )
        # even, small not usable
        self.assertEqual(check_is_usable_key(dfL, dfR, 'even'), False)
        self.assertEqual(check_is_usable_key(dfL, dfR, 'small'), False)

        # even, small usable as combination key
        self.assertTrue(check_is_usable_key(dfL, dfR, ['even', 'small']))

        # Exception if col doesn't exist.
        # Different exceptions for Polars/Pandas
        # Possibly not worth testing...

    def testFindUsableKeySameLen(self):
        dfL = self.read_parquet(inpath('a.parquet'))
        dfR = self.read_parquet(inpath('b.parquet'))
        fields = ['row', 'sq', 'recip', 'name', 'even', 'date']
        # None
        key = find_usable_key(self.is_pandas, dfL, dfR)
        left, right, key = find_usable_key(self.is_pandas, dfL, dfR, key=None)
        self.assertIsNone(key)

        expected = fields
        self.assertEqual(col_names(left), expected)
        self.assertEqual(col_names(right), expected)

        # True (unchanged)
        left, right, key = find_usable_key(self.is_pandas, dfL, dfR, key=True)
        self.assertEqual(key, 'row')  # first usable key
        self.assertEqual(col_names(left), fields)
        self.assertEqual(col_names(right), fields)

        # True (remove row)
        L = dfL[fields[1:]]
        R = dfR[fields[1:]]
        left, right, key = find_usable_key(self.is_pandas, L, R, key=True)
        self.assertEqual(key, 'sq')  # first usable key
        self.assertEqual(col_names(left), fields[1:])
        self.assertEqual(col_names(right), fields[1:])

        # True (nothing good)
        L = dfL[['even']]
        R = dfR[['even']]
        left, right, key = find_usable_key(
            self.is_pandas, L, R, key=True, verbosity=0
        )  # suppress warning
        self.assertIsNone(key)  # first usable key
        self.assertEqual(col_names(left), ['even'])
        self.assertEqual(col_names(right), ['even'])

        # row
        left, right, key = find_usable_key(self.is_pandas, dfL, dfR, key='row')
        self.assertEqual(key, 'row')  # first usable key
        self.assertEqual(col_names(left), fields)
        self.assertEqual(col_names(right), fields)

    def testFindUsableKeyDifferentLengths(self):
        dfL = self.read_parquet(inpath('a.parquet'))
        dfR2 = self.read_parquet(inpath('f5.parquet'))
        fields = ['row', 'sq', 'recip', 'name', 'even', 'date']
        left, right, key = find_usable_key(
            self.is_pandas, dfL, dfR2, key='row'
        )
        self.assertEqual(key, 'row')  # first usable key
        self.assertEqual(col_names(left), fields)
        self.assertEqual(col_names(right), fields)


class TestKeyFunctionsPandas(TestKeyFunctions, ReferenceTestCase):
    __test__ = True
    is_pandas = True

    def read_parquet(self, *args, **kw):
        return pd.read_parquet(*args, **kw)


class TestKeyFunctionsPolars(TestKeyFunctions, ReferenceTestCase):
    __test__ = True
    is_pandas = False

    def read_parquet(self, *args, **kw):
        return pl.read_parquet(*args, **kw)


if __name__ == '__main__':
    TDDA_CONFIG_TESTS = 'TDDA_CONFIG_TESTS' in os.environ
    ReferenceTestCase.main(testtdda=1)
