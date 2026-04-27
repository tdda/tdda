#
# Unit tests for file functions from tdda.referencetest.checkfiles
#

import json
import os
import yaml

from tdda.referencetest import ReferenceTestCase, tag
from tdda.referencetest.utils import (
    normalize_json,
    normalize_yaml,
    remove_dict_keys,
    remove_dict_keys_and_sort,
)


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


if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
