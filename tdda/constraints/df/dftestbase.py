# -*- coding: utf-8 -*-

"""
Mixin base classes for engine-parameterised DataFrame constraint tests.
None of these classes inherit from ReferenceTestCase — concrete subclasses
in testpdconstraints.py and testplconstraints.py do that.
"""

import datetime
import getpass
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from collections import OrderedDict

from shutil import which

import numpy as np
import pandas as pd

from tdda.constraints.base import (
    NoDuplicatesConstraint,
    DatasetConstraints,
    Fields,
    FieldConstraints,
    unicode_definite,
    NativeDefiniteObject,
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
from tdda.referencetest import tag


TDDA_MD_IGNORES = [
    r"""^\s*"?local_time"?[ =:]+["'].*['"],?$""",
    r"""^\s*"?utc_time"?[:= ]+['"].*['"],?$""",
    r"""^\s*"?creator"?[:= ]+['"]?TDDA .*['"]?,?$""",
    r"""^\s*"?source"?[:= ]+ ['"]?/.*['"]?,?$""",
    r"""^\s*"?host"?[:= ]+ ['"]?.*['"]?,?$""",
    r"""^\s*"?user"?[:= ]+ ['"]?.*['"]?,?$""",
    r"""^\s*"?tddafile"?[:= ]+ ['"]?.*['"]?,?$""",
]

E118_SUMMARY = """
SUMMARY:

Records: 118
Failing Records: 27 (22.88%)

Constrained Fields: 16
Failing Fields: 11 (68.75%)

Constrained Values: 1,888
Failing Values: 176 (9.32%)

Constraints: 72
Failing Constraints: 15 (20.83%)
"""


def rmdirs(parent, dirs):
    for d in dirs:
        shutil.rmtree(os.path.join(parent, d), ignore_errors=True)


def check_shell_output(args):
    result = subprocess.check_output(NativeDefiniteObject(args))
    return unicode_definite(result).replace('\r', '')


class DFTestBase:
    """Base providing engine-aware DataFrame construction."""
    engine = None
    backend = None

    def _make_df(self, data):
        if self.engine == 'polars':
            import polars as pl
            return pl.DataFrame(data)
        return pd.DataFrame(data)


class ParquetFileChecker:
    def check_parquet_file_correct(self, actual_path, expected_path):
        actual_df = load_df(actual_path)
        expected_df = load_df(os.path.join(TESTDATADIR, expected_path))
        self.assertDataFramesEquivalent(
            actual_df, expected_df, actual_path, expected_path
        )


class CommandLineHelper:
    @classmethod
    def setUpHelper(cls):
        cls.test_tmpdir = os.path.join(tempfile.gettempdir(), getpass.getuser())
        os.makedirs(cls.test_tmpdir, exist_ok=True)
        cls.test_dirs = [
            'referencetest_examples',
            'constraints_examples',
            'rexpy_examples',
        ]
        cls.constraintsdir = os.path.abspath(
            os.path.dirname(__file__)
        )
        cls.tddaTopDir = os.path.dirname(
            os.path.dirname(cls.constraintsdir)
        )
        cls.testDataDir = os.path.join(
            cls.test_tmpdir, 'constraints_examples', 'testdata'
        )

        cls.e92csv = os.path.join(cls.testDataDir, 'elements92.csv')
        cls.e118csv = os.path.join(cls.testDataDir, 'elements118.csv')
        cls.e118parquet = os.path.join(cls.testDataDir, 'elements118.parquet')
        cls.e92tdda_correct = os.path.join(
            cls.testDataDir, 'elements92.tdda'
        )
        cls.dddcsv = os.path.join(cls.testDataDir, 'ddd.csv')
        cls.dddtdda_correct = os.path.join(cls.testDataDir, 'ddd.tdda')

        cls.e92tdda = os.path.join(cls.test_tmpdir, 'elements92.tdda')
        cls.e92bads1 = os.path.join(cls.test_tmpdir, 'elements92bads1.csv')
        cls.e92bads2 = os.path.join(cls.test_tmpdir, 'elements92bads2.csv')
        cls.e92bads3 = os.path.join(cls.test_tmpdir, 'elements92bads3.csv')

        cls.E118summary = E118_SUMMARY.strip()
        argv = ['tdda', 'examples', cls.test_tmpdir]
        cls.execute_command(argv)

    @classmethod
    def tearDownHelper(cls):
        rmdirs(cls.test_tmpdir, cls.test_dirs)

    def _engine_flags(self):
        if self.engine == 'polars':
            return ['--polars']
        return []

    def _pandas_backend_flags(self):
        """Backend flags used in tests that explicitly need original pandas."""
        return ['-B', 'o']


# ---------------------------------------------------------------------------
# Verify mixin
# ---------------------------------------------------------------------------

class DFVerifyBase(DFTestBase):
    """Engine-parameterised verify tests.

    Subclass must set:
        engine = 'pandas' | 'polars'
        backend = 'original' | None   (None means use engine default)
    """

    def testElements92(self):
        csv_path = os.path.join(TESTDATADIR, 'elements92.csv')
        df = load_df(csv_path, engine=self.engine)
        constraints_path = os.path.join(TESTDATADIR, 'elements92.tdda')
        v = verify(df, constraints_path)
        self.assertEqual(v.passes, 72)
        self.assertEqual(v.failures, 0)

    def testElements92rex(self):
        csv_path = os.path.join(TESTDATADIR, 'elements92.csv')
        df = load_df(csv_path, engine=self.engine)
        constraints_path = os.path.join(TESTDATADIR, 'elements92rex.tdda')
        v = verify(df, constraints_path)
        self.assertEqual(v.passes, 78)
        self.assertEqual(v.failures, 0)

    def testElements118CSV(self):
        csv_path = os.path.join(TESTDATADIR, 'elements118.csv')
        df = load_df(csv_path, engine=self.engine)
        constraints_path = os.path.join(TESTDATADIR, 'elements92.tdda')
        v = verify(df, constraints_path, report='fields')
        self.assertEqual(v.passes, 57)
        self.assertEqual(v.failures, 15)
        vdf = v.to_dataframe()
        vdf.sort_values('field', inplace=True)
        self.assertStringCorrect(vdf.to_string(), 'elements118.df')

    def testElements118Parquet(self):
        path = os.path.join(TESTDATADIR, 'elements118.parquet')
        df = load_df(path, engine=self.engine)
        constraints_path = os.path.join(TESTDATADIR, 'elements92.tdda')
        v = verify(df, constraints_path, report='fields')
        self.assertEqual(v.passes, 57)
        self.assertEqual(v.failures, 15)
        vdf = v.to_dataframe()
        vdf.sort_values('field', inplace=True)
        self.assertStringCorrect(vdf.to_string(), 'elements118.df')

    def testElements118rexCSV(self):
        csv_path = os.path.join(TESTDATADIR, 'elements118.csv')
        df = load_df(csv_path, engine=self.engine)
        constraints_path = os.path.join(TESTDATADIR, 'elements92rex.tdda')
        v = verify(df, constraints_path, report='fields')
        self.assertEqual(v.passes, 61)
        self.assertEqual(v.failures, 17)
        vdf = v.to_dataframe()
        vdf.sort_values('field', inplace=True)
        self.assertStringCorrect(vdf.to_string(), 'elements118rex.df')

    def testElements118rexParquet(self):
        path = os.path.join(TESTDATADIR, 'elements118.parquet')
        df = load_df(path, engine=self.engine)
        constraints_path = os.path.join(TESTDATADIR, 'elements92rex.tdda')
        v = verify(df, constraints_path, report='fields')
        self.assertEqual(v.passes, 61)
        self.assertEqual(v.failures, 17)
        vdf = v.to_dataframe()
        vdf.sort_values('field', inplace=True)
        self.assertStringCorrect(vdf.to_string(), 'elements118rex.df')

    def testVerifySignWithWrongType(self):
        df = self._make_df(
            {'a': ['one', 'two', 'three']}
        )
        cdict = {'fields': {'a': {'type': 'int', 'sign': 'positive'}}}
        v = verify(df, cdict, repair=False)
        self.assertFalse(v.fields['a']['type'])
        self.assertFalse(v.fields['a']['sign'])

    def testVerifyStringLengthWithWrongType(self):
        df = self._make_df(
            {'a': [1, 2, -1]}
        )
        cdict = {
            'fields': {'a': {'type': 'string', 'min_length': 2, 'max_length': 3}}
        }
        v = verify(df, cdict, repair=False)
        self.assertFalse(v.fields['a']['type'])
        self.assertFalse(v.fields['a']['min_length'])
        self.assertFalse(v.fields['a']['max_length'])

    def testVerify1k(self):
        csv_path = os.path.join(TESTDATADIR, 'accounts1k.csv:')
        reftddafile1k = os.path.join(TESTDATADIR, 'ref-accounts1k.tdda')
        v = verify(
            csv_path,
            constraints_path=reftddafile1k,
            engine=self.engine,
            backend=self.backend,
            verbose=False,
        )
        self.assertEqual(v.passes, 75)
        self.assertEqual(v.failures, 0)

    def testVerify1k_parquet(self):
        pq_path = os.path.join(TESTDATADIR, 'accounts1k.parquet')
        reftddafile1k = os.path.join(TESTDATADIR, 'ref-accounts1k.tdda')
        v = verify(
            pq_path,
            constraints_path=reftddafile1k,
            engine=self.engine,
            verbose=False,
        )
        self.assertEqual(v.passes, 75)
        self.assertEqual(v.failures, 0)

    def testVerify25kAgainst1k(self):
        csv_path = os.path.join(TESTDATADIR, 'accounts25k.csv:')
        reftddafile1k = os.path.join(TESTDATADIR, 'ref-accounts1k.tdda')
        v = verify(
            csv_path,
            constraints_path=reftddafile1k,
            engine=self.engine,
            backend=self.backend,
            verbose=False,
        )
        passingConstraints = 55
        failingConstraints = 20
        expected = (passingConstraints, failingConstraints)
        self.assertEqual(v.passes, passingConstraints)
        self.assertEqual(v.failures, failingConstraints)
        # !!! IF THIS FAILS, THE EXAMPLES README NEEDS TO BE UPDATED
        self.assertEqual(expected, (55, 20), 'NUMBERS DIFFER FROM README!')
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

    def testVerify25kAgainst1k_parquet(self):
        pq_path = os.path.join(TESTDATADIR, 'accounts25k.parquet')
        reftddafile1k = os.path.join(TESTDATADIR, 'ref-accounts1k.tdda')
        v = verify(
            pq_path,
            constraints_path=reftddafile1k,
            engine=self.engine,
            verbose=False,
        )
        # CSV vs parquet difference: empty strings vs None in account_type
        passingConstraints = 54
        failingConstraints = 21
        self.assertEqual(v.passes, passingConstraints)
        self.assertEqual(v.failures, failingConstraints)

    def testVerifyWithMalformedInMemoryConstraintDict(self):
        df = self._make_df(
            {'a': [1, 2, 3], 'b': ['one', 'two', 'three']}
        )
        cdicts = [
            [],
            {},
            {'fields': 'a'},
            {'fields': 22},
            {'fields': {'a': 33, 'b': 'b'}},
        ]
        for cdict in cdicts:
            constraints = DatasetConstraints()
            with self.assertRaises(Exception):
                constraints.initialize_from_dict(unicode_definite(cdict))
                _v = verify(df, cdict, repair=False)


# ---------------------------------------------------------------------------
# Discover mixin
# ---------------------------------------------------------------------------

class DFDiscoverBase(DFTestBase):
    """Engine-parameterised discover tests."""

    @classmethod
    def setUpClass(cls):
        copy_accounts_data_unzipped(TESTDATADIR)

    def testDiscover1k(self):
        csv_path = os.path.join(TESTDATADIR, 'accounts1k.csv:')
        tddafile1k = os.path.join(self.tmp_dir, 'accounts1kgen.tdda')
        reftddafile1k = os.path.join(TESTDATADIR, 'ref-accounts1k.tdda')
        _c = discover(
            csv_path,
            constraints_path=tddafile1k,
            engine=self.engine,
            backend=self.backend,
            verbose=False,
        )
        self.assertTextFileCorrect(
            tddafile1k,
            reftddafile1k,
            rstrip=True,
            ignore_lines=[
                '"local_time":',
                '"utc_time":',
                '"creator":',
                '"source":',
                '"host":',
                '"user":',
                '"dataset":',
                '"tddafile":',
            ],
        )

    def testDiscover1k_parquet(self):
        pq_path = os.path.join(TESTDATADIR, 'accounts1k.parquet')
        tddafile1k = os.path.join(self.tmp_dir, 'accounts1kgen.tdda')
        reftddafile1k = os.path.join(TESTDATADIR, 'ref-accounts1k.tdda')
        _c = discover(
            pq_path,
            constraints_path=tddafile1k,
            engine=self.engine,
            verbose=False,
        )
        self.assertTextFileCorrect(
            tddafile1k,
            reftddafile1k,
            rstrip=True,
            ignore_lines=[
                '"local_time":',
                '"utc_time":',
                '"creator":',
                '"source":',
                '"host":',
                '"user":',
                '"tddafile":',
                '"dataset":',
            ],
        )

    def testDiscover25k(self):
        csv_path = os.path.join(TESTDATADIR, 'accounts25k.csv:')
        tddafile = os.path.join(self.tmp_dir, 'accounts25kgen.tdda')
        reftddafile = os.path.join(TESTDATADIR, 'ref-accounts25k.tdda')
        _c = discover(
            csv_path,
            constraints_path=tddafile,
            engine=self.engine,
            backend=self.backend,
            verbose=False,
        )
        self.assertTextFileCorrect(
            tddafile,
            reftddafile,
            rstrip=True,
            ignore_lines=[
                '"local_time":',
                '"utc_time":',
                '"creator":',
                '"source":',
                '"host":',
                '"user":',
                '"tddafile":',
                '"dataset":',
            ],
        )

    def testConstraintGenerationNoRex(self):
        self._constraintsGenerationTest(inc_rex=False)

    def testConstraintGenerationWithRex(self):
        self._constraintsGenerationTest(inc_rex=True)

    def _constraintsGenerationTest(self, inc_rex=False):
        csv_path = os.path.join(TESTDATADIR, 'elements92.csv')
        df = load_df(csv_path, engine=self.engine)
        if inc_rex:
            old_ref_name = 'elements92oldrex.tdda'
            new_ref_name = 'elements92rex.tdda'
            old_ref_constraints_path = os.path.join(
                TESTDATADIR, old_ref_name
            )
            new_ref_constraints_path = os.path.join(
                TESTDATADIR, new_ref_name
            )
        else:
            ref_name = 'elements92.tdda'
            old_ref_constraints_path = os.path.join(TESTDATADIR, ref_name)
            new_ref_constraints_path = os.path.join(TESTDATADIR, ref_name)
        with open(old_ref_constraints_path, encoding='utf-8') as f:
            old_refjson = f.read()
        with open(new_ref_constraints_path, encoding='utf-8') as f:
            new_refjson = f.read()
        old_ref = unicode_definite(json.loads(old_refjson))
        new_ref = unicode_definite(json.loads(new_refjson))
        constraints = discover(
            df, inc_rex=inc_rex, group_rexes=True, verbose=False
        )
        discovered = unicode_definite(json.loads(constraints.to_json()))
        discovered_fields = discovered['fields']
        old_ref_fields = old_ref['fields']
        new_ref_fields = new_ref['fields']
        self.assertEqual(
            set(discovered_fields.keys()), set(new_ref_fields.keys())
        )
        for field, ref_field in new_ref_fields.items():
            old_ref_field = old_ref_fields[field]
            new_ref_field = new_ref_fields[field]
            discovered_field = discovered_fields[field]
            self.assertEqual(
                (field, set(discovered_field.keys())),
                (field, set(new_ref_field.keys())),
            )
            for c, new_expected in new_ref_field.items():
                actual = discovered_field[c]
                old_expected = old_ref_field[c]
                if type(new_expected) == float:
                    self.assertAlmostEqual(actual, new_expected, 4)
                elif type(new_expected) == list:
                    self.assertIn(
                        set(actual),
                        [set(new_expected), set(old_expected)],
                    )
                elif new_expected in ('int', 'real'):
                    self.assertTrue(actual in ('int', 'real'))
                else:
                    self.assertIn(actual, (old_expected, new_expected))


# ---------------------------------------------------------------------------
# Detect mixin
# ---------------------------------------------------------------------------

class DFDetectBase(DFTestBase, ParquetFileChecker):
    """Engine-parameterised detect tests."""

    @classmethod
    def setUpClass(cls):
        copy_accounts_data_unzipped(TESTDATADIR)

    def testDetectElements118rexToFile(self):
        csv_path = os.path.join(TESTDATADIR, 'elements118.csv')
        df = load_df(csv_path, engine=self.engine)
        constraints_path = os.path.join(TESTDATADIR, 'elements92rex.tdda')
        detectfile = os.path.join(
            self.tmp_dir, 'elements118rex_detect.csv'
        )
        v = detect(
            df,
            constraints_path,
            report='fields',
            outpath=detectfile,
            output_fields=['Z'],
            rowindex_is_index=False,
        )
        self.assertEqual(v.passes, 61)
        self.assertEqual(v.failures, 17)
        self.assertTextFileCorrect(detectfile, 'elements118rex_detect.csv')

    def testDetectElements118rexToFilePerConstraint(self):
        csv_path = os.path.join(TESTDATADIR, 'elements118.csv')
        df = load_df(csv_path, engine=self.engine)
        constraints_path = os.path.join(TESTDATADIR, 'elements92rex.tdda')
        detectfile = os.path.join(
            self.tmp_dir, 'elements118rex_detect_perc.csv'
        )
        v = detect(
            df,
            constraints_path,
            report='fields',
            outpath=detectfile,
            output_fields=['Z'],
            per_constraint=True,
            rowindex_is_index=False,
        )
        self.assertEqual(v.passes, 61)
        self.assertEqual(v.failures, 17)
        self.assertTextFileCorrect(
            detectfile, 'elements118rex_detect_perc.csv'
        )

    def testDetectElements118rexToDataFrame(self):
        csv_path = os.path.join(TESTDATADIR, 'elements118.csv')
        df = load_df(csv_path, engine=self.engine)
        constraints_path = os.path.join(TESTDATADIR, 'elements92rex.tdda')
        v = detect(
            df, constraints_path, output_fields=['Z'], rowindex_is_index=False
        )
        self.assertEqual(v.passes, 61)
        self.assertEqual(v.failures, 17)
        ddf = v.detected()
        self.assertDataFrameCorrect(
            ddf, 'elements118rex_detect.parquet', kind='parquet',
            type_matching='medium',
            check_data=self.all_fields_except(['Index']),
            check_types=self.all_fields_except(['Index']),
        )

    def testDetectElements118_csv_to_csv(self):
        self._detectElements('csv', 'csv')

    def testDetectElements118_csv_to_parquet(self):
        self._detectElements('csv', 'parquet')

    def testDetectElements118_parquet_to_csv(self):
        self._detectElements('parquet', 'csv')

    def testDetectElements118_parquet_to_parquet(self):
        self._detectElements('parquet', 'parquet')

    def _detectElements(self, input, output):
        csv_path = os.path.join(TESTDATADIR, 'elements118.%s' % input)
        df = load_df(csv_path, engine=self.engine)
        constraints_path = os.path.join(TESTDATADIR, 'elements92.tdda')
        detect_name = 'elements118_detect_from_%s.%s' % (input, output)
        detectfile = os.path.join(self.tmp_dir, detect_name)
        v = detect(
            df,
            constraints_path,
            report='fields',
            outpath=detectfile,
            output_fields=['Z'],
            per_constraint=True,
            index=True,
            rownumber_is_index=False,
        )
        self.assertEqual(v.detection.n_passing_records, 91)
        self.assertEqual(v.detection.n_failing_records, 27)
        if output == 'parquet':
            self.check_parquet_file_correct(detectfile, detect_name)
        else:
            self.assertTextFileCorrect(detectfile, detect_name)

    def testDetectWithWrongTypes(self):
        df = self._make_df(
            {'a': [1, 2, 3], 'b': ['one', 'two', 'three']}
        )
        cdict = {
            'fields': {
                'a': {'type': 'string', 'min_length': 2, 'max_length': 3},
                'b': {'type': 'int', 'min': 1, 'max': 3, 'sign': 'positive'},
            }
        }
        v = detect(
            df,
            cdict,
            per_constraint=True,
            output_fields=[],
            interleave=True,
            repair=False,
        )
        d = v.detected()
        self.assertTrue(not d['a_type_ok'].any())
        self.assertTrue(not d['b_type_ok'].any())
        self.assertTrue(not d['b_min_ok'].any())
        self.assertTrue(not d['b_max_ok'].any())

    def testDetect25kAgainst1k(self):
        csv_path = os.path.join(TESTDATADIR, 'accounts25k.csv:')
        reftddafile1k = os.path.join(TESTDATADIR, 'ref-accounts1k.tdda')
        refpath = os.path.join(
            TESTDATADIR, 'ref-detect25k-failures.txt'
        )
        outfile = os.path.join(
            self.tmp_dir, 'accounts25kfailures.txt'
        )
        v = detect(
            csv_path,
            constraints_path=reftddafile1k,
            outpath=outfile,
            engine=self.engine,
            backend=self.backend,
            verbose=False,
        )
        passingConstraints = 55
        failingConstraints = 20
        passingRecords = 23373
        failingRecords = 1627
        expected = (
            passingConstraints,
            failingConstraints,
            passingRecords,
            failingRecords,
        )
        self.assertEqual(v.passes, passingConstraints)
        self.assertEqual(v.failures, failingConstraints)
        self.assertEqual(v.detection.n_passing_records, passingRecords)
        self.assertEqual(v.detection.n_failing_records, failingRecords)
        # !!! IF THIS FAILS, THE EXAMPLES README MAY NEED TO BE UPDATED
        self.assertEqual(
            expected, (55, 20, 23373, 1627), 'NUMBERS DIFFER FROM README!'
        )
        # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        self.assertTextFileCorrect(outfile, refpath)


# ---------------------------------------------------------------------------
# CLI mixin
# ---------------------------------------------------------------------------

class DFCommandBase(DFTestBase, CommandLineHelper):
    """Engine-parameterised CLI tests."""

    def testDiscoverCmd(self):
        try:
            os.remove(self.e92tdda)
        except Exception:
            pass
        argv = (
            ['tdda', 'discover', self.e92csv, self.e92tdda]
            + self._engine_flags()
        )
        self.execute_command(argv)
        self.assertTextFileCorrect(
            self.e92tdda,
            'elements92_pandas.tdda',
            rstrip=True,
            ignore_substrings=[
                '"local_time":',
                '"utc_time":',
                '"source":',
                '"host":',
                '"user":',
                '"tddafile":',
                '"creator":',
            ],
        )
        os.remove(self.e92tdda)

    def testVerifyE92Cmd(self):
        argv = (
            ['tdda', 'verify', self.e92csv, self.e92tdda_correct]
            + self._engine_flags()
        )
        result = self.execute_command(argv)
        self.assertTrue(
            result.strip().endswith(
                'Constraints: 72\nFailing Constraints: 0 (0.00%)'
            )
        )

    def testVerifyE118Cmd(self):
        argv = (
            ['tdda', 'verify', self.e118csv, self.e92tdda_correct]
            + self._engine_flags()
        )
        result = self.execute_command(argv)
        self.assertTrue(
            result.strip().endswith(
                'Constraints: 72\nFailing Constraints: 15 (20.83%)'
            )
        )
        self.assertStringCorrect(
            str(result), 'elements118_verify_92_out.txt'
        )

    def testVerifyEpsilon(self):
        argv = (
            ['tdda', 'verify', self.e118csv, self.e92tdda_correct, '--fields']
            + self._engine_flags()
        )
        result = self.execute_command(argv)
        self.assertTrue(
            result.strip().endswith(
                'Constraints: 72\nFailing Constraints: 15 (20.83%)'
            )
        )

        argv = (
            [
                'tdda', 'verify', self.e118csv, self.e92tdda_correct,
                '--fields', '--epsilon', '0.5',
            ]
            + self._engine_flags()
        )
        result = self.execute_command(argv)
        self.assertTrue(
            result.strip().endswith(
                'Constraints: 72\nFailing Constraints: 12 (16.67%)'
            )
        )

        argv = (
            [
                'tdda', 'verify', self.e118csv, self.e92tdda_correct,
                '--fields', '--epsilon', '10',
            ]
            + self._engine_flags()
        )
        result = self.execute_command(argv)
        self.assertTrue(
            result.strip().endswith(
                'Constraints: 72\nFailing Constraints: 11 (15.28%)'
            )
        )

    def testDetectE118Cmd(self):
        argv = (
            [
                'tdda', 'detect',
                self.e118csv, self.e92tdda_correct, self.e92bads1,
                '--per-constraint', '--output-fields', '--index',
            ]
            + self._pandas_backend_flags()
        )
        result = self.execute_command(argv)
        self.assertTrue(result.strip().endswith(self.E118summary))
        self.assertTrue(os.path.exists(self.e92bads1))
        self.assertTextFileCorrect(self.e92bads1, 'detect-els-cmdline.csv')
        os.remove(self.e92bads1)

    def testDetectE118CmdInterleaved(self):
        argv = (
            [
                'tdda', 'detect',
                self.e118csv, self.e92tdda_correct, self.e92bads3,
                '--per-constraint', '--output-fields', '--interleave',
            ]
            + self._pandas_backend_flags()
        )
        result = self.execute_command(argv)
        self.assertTrue(result.strip().endswith(self.E118summary))
        self.assertTrue(os.path.exists(self.e92bads3))
        self.assertTextFileCorrect(
            self.e92bads3, 'detect-els-cmdline-interleaved.csv'
        )
        os.remove(self.e92bads3)

    def testDetectE118ParquetCmd(self):
        argv = (
            [
                'tdda', 'detect',
                self.e118parquet, self.e92tdda_correct, self.e92bads2,
                '--per-constraint', '--output-fields', '--index',
            ]
            + self._engine_flags()
        )
        result = self.execute_command(argv)
        self.assertTrue(result.strip().endswith(self.E118summary))
        self.assertTrue(os.path.exists(self.e92bads2))
        self.assertTextFileCorrect(self.e92bads2, 'detect-els-cmdline2.csv')
        os.remove(self.e92bads2)


# ---------------------------------------------------------------------------
# Shared base classes for API and command-line test classes
# ---------------------------------------------------------------------------

class DFCommandAPIBase(DFCommandBase, CommandLineHelper):
    """Mixin: runs CLI tests via main_with_argv (in-process)."""

    @classmethod
    def setUpClass(cls):
        cls.setUpHelper()

    @classmethod
    def tearDownClass(cls):
        cls.tearDownHelper()

    @classmethod
    def execute_command(cls, argv):
        return str(main_with_argv(argv, verbose=False))


class DFCommandLineBase(DFCommandBase, CommandLineHelper):
    """Mixin: runs CLI tests via shell subprocess."""

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
    def execute_command(cls, argv):
        try:
            result = check_shell_output(argv)
        except Exception:
            print(
                '\n\nIf this test fails, it often means you do not have a '
                'working command-line\ninstallation of the tdda command.\n\n'
                'To test this, try typing\n\n  tdda version\n\n'
            )
            raise
        return result
