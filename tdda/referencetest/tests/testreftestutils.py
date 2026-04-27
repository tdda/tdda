#
# Unit tests for base ReferenceTest class functionality
#

import pandas as pd
import polars as pl

from tdda.abstractdf import *
from tdda.referencetest import ReferenceTestCase, tag
from tdda.referencetest.utils import *
from tdda.utils import TDDAError


class TestReferenceTest(ReferenceTestCase):
    pldf = pl.DataFrame({'a': [0]})
    pddf = pd.DataFrame({'a': [0]})
    pldf3 = pl.DataFrame(
        {
            'a': [0],
            'c': ['a'],
            'b': [True],
        }
    )
    pddf3 = pldf3.to_pandas()

    def testIsPolars(self):
        self.assertTrue(is_polars_df(self.pldf))
        self.assertFalse(is_polars_df(self.pddf))

    def testIsPandas(self):
        self.assertTrue(is_pandas_df(self.pddf))
        self.assertFalse(is_pandas_df(self.pldf))

    def test_df_type(self):
        self.assertEqual(df_type(self.pddf), 'pandas')
        self.assertEqual(df_type(self.pldf), 'polars')
        self.assertRaises(TDDAError, df_type, None)

    def test_df_definite(self):
        self.assertIs(df_definite(self.pldf, 'polars'), self.pldf)
        self.assertIs(df_definite(self.pddf, 'pandas'), self.pddf)

        pldf2 = df_definite(self.pddf, 'polars')
        self.assertIsNot(pldf2, self.pddf)
        self.assertTrue(is_polars_df, pldf2)
        self.assertTrue(pldf2.equals(self.pldf))

        pddf2 = df_definite(self.pldf, 'pandas')
        self.assertIsNot(pddf2, self.pldf)
        self.assertTrue(is_pandas_df, pddf2)
        self.assertTrue(pddf2.equals(self.pddf))

    def test_all_fields_except(self):
        f = all_fields_except(['a'])
        self.assertEqual(f(self.pldf3), ['b', 'c'])
        self.assertEqual(f(self.pddf3), ['b', 'c'])

        f = all_fields_except(['a', 'b', 'c'])
        self.assertEqual(f(self.pldf3), [])
        self.assertEqual(f(self.pddf3), [])

        f = all_fields_except([])
        self.assertEqual(f(self.pldf3), ['a', 'b', 'c'])
        self.assertEqual(f(self.pddf3), ['a', 'b', 'c'])

    def test_col_names(self):
        self.assertEqual(col_names(self.pldf3), ['a', 'c', 'b'])
        self.assertEqual(col_names(self.pddf3), ['a', 'c', 'b'])


if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
