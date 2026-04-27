import datetime
import os
import tempfile
import unicodedata

import numpy as np
import pandas as pd

from tdda.referencetest.referencetestcase import ReferenceTestCase, tag
from tdda.pd.utils import (
    first_non_null,
    object_col_underlying_type,
    find_safe_null_rep,
    NULL_REPS,
    FIRST_BRAILLE,
)
from unicodedata import normalize

TMPDIR = tempfile.mkdtemp()
TESTDIR = os.path.join(os.path.dirname(__file__), 'testdata')


class TestPandasUtils(ReferenceTestCase):
    df = pd.DataFrame(
        {
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
        }
    )

    def test_first_non_null(self):
        firsts = [first_non_null(self.df[c]) for c in self.df]
        self.assertEqual(
            firsts,
            [
                0,
                1,
                1,
                1.5,
                True,
                True,
                'a',
                'a',
                datetime.date(2020, 1, 2),
                pd.Timestamp('2020-01-02 12:34:56'),
                None,
            ],
        )

    def test_object_col_underlying_type(self):
        types = [object_col_underlying_type(self.df[c]) for c in self.df]
        self.assertEqual(
            types[:-2],
            [
                'int64',
                'float64',
                'Int64',
                'float64',
                'bool',
                'boolean',
                'str',
                'string',
                'date',
            ],
        )
        self.assertTrue(types[-2].startswith('datetime64'))
        self.assertEqual(types[-1], 'NoneType')

    def test_find_safe_null_rep(self):
        df = pd.DataFrame(
            {
                'a': ['a', 'b', None],
                'n': [1, 2, 3],
                'b': [True, False, True],
            }
        )
        self.assertEqual(find_safe_null_rep(df), '')  # '' OK
        self.assertEqual(find_safe_null_rep(df, non_ascii=True), '∙')  # '' OK

        df['c'] = ['', '', '∙']
        self.assertEqual(find_safe_null_rep(df), 'NULL')
        self.assertEqual(find_safe_null_rep(df, non_ascii=True), '∅')

        df['d'] = ['NULL', '∙', '']
        self.assertEqual(find_safe_null_rep(df), '∅')

        df['e'] = ['∅', '∅', '∅']

        df['f'] = [chr(x) for x in range(0xA1, 0xA4)]
        self.assertEqual(find_safe_null_rep(df), '¤')

        # a and b no use: used
        self.assertEqual(find_safe_null_rep(df, ['a', 'b']), '¤')

        # c can be used
        self.assertEqual(find_safe_null_rep(df, ['a', 'b', 'c']), 'c')

        # Just to be awkward: Use all the defaults

        df = pd.DataFrame({'a': NULL_REPS})
        self.assertEqual(find_safe_null_rep(df), '⠁')  # first braille

        # All the defaults, and the same number of Brailles:

        N = len(df)
        df['b'] = [chr(n) for n in range(FIRST_BRAILLE, FIRST_BRAILLE + N)]
        expected = chr(FIRST_BRAILLE + N)
        self.assertEqual(find_safe_null_rep(df), expected)  # first braille


if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=True)
