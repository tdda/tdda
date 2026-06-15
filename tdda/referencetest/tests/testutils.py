#
# Unit tests for file functions from tdda.referencetest.checkfiles
#

import json
import os
import yaml

import pandas as pd

from tdda.referencetest import ReferenceTestCase, tag
from tdda.referencetest.utils import (
    apply_preprocess,
    norm_paths_in_json,
    normalize_json,
    normalize_yaml,
    remove_dict_keys,
    remove_dict_keys_and_sort,
)


WINDOWS_JSON = r"""
{
  "items": [
    "C:\\a\\b.csv",
    "hello"
  ],
  "name": "unchanged",
  "nested": {
    "count": 42,
    "file_path": "C:\\tmp\\out.csv"
  },
  "source": "C:\\Users\\tdda\\data\\file.csv"
}
""".lstrip()

POSIX_JSON = """
{
  "items": [
    "/a/b.csv",
    "hello"
  ],
  "name": "unchanged",
  "nested": {
    "count": 42,
    "file_path": "/tmp/out.csv"
  },
  "source": "/Users/tdda/data/file.csv"
}
""".lstrip()

FILE_PATH_NORMED_JSON = r"""
{
  "items": [
    "C:\\a\\b.csv",
    "hello"
  ],
  "name": "unchanged",
  "nested": {
    "count": 42,
    "file_path": "/tmp/out.csv"
  },
  "source": "C:\\Users\\tdda\\data\\file.csv"
}
""".lstrip()

SOURCE_AND_FILE_PATH_NORMED_JSON = r"""
{
  "items": [
    "C:\\a\\b.csv",
    "hello"
  ],
  "name": "unchanged",
  "nested": {
    "count": 42,
    "file_path": "/tmp/out.csv"
  },
  "source": "/Users/tdda/data/file.csv"
}
""".lstrip()


class TestUtils(ReferenceTestCase):
    def testRemoveDictKeys(self):
        d = {'one': 1, 'two': {'one': 1}, 'three': [{'one': 1, 'two': 2}, 3]}
        expected = {'two': {}, 'three': [{'two': 2}, 3]}
        self.assertEqual(remove_dict_keys(d, keys=['one']), expected)

    def testRemoveDictKeysAndSort(self):
        d = {'one': 1, 'two': {'one': 1}, 'three': [{'one': 1, 'two': 2}, 3]}
        expected = {'three': [{'two': 2}, 3], 'two': {}}
        self.assertEqual(remove_dict_keys_and_sort(d, keys=['one']), expected)

    def testNormalizeJson(self):
        j = """
{
    "one": 1,
    "two": {"one": 1},
    "three": [
        {"one": 1, "two": 2},
        3
    ]
}
"""

        expected = """{
  "one": 1,
  "three": [
    {
      "one": 1,
      "two": 2
    },
    3
  ],
  "two": {
    "one": 1
  }
}"""
        self.assertEqual(normalize_json(j), expected)

    def testNormalizeYAML(self):
        y = """
one: 1
two:
    one: 1
three:
-   one: 1
    two: 2
- 3
"""
        self.assertEqual(
            normalize_yaml(y),
            """one: 1
three:
- one: 1
  two: 2
- 3
two:
  one: 1
""",
        )


class TestNormPathsInJson(ReferenceTestCase):
    def testNormPathsTrue(self):
        self.assertStringsEquivalent(
            norm_paths_in_json(WINDOWS_JSON, True), POSIX_JSON
        )

    def testNormPathsKeyGlob(self):
        self.assertStringsEquivalent(
            norm_paths_in_json(WINDOWS_JSON, '*_path'),
            FILE_PATH_NORMED_JSON,
        )

    def testNormPathsKeyList(self):
        self.assertStringsEquivalent(
            norm_paths_in_json(WINDOWS_JSON, ['source', '*_path']),
            SOURCE_AND_FILE_PATH_NORMED_JSON,
        )

    def testNormPathsNoOp(self):
        self.assertStringsEquivalent(
            norm_paths_in_json(WINDOWS_JSON, 'no_such_key'),
            WINDOWS_JSON,
        )


class TestApplyPreprocess(ReferenceTestCase):
    def testSingleFunction(self):
        self.assertEqual(apply_preprocess('a', lambda x: x + 'b'), 'ab')

    def testNone(self):
        self.assertEqual(apply_preprocess('a', None), 'a')

    def testListOrder(self):
        # Non-commutative: f appends 'b', g appends 'c'
        # [f, g] should give 'abc', not 'acb'
        f = lambda x: x + 'b'
        g = lambda x: x + 'c'
        self.assertEqual(apply_preprocess('a', [f, g]), 'abc')
        self.assertEqual(apply_preprocess('a', [g, f]), 'acb')

    def testListOrderDataFrame(self):
        # Non-commutative on DataFrames: f appends '_x', g uppercases
        # [f, g] gives 'VALUE_X', [g, f] gives 'VALUE_x'
        df = pd.DataFrame({'name': ['value']})
        f = lambda d: d.assign(name=d['name'] + '_x')
        g = lambda d: d.assign(name=d['name'].str.upper())
        self.assertEqual(
            apply_preprocess(df, [f, g])['name'][0], 'VALUE_X'
        )
        self.assertEqual(
            apply_preprocess(df, [g, f])['name'][0], 'VALUE_x'
        )


if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
