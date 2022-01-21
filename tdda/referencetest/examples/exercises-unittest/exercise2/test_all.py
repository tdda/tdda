# -*- coding: utf-8 -*-
"""
exercise1/test_all.py: A simple exercise to show tagging tests

Source repository: http://github.com/tdda/tdda

License: MIT

Copyright (c) Stochastic Solutions Limited 2019
"""

import time

from tdda.referencetest import ReferenceTestCase

from generators import generate_string


class TestQuickThings(ReferenceTestCase):

    def testExampleStringGeneration(self):
        actual = generate_string()
        self.assertStringCorrect(actual, 'expected.html')

    def testZero(self):
        self.assertIsNone(None)


class TestSuperSlowThings(ReferenceTestCase):

    def testOne(self):
        time.sleep(1)
        self.assertEqual(1, 1)

    def testTwo(self):
        time.sleep(2)
        self.assertEqual(2, 2)

    def testThree(self):
        time.sleep(3)
        self.assertEqual(3, 3)


if __name__ == '__main__':
    ReferenceTestCase.main()

