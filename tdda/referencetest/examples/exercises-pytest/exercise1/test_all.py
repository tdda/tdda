# -*- coding: utf-8 -*-
"""
test_using_referencepytest.py: A simple example of how to use
                               tdda.referencetest.referencepytest with pytest

Source repository: http://github.com/tdda/tdda

License: MIT

Copyright (c) Stochastic Solutions Limited 2019
"""

from generators import generate_string


def testExampleStringGeneration():
    actual = generate_string()
    with open('expected.html') as f:
        expected = f.read()
    assert actual == expected



