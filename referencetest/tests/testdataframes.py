# -*- coding: utf-8 -*-

"""
Source repository: http://github.com/tdda/tdda

License: MIT

Copyright (c) Stochastic Solutions Limited 2016
"""

from __future__ import print_function
from __future__ import unicode_literals

import pandas as pd

from tdda.referencetest.referencetestcase import ReferenceTestCase


class MyTest(ReferenceTestCase):
    def test_df(self):
        df1 = pd.DataFrame({'a': [1, 2, 3, 4, 5]})
        df2 = pd.DataFrame({'a': [1, 2, 3, 4, 5]})
        self.assertDatasetsEqual(df1, df2)

    def test_bad_df(self):
        df1 = pd.DataFrame({'a': [1, 2, 3, 4, 5]})
        df2 = pd.DataFrame({'a': [1, 2, 3, 4, 6]})
        with self.assertRaises(Exception):
            self.assertDatasetEqual(df1, df2)
        #AssertionError:
        #*** Dataframe contents check failed.
        #*** Column values differ: a


if __name__ == '__main__':
    ReferenceTestCase.main()



