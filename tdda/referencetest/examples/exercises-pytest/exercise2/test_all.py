# -*- coding: utf-8 -*-
"""
test_using_referencepytest.py: A simple example of how to use
                               tdda.referencetest.referencepytest with pytest

Source repository: http://github.com/tdda/tdda

License: MIT

Copyright (c) Stochastic Solutions Limited 2019
"""
import time

from generators import generate_string


def testZero():
    assert True


def testOne():
    time.sleep(1)
    assert 1 == 1


def testExampleStringGeneration(ref):
    actual = generate_string()
    ref.assertStringCorrect(actual, 'expected.html')


def testTwo():
    time.sleep(2)
    assert 2 == 2


def testThree():
    time.sleep(3)
    assert 3 == 3
