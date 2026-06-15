# -*- coding: utf-8 -*-

"""
Concrete polars test classes for DataFrame constraint tests.
Populated incrementally as each operation is implemented.
"""

import datetime
import os
import unittest

import polars as pl

from shutil import which

from tdda.constraints import detect, discover
from tdda.constraints.base import (
    DatasetConstraints,
    FieldConstraints,
    NoDuplicatesConstraint,
)
from tdda.constraints.df import constraints as dfc
from tdda.referencetest import ReferenceTestCase, tag

from tdda.constraints.df.dftestbase import (
    DFVerifyBase,
    DFDiscoverBase,
    DFDetectBase,
    DFCommandBase,
    DFCommandAPIBase,
    DFCommandLineBase,
)
from tdda.utils import CONSTRAINTSTESTDATADIR as TESTDATADIR


class TestPolarsVerify(ReferenceTestCase, DFVerifyBase):
    engine = 'polars'

TestPolarsVerify.set_default_data_location(TESTDATADIR)


class TestPolarsDiscover(ReferenceTestCase, DFDiscoverBase):
    engine = 'polars'

TestPolarsDiscover.set_default_data_location(TESTDATADIR)


class TestPolarsDetect(ReferenceTestCase, DFDetectBase):
    engine = 'polars'

    def testDetect25kAgainst1k_parquet(self):
        pq_path = os.path.join(TESTDATADIR, 'accounts25k.parquet')
        reftddafile1k = os.path.join(TESTDATADIR, 'ref-accounts1k.tdda')
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
        self.assertDataFrameCorrect(
            pl.read_parquet(outfile),
            'ref-detect25k-failures.parquet',
            kind='parquet',
        )

TestPolarsDetect.set_default_data_location(TESTDATADIR)


class TestPolarsDetectDuplicates(ReferenceTestCase):
    def testDetectDuplicates(self):
        iconstraints = FieldConstraints('i', [NoDuplicatesConstraint()])
        sconstraints = FieldConstraints('s', [NoDuplicatesConstraint()])
        constraints = DatasetConstraints(
            [iconstraints, sconstraints],
            allowed_fields=False,
            required_fields=False,
        )

        df1 = pl.DataFrame(
            {
                'i': [1, 2, 3, 4, None],
                's': ['one', 'two', 'three', 'four', None],
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

        df2 = pl.DataFrame(
            {
                'i': [1, 2, 3, 2, None],
                's': ['one', 'two', 'three', 'two', None],
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
            ddf2, 'detect_dups.parquet', kind='parquet'
        )


TestPolarsDetectDuplicates.set_default_data_location(TESTDATADIR)


class TestPolarsDataFrameConstraints(ReferenceTestCase):
    def testDiscoverDataframeDates(self):
        df = pl.DataFrame(
            {'a': [datetime.date(1987, 1, 1), datetime.date(2019, 1, 2)]}
        )
        c = discover(df, verbose=False)
        ac = c.fields['a'].constraints
        self.assertEqual(ac['type'].value, 'date')
        self.assertEqual(ac['min'].value, datetime.date(1987, 1, 1))
        self.assertEqual(ac['max'].value, datetime.date(2019, 1, 2))
        self.assertEqual(ac['max_nulls'].value, 0)

    def testDiscoverDataframeDateTimes(self):
        df = pl.DataFrame(
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


class TestPolarsCommandAPI(DFCommandAPIBase, ReferenceTestCase):
    engine = 'polars'


@unittest.skipIf(not which('tdda'), 'tdda not installed')
class TestPolarsCommandLine(DFCommandLineBase, ReferenceTestCase):
    engine = 'polars'


TestPolarsCommandAPI.set_default_data_location(TESTDATADIR)
TestPolarsCommandLine.set_default_data_location(TESTDATADIR)


if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
