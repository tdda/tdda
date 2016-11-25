# -*- coding: utf-8 -*-

#
# Unit tests for functions from tdda.referencetest.checkpandas
#

from __future__ import absolute_import
from __future__ import unicode_literals
from __future__ import division

import unittest

try:
    import pandas as pd
except ImportError:
    pd = None

from tdda.referencetest.checkpandas import PandasComparison


@unittest.skipIf(pd is None, 'no pandas')
class TestStrings(unittest.TestCase):

    def test_datasets_ok(self):
        compare = PandasComparison()
        df1 = pd.DataFrame({'a': [1, 2, 3, 4, 5],
                            'b': [1.0001, 2.0001, 3.0001, 4.0001, 5.0001]})
        df2 = pd.DataFrame({'a': [1, 2, 3, 4, 5],
                            'b': [1.0002, 2.0002, 3.0002, 4.0002, 5.0002]})
        df3 = pd.DataFrame({'a': [1, 2, 3, 4, 5],
                            'b': [1, 2, 3, 4, 5]})
        self.assertEqual(compare.check_dataframe(df1, df1), (0, []))
        self.assertEqual(compare.check_dataframe(df1, df2, precision=3),
                         (0, []))
        self.assertEqual(compare.check_dataframe(df1, df3,
                                                 check_types=['a'],
                                                 check_data=['a']),
                         (0, []))

    def test_datasets_fail(self):
        compare = PandasComparison()
        df1 = pd.DataFrame({'a': [1, 2, 3, 4, 5],
                            'b': [1.0001, 2.0001, 3.0001, 4.0001, 5.0001]})
        df2 = pd.DataFrame({'a': [1, 2, 3, 4, 5],
                            'b': [1.0002, 2.0002, 3.0002, 4.0002, 5.0002]})
        df3 = pd.DataFrame({'a': [1, 2, 3, 4, 5],
                            'b': [1, 2, 3, 4, 5]})
        self.assertEqual(compare.check_dataframe(df1, df2),
                         (1, ['Dataframe contents check failed.',
                              'Column values differ: b']))
        self.assertEqual(compare.check_dataframe(df1, df3, check_types=['a']),
                         (1, ['Dataframe contents check failed.',
                              'Column values differ: b']))
        self.assertEqual(compare.check_dataframe(df1, df3, check_data=['a']),
                         (1,
                          ['Column check failed',
                           'Wrong column type b (float64, expected int64)']))


if __name__ == '__main__':
    unittest.main()
