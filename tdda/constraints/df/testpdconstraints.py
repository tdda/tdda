# -*- coding: utf-8 -*-

"""
Concrete pandas test classes for DataFrame constraint tests.
"""

import datetime
import os
import unittest

from collections import OrderedDict
from shutil import which

import numpy as np
import pandas as pd

from tdda.constraints import base
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
    unicode_definite,
)
from tdda.constraints.console import main_with_argv
from tdda.constraints import discover, verify, detect

from tdda.constraints.df import constraints as dfc
from tdda.constraints.df.constraints import load_df
from tdda.utils import (
    CONSTRAINTSTESTDATADIR as TESTDATADIR,
    TESTREPORTSDIR,
    swap_ext,
)
from tdda.examples import copy_accounts_data_unzipped

from tdda.referencetest import ReferenceTestCase, tag
from tdda.referencetest.pddates import infer_date_format
from tdda.serial import csv_to_pandas

from tdda.constraints.df.dftestbase import (
    TDDA_MD_IGNORES,
    E118_SUMMARY,
    ParquetFileChecker,
    CommandLineHelper,
    DFVerifyBase,
    DFDiscoverBase,
    DFDetectBase,
    DFCommandBase,
    DFCommandAPIBase,
    DFCommandLineBase,
    check_shell_output,
    rmdirs,
)


# ---------------------------------------------------------------------------
# Concrete pandas verify class
# ---------------------------------------------------------------------------

class TestPandasVerify(ReferenceTestCase, DFVerifyBase):
    engine = 'pandas'
    backend = 'original'

    def testVerify1kMultiBackend(self):
        """Multi-backend pandas-specific variant of testVerify1k."""
        csv_path = os.path.join(TESTDATADIR, 'accounts1k.csv:')
        reftddafile1k = os.path.join(TESTDATADIR, 'ref-accounts1k.tdda')
        for backend in ('numpy_nullable', 'pyarrow'):
            v = verify(
                csv_path,
                constraints_path=reftddafile1k,
                backend=backend,
                verbose=False,
            )
            self.assertEqual(v.passes, 75)
            self.assertEqual(v.failures, 0)

    def testVerify25kMultiBackend(self):
        """Multi-backend pandas-specific variant of testVerify25kAgainst1k."""
        csv_path = os.path.join(TESTDATADIR, 'accounts25k.csv:')
        reftddafile1k = os.path.join(TESTDATADIR, 'ref-accounts1k.tdda')
        for backend in ('numpy_nullable', 'pyarrow'):
            v = verify(
                csv_path,
                constraints_path=reftddafile1k,
                backend=backend,
                verbose=False,
            )
            self.assertEqual(v.passes, 55)
            self.assertEqual(v.failures, 20)


TestPandasVerify.set_default_data_location(TESTDATADIR)


# ---------------------------------------------------------------------------
# Concrete pandas discover class
# ---------------------------------------------------------------------------

class TestPandasDiscover(ReferenceTestCase, DFDiscoverBase):
    engine = 'pandas'
    backend = 'original'


# ---------------------------------------------------------------------------
# Concrete pandas detect class
# ---------------------------------------------------------------------------

