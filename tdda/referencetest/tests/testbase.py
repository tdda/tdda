#
# Unit tests for base ReferenceTest class functionality
#

import os

import pandas as pd
import polars as pl

from tdda.abstractdf import is_pandas_df, is_polars_df
from tdda.referencetest import ReferenceTestCase, ReferenceTest


class TestReferenceTest(ReferenceTestCase):
    def testDefaultLocations(self):
        class ClassA(ReferenceTest):
            pass

        class ClassB(ClassA):
            pass

        class ClassC1(ClassB):
            pass

        class ClassC2(ClassB):
            pass

        class classZ(ReferenceTest):
            pass

        a = ClassA(None)
        b = ClassB(None)
        c1 = ClassC1(None)
        c2 = ClassC2(None)

        self.assertEqual(a._resolve_reference_path('x'), 'x')
        self.assertEqual(b._resolve_reference_path('x'), 'x')
        self.assertEqual(c1._resolve_reference_path('x'), 'x')
        self.assertEqual(c2._resolve_reference_path('x'), 'x')

        ClassA.set_default_data_location('t1')
        ClassB.set_default_data_location('t2')
        ClassC1.set_default_data_location('t3')

        a = ClassA(None)
        b = ClassB(None)
        c1 = ClassC1(None)
        c2 = ClassC2(None)

        self.assertEqual(
            a._resolve_reference_path('x'), os.path.join('t1', 'x')
        )
        self.assertEqual(
            b._resolve_reference_path('x'), os.path.join('t2', 'x')
        )
        self.assertEqual(
            c1._resolve_reference_path('x'), os.path.join('t3', 'x')
        )
        self.assertEqual(
            c2._resolve_reference_path('x'), os.path.join('t2', 'x')
        )

    def test_choose_common_df_lib(self):
        c = ReferenceTest(None)  # None for assertTrue method; not used here
        pddf = pd.DataFrame()
        pldf = pl.DataFrame()

        d, r, L = c.choose_common_df_lib(pddf, pddf)  # both pandas
        self.assertIs(L, c.pandas)

        d, r, L = c.choose_common_df_lib(pldf, pldf)  # both pandas
        self.assertIs(L, c.polars)

        d, r, L = c.choose_common_df_lib(pddf, pldf, 'pandas')
        self.assertIs(L, c.pandas)
        self.assertTrue(is_pandas_df(d))
        self.assertTrue(is_pandas_df(r))

        d, r, L = c.choose_common_df_lib(pddf, pldf, 'polars')
        self.assertIs(L, c.polars)
        self.assertTrue(is_polars_df(d))
        self.assertTrue(is_polars_df(r))

        # config default is polars
        d, r, L = c.choose_common_df_lib(pddf, pldf)
        self.assertIs(L, c.polars)
        self.assertTrue(is_polars_df(d))
        self.assertTrue(is_polars_df(r))


if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
