import os

from tdda.referencetest import ReferenceTestCase, tag
from tdda.referencetest.captureoutput import capture_output

from tdda.referencetest.ddiff import ddiff_helper
from tdda.state import set_testing

REFTESTDIR = os.path.dirname(__file__)     # tdda.referencetest
TDDADIR = os.path.dirname(REFTESTDIR)      # tdda
EXDIR = os.path.join(REFTESTDIR,
                     'diffexamples')       # tdda/referencetest/diffexamples
REFDIR = os.path.join(REFTESTDIR,
                      'testdata', 'diff')  # tdda/referencetest/testdata/diff

def inpath(filename):
    return os.path.join(EXDIR, filename)


def refpath(filename):
    return os.path.join(REFDIR, filename)


class TestTDDADiff(ReferenceTestCase):

    # HELPERS

    def diff(self, args):
        """Helper for tdda diff tests"""
        with capture_output() as c:
            ddiff_helper(args)
            result = str(c)
        return result

    def difftest(self, left, right, flags=None, flagpart=None):
        L, R = inpath(left), inpath(right)
        if flagpart is None and flags is not None:
            flagpart = '_'.join(f.replace(' ', '_') for f in flags)
        elif flags is not None:
            assert isinstance(flags, list) or isinstance(flags, tuple)
        suffix = f'_{flagpart}' if flagpart else ''
        expected = refpath(f'{left}_{right}{suffix}.txt')
        args = [L, R] + (flags or [])
        actual = self.diff(args)
        self.assertStringCorrect(actual, expected)
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
            'Total number of different values: 2 of 28 (7.14%).',
            actual)

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
            'Total number of different values: 2 of 6 (33.33%).',
            actual)

    # CROSS-TYPE

    def test_a_csv_b_parquet (self):
        """CSV against parquet"""
        actual = self.difftest('a.csv', 'b.parquet')

        # Should also be same result as for csv
        self.assertStringCorrect(actual, refpath('a.csv_b.csv.txt'))

    def test_a_parquet_b_csv (self):
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
        self.assertIn('Total number of different values: 1 of 28 (3.57%).',
                      actual)

    # DIFFERENT NUMBER OF ROWS

    @tag
    def test_a_csv_d_csv(self):
        """One extra row"""
        actual = self.difftest('a.csv', 'f5.tsv')

if __name__ == '__main__':
    TDDA_CONFIG_TESTS = 'TDDA_CONFIG_TESTS' in os.environ
    set_testing(True)

    ReferenceTestCase.main()