class TestPandasDetect(ReferenceTestCase, DFDetectBase):
    engine = 'pandas'
    backend = 'original'

    def testDetect25kAgainst1k_parquet(self):
        pq_path = os.path.join(TESTDATADIR, 'accounts25k.parquet')
        reftddafile1k = os.path.join(TESTDATADIR, 'ref-accounts1k.tdda')
        refpath = os.path.join(
            TESTDATADIR, 'ref-detect25k-failures.parquet'
        )
        outfile = os.path.join(self.tmp_dir, 'accounts25kfailures.parquet')
        v = detect(
            pq_path,
            constraints_path=reftddafile1k,
            outpath=outfile,
            verbose=False,
        )
        self.assertEqual(v.passes, 54)
        self.assertEqual(v.failures, 21)
        self.assertEqual(v.detection.n_passing_records, 23373)
        self.assertEqual(v.detection.n_failing_records, 1627)
        actual_df = pd.read_parquet(outfile)
        expected_df = pd.read_parquet(refpath)
        self.assertDataFramesEqual(actual_df, expected_df, outfile, refpath)

    def testDetectDuplicates(self):
        iconstraints = FieldConstraints('i', [NoDuplicatesConstraint()])
        sconstraints = FieldConstraints('s', [NoDuplicatesConstraint()])
        constraints = DatasetConstraints(
            [iconstraints, sconstraints],
            allowed_fields=False,
            required_fields=False,
        )

        df1 = pd.DataFrame(
            {
                'i': pd.array([1, 2, 3, 4, None], dtype='int64[pyarrow]'),
                's': pd.array(
                    ['one', 'two', 'three', 'four', None],
                    dtype='string[pyarrow]'
                ),
            }
        )
        n1 = len(df1)
        verifier1 = dfc.DFConstraintVerifier(df1)
        v1 = verifier1.detect(
            constraints,
            VerificationClass=dfc.DFDetection,
            n_source_records=n1,
        )
        self.assertEqual(v1.passes, 2)
        self.assertEqual(v1.failures, 0)
        ddf1 = v1.detected()
        self.assertIsNone(ddf1)

        df2 = pd.DataFrame(
            {
                'i': pd.array([1, 2, 3, 2, None], dtype='int64[pyarrow]'),
                's': pd.array(
                    ['one', 'two', 'three', 'two', None],
                    dtype='string[pyarrow]'
                ),
            }
        )
        n2 = len(df2)
        verifier2 = dfc.DFConstraintVerifier(df2)
        v2 = verifier2.detect(
            constraints,
            VerificationClass=dfc.DFDetection,
            per_constraint=True,
            output_fields=['i', 's'],
            n_source_records=n2,
        )
        self.assertEqual(v2.passes, 0)
        self.assertEqual(v2.failures, 2)
        ddf2 = v2.detected()
        self.assertDataFrameCorrect(
            ddf2, 'detect_dups.parquet', kind='parquet',
            type_matching='medium',
            check_data=self.all_fields_except(['Index']),
            check_types=self.all_fields_except(['Index']),
        )


TestPandasDetect.set_default_data_location(TESTDATADIR)


# ---------------------------------------------------------------------------
# Pandas-only: field verification (complex inline DataFrame assertions)
# ---------------------------------------------------------------------------

