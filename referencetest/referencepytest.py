# -*- coding: utf-8 -*-

"""
referencepytest.py: pytest interface to tdda reference testing.

Source repository: http://github.com/tdda/tdda

License: MIT

Copyright (c) Stochastic Solutions Limited 2016


This provides all of the methods in the ReferenceTest class, but as
module functions rather than class methods, using python's native
'assert' mechanism as its means of making assertions.

For example:

    from tdda.referencetest.referencepytest import (set_data_location,
                                                    assertStringCorrect)
    import my_module

    set_data_location(None, '/data')

    def test_my_table_function():
        result = my_module.my_function()
        assertStringCorrect(result, 'result.txt', kind='table')

    def test_my_graph_function():
        result = my_module.my_function()
        assertStringCorrect(result, 'result.txt', kind='graph')

There isn't (currently) any particularly good way to manage regeneration
of reference data using this framework. You have to call set_regeneration()
explicitly in your test code (or in your conftest.py).

"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import sys

from tdda.referencetest.referencetest import ReferenceTest


def pytest_assert(x, msg):
    """
    assertion using standard python assert statement, as expected by pytest.
    """
    assert x, msg


sys.modules[__name__] = ReferenceTest(pytest_assert)

