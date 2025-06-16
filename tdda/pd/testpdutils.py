import datetime
import os
import tempfile
import unicodedata

import numpy as np
import pandas as pd

from tdda.referencetest.referencetestcase import ReferenceTestCase, tag
from tdda.pd.utils import (
    first_non_null,
    object_col_underlying_type
)
from unicodedata import normalize

TMPDIR = tempfile.mkdtemp()
TESTDIR = os.path.join(os.path.dirname(__file__), 'testdata')


class TestPandasUtils(ReferenceTestCase):

    df = pd.DataFrame({
            'i': [0, 1, 2],
            'fi': [None, 1, 2],
            'I': pd.Series([None, 1, 2], dtype='Int64'),
            'f': [None, 1.5, 2.5],
            'b': [None, True, False],
            'B': pd.Series([None, True, False], dtype='boolean'),
            's': [None, 'a', ''],
            'S': pd.Series([None, 'a', ''], dtype='string'),
            'd': [None] + [datetime.date(2020, 1, 2)] * 2,
            't': [None] + [datetime.datetime(2020, 1, 2, 12, 34, 56)] * 2,
            'nil': [None] * 3,
    })

    def test_first_non_null(self):
        firsts = [first_non_null(self.df[c]) for c in self.df]
        self.assertEqual(firsts,
                         [0, 1, 1, 1.5, True, True, 'a', 'a',
                          datetime.date(2020, 1, 2),
                          pd.Timestamp('2020-01-02 12:34:56'),
                          None])

    def test_object_col_underlying_type(self):
        self.assertEqual(
            [object_col_underlying_type(self.df[c]) for c in self.df],
            ['int64', 'float64', 'Int64',
             'float64',
             'bool', 'boolean',
             'str', 'string',
             'date',
             'datetime64[ns]',
             'NoneType']
        )




if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=True)