class TestPandasFieldVerification(ReferenceTestCase):
    def testFieldVerification(self):
        df1 = pd.DataFrame(
            {
                'b': [True, False] * 2,
                'i': range(1, 5),
                'r': [float(x) for x in range(1, 5)],
                's': ['S%s' % x for x in range(1, 5)],
                'd': [datetime.datetime(2016, 1, x) for x in range(1, 5)],
            }
        )
        ic1 = FieldConstraints(
            'i',
            [
                TypeConstraint('int'),
                MinConstraint(0),
                MaxConstraint(10),
                SignConstraint('positive'),
                MaxNullsConstraint(0),
                NoDuplicatesConstraint(),
            ],
        )

        ic2 = FieldConstraints(
            'i',
            [
                TypeConstraint('bool'),
                MinConstraint(2),
                MaxConstraint(3),
                SignConstraint('negative'),
                MaxNullsConstraint(0),
                NoDuplicatesConstraint(),
            ],
        )

        dfc1 = [ic1]
        dsc1 = DatasetConstraints(
            dfc1, allowed_fields=False, required_fields=False
        )
        pdcv1 = dfc.DFConstraintVerifier(df1)
        results1 = base.verify(
            dsc1, list(df1), pdcv1.verifiers(), n_source_records=10
        )
        expected = (
            'FIELDS:\n\n'
            'i: 0 failures  6 passes  '
            'type ✓  min ✓  max ✓  sign ✓  '
            'max_nulls ✓  no_duplicates ✓\n\n'
            'SUMMARY:\n\n'
            'Constrained Fields: 1\n'
            'Failing Fields: 0 (0.00%)\n\n'
            'Constraints: 6\n'
            'Failing Constraints: 0 (0.00%)'
        )
        self.assertEqual(str(results1), expected)
        expected_df = pd.DataFrame(
            OrderedDict(
                (
                    ('field', ['i']),
                    ('failures', [0]),
                    ('passes', [6]),
                    ('type', [True]),
                    ('min', [True]),
                    ('max', [True]),
                    ('sign', [True]),
                    ('max_nulls', [True]),
                    ('no_duplicates', [True]),
                )
            )
        )
        vdf = dfc.DFVerification.verification_to_dataframe(results1)
        self.assertTrue(vdf.equals(expected_df))

        df2 = pd.DataFrame({'i': [1, 2, 2, 6, np.nan]})
        dfc2 = [ic2]
        dsc2 = DatasetConstraints(
            dfc2, allowed_fields=False, required_fields=False
        )
        pdcv2 = dfc.DFConstraintVerifier(df2)
        results2 = base.verify(
            dsc2, list(df2), pdcv2.verifiers(), n_source_records=10
        )
        expected = (
            'FIELDS:\n\n'
            'i: 5 failures  1 pass  '
            'type ✓  min ✗  max ✗  sign ✗  '
            'max_nulls ✗  no_duplicates ✗\n\n'
            'SUMMARY:\n\n'
            'Constrained Fields: 1\n'
            'Failing Fields: 1 (100.00%)\n\n'
            'Constraints: 6\n'
            'Failing Constraints: 5 (83.33%)'
        )
        self.assertEqual(str(results2), expected)
        expected_df = pd.DataFrame(
            OrderedDict(
                (
                    ('field', ['i']),
                    ('failures', [5]),
                    ('passes', [1]),
                    ('type', [True]),
                    ('min', [False]),
                    ('max', [False]),
                    ('sign', [False]),
                    ('max_nulls', [False]),
                    ('no_duplicates', [False]),
                )
            )
        )
        vdf = dfc.DFVerification.verification_to_dataframe(results2)
        self.assertTrue(vdf.equals(expected_df))

        pdcv2strict = dfc.DFConstraintVerifier(df2, type_checking='strict')
        results2strict = base.verify(
            dsc2, list(df2), pdcv2strict.verifiers(), n_source_records=10
        )
        expected = (
            'FIELDS:\n\n'
            'i: 6 failures  0 passes  '
            'type ✗  min ✗  max ✗  sign ✗  '
            'max_nulls ✗  no_duplicates ✗\n\n'
            'SUMMARY:\n\n'
            'Constrained Fields: 1\n'
            'Failing Fields: 1 (100.00%)\n\n'
            'Constraints: 6\n'
            'Failing Constraints: 6 (100.00%)'
        )
        self.assertEqual(str(results2strict), expected)
        expected_df = pd.DataFrame(
            OrderedDict(
                (
                    ('field', ['i']),
                    ('failures', [6]),
                    ('passes', [0]),
                    ('type', [False]),
                    ('min', [False]),
                    ('max', [False]),
                    ('sign', [False]),
                    ('max_nulls', [False]),
                    ('no_duplicates', [False]),
                )
            )
        )
        vdf = dfc.DFVerification.verification_to_dataframe(results2strict)
        self.assertTrue(vdf.equals(expected_df))

        ic3 = FieldConstraints('i', [TypeConstraint('int')])
        df3 = df1
        dfc3 = [ic3]
        dsc3 = DatasetConstraints(
            dfc3, allowed_fields=False, required_fields=False
        )
        pdcv3 = dfc.DFConstraintVerifier(df3)
        results3 = base.verify(
            dsc3, list(df3), pdcv3.verifiers(), n_source_records=10
        )
        expected = (
            'FIELDS:\n\n'
            'i: 0 failures  1 pass  type ✓\n\n'
            'SUMMARY:\n\n'
            'Constrained Fields: 1\n'
            'Failing Fields: 0 (0.00%)\n\n'
            'Constraints: 1\n'
            'Failing Constraints: 0 (0.00%)'
        )
        self.assertEqual(str(results3), expected)
        expected_df = pd.DataFrame(
            OrderedDict(
                (
                    ('field', ['i']),
                    ('failures', [0]),
                    ('passes', [1]),
                    ('type', [True]),
                )
            )
        )
        vdf = dfc.DFVerification.verification_to_dataframe(results3)
        self.assertTrue(vdf.equals(expected_df))

        pdcv3 = dfc.DFConstraintVerifier(df3)
        results3 = base.verify(
            dsc3, list(df3), pdcv3.verifiers(), ascii=True, n_source_records=10
        )
        expected = (
            'FIELDS:\n\n'
            'i: 0 failures  1 pass  type OK\n\n'
            'SUMMARY:\n\n'
            'Constrained Fields: 1\n'
            'Failing Fields: 0 (0.00%)\n\n'
            'Constraints: 1\n'
            'Failing Constraints: 0 (0.00%)'
        )
        self.assertEqual(str(results3), expected)


