# -*- coding: utf-8 -*-
"""
exercise1/test_all.py: A simple example of how to use
                       tdda.referencetest.ReferenceTestCase.

Source repository: http://github.com/tdda/tdda

License: MIT

Copyright (c) Stochastic Solutions Limited 2019
"""

import unittest

from generators import generate_string


class TestFileGeneration(unittest.TestCase):
    def testExampleStringGeneration(self):
        actual = generate_string()
        with open('expected.html') as f:
            expected = f.read()
        self.assertEqual(actual, expected)


if __name__ == '__main__':
    unittest.main()