TestPandasFieldVerification.set_default_data_location(TESTDATADIR)


# ---------------------------------------------------------------------------
# Pandas-only: DDD and date DataFrame tests
# ---------------------------------------------------------------------------

class TestPandasDataFrameConstraints(ReferenceTestCase):
    norm_paths = True

    def testDDD_df(self):
        csv_path = os.path.join(TESTDATADIR, 'ddd.csv')
        df = pd.read_csv(csv_path)
        constraints_path = os.path.join(TESTDATADIR, 'ddd.tdda')
        v = verify(df, constraints_path, backend='original')
        # CSV reader reads 'elevens' as int and date cols as strings
        self.assertEqual(v.passes, 58)
        self.assertEqual(v.failures, 3)

    def testDDD_csv(self):
        csv_path = os.path.join(TESTDATADIR, 'ddd.csv')
        o_constraints_path = os.path.join(TESTDATADIR, 'dddo.tdda')
        v = verify(
            csv_path, o_constraints_path, backend='original', verbose=False
        )
        self.assertEqual(v.passes, 61)
        self.assertEqual(v.failures, 0)

        n_constraints_path = os.path.join(TESTDATADIR, 'dddn.tdda')
        v = verify(
            csv_path,
            n_constraints_path,
            backend='numpy_nullable',
            verbose=False,
        )
        self.assertEqual(v.passes, 55)
        self.assertEqual(v.failures, 6)

        constraints_path = os.path.join(TESTDATADIR, 'ddd.tdda')
        for backend in ('numpy_nullable', 'pyarrow'):
            v = verify(
                csv_path + ':',
                constraints_path,
                backend=backend,
                verbose=False,
            )
            self.assertEqual(v.passes, 61)
            self.assertEqual(v.failures, 0)

    def testDDD_discover_and_verify1(self):
        import tempfile
        tmpdir = tempfile.gettempdir()
        actual_constraints = os.path.join(tmpdir, 'dddtestconstraints.tdda')
        actual_constraints2 = os.path.join(
            tmpdir, 'dddtestconstraints2.tdda'
        )
        ref_constraints_tdda = os.path.join(TESTDATADIR, 'ddd-dv.tdda')
        report_formats = ['html', 'txt', 'md', 'json', 'yaml', 'toml']
        csv_path = os.path.join(TESTDATADIR, 'ddd.csv')

        c = discover(
            csv_path,
            constraints_path=actual_constraints,
            report_formats=report_formats,
            group_rexes=True,
            backend='original',
            verbose=False,
        )
        with open(actual_constraints2, 'w', encoding='utf-8') as f:
            f.write(c.to_json())
        v = verify(
            csv_path,
            actual_constraints2,
            report='fields',
            backend='original',
            verbose=False,
        )
        self.assertFileCorrect(
            actual_constraints,
            ref_constraints_tdda,
            ignore_patterns=TDDA_MD_IGNORES,
        )
        self.assertEqual(v.passes, 63)
        self.assertEqual(v.failures, 0)
        for fmt in report_formats:
            ref_path = os.path.join(TESTREPORTSDIR, f'ddd-dv.{fmt}')
            actual_path = swap_ext(actual_constraints, fmt)
            self.assertFileCorrect(
                actual_path, ref_path, ignore_patterns=TDDA_MD_IGNORES
            )

    def testDiscoverDataframeDates(self):
        df = pd.DataFrame(
            {'a': [datetime.date(1987, 1, 1), datetime.date(2019, 1, 2)]}
        )
        c = discover(df, verbose=False)
        ac = c.fields['a'].constraints
        self.assertEqual(ac['type'].value, 'date')
        self.assertEqual(ac['min'].value, datetime.date(1987, 1, 1))
        self.assertEqual(ac['max'].value, datetime.date(2019, 1, 2))
        self.assertEqual(ac['max_nulls'].value, 0)

    def testDiscoverDataframeDateTimes(self):
        df = pd.DataFrame(
            {
                'a': [
                    datetime.datetime(1987, 1, 1),
                    datetime.datetime(2019, 1, 2),
                ]
            }
        )
        c = discover(df, verbose=False)
        ac = c.fields['a'].constraints
        self.assertEqual(ac['type'].value, 'date')
        self.assertEqual(ac['min'].value, datetime.datetime(1987, 1, 1))
        self.assertEqual(ac['max'].value, datetime.datetime(2019, 1, 2))
        self.assertEqual(ac['max_nulls'].value, 0)


# ---------------------------------------------------------------------------
# Pandas-only: CLI option flags (backend-specific)
# ---------------------------------------------------------------------------

class TestPandasVerifyOptionFlags(ReferenceTestCase, CommandLineHelper):
    @classmethod
    def setUpClass(cls):
        cls.setUpHelper()

    @classmethod
    def tearDownClass(cls):
        cls.tearDownHelper()

    @classmethod
    def execute_command(cls, argv):
        return str(main_with_argv(argv, verbose=False))

    def testVerifyOptionFlags(self):
        argv = ['tdda', 'verify', self.e92csv, self.e92tdda_correct]
        result = self.execute_command(argv)
        self.assertEqual(len(result.splitlines()), 41)
        self.assertTrue('✓' in result)
        self.assertFalse('OK' in result)

        argv = ['tdda', 'verify', self.e92csv, self.e92tdda_correct, '--ascii']
        result = self.execute_command(argv)
        self.assertEqual(len(result.splitlines()), 41)
        self.assertTrue('OK' in result)

        argv = [
            'tdda', 'verify', self.e92csv, self.e92tdda_correct, '--fields',
        ]
        result = self.execute_command(argv)
        self.assertEqual(len(result.splitlines()), 8)

        argv = [
            'tdda', 'verify', self.e92csv, self.e92tdda_correct, '--all',
        ]
        result = self.execute_command(argv)
        self.assertEqual(len(result.splitlines()), 41)

        argv = [
            'tdda', 'verify', self.dddcsv, self.dddtdda_correct,
            '--fields', '--type_checking', 'strict', '-Bo',
        ]
        result = self.execute_command(argv)
        self.assertTrue(
            result.strip().endswith(
                'Constraints: 61\nFailing Constraints: 6 (9.84%)'
            )
        )
        argv = [
            'tdda', 'verify', self.dddcsv, self.dddtdda_correct,
            '--fields', '--type_checking', 'sloppy', '-B', 'original',
        ]
        result = self.execute_command(argv)
        self.assertTrue(
            result.strip().endswith(
                'Constraints: 61\nFailing Constraints: 1 (1.64%)'
            )
        )


TestPandasVerifyOptionFlags.set_default_data_location(TESTDATADIR)


# ---------------------------------------------------------------------------
# Concrete pandas CLI classes
# ---------------------------------------------------------------------------

class TestPandasCommandAPI(DFCommandAPIBase, ReferenceTestCase):
    engine = 'pandas'


@unittest.skipIf(not which('tdda'), 'tdda not installed')
class TestPandasCommandLine(DFCommandLineBase, ReferenceTestCase):
    engine = 'pandas'


TestPandasCommandAPI.set_default_data_location(TESTDATADIR)
TestPandasCommandLine.set_default_data_location(TESTDATADIR)


if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
