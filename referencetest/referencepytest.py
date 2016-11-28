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

    from tdda.referencetest import referencepytest
    import my_module

    @pytest.fixture(scope='module')
    def ref():
        r = referencepytest.ref()
        r.set_data_location(None, '/data')
        return r

    def test_my_table_function(ref):
        result = my_module.my_function()
        ref.assertStringCorrect(result, 'result.txt', kind='table')

    def test_my_graph_function(ref):
        result = my_module.my_function()
        ref.assertStringCorrect(result, 'result.txt', kind='graph')


Put calls to ref().set_regeneration() in the test, or in conftest.py, to
control regeneration of reference data. There is no command-line option
for this, yet.
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import sys

import pytest

from tdda.referencetest.referencetest import ReferenceTest


def pytest_assert(x, msg):
    """
    assertion using standard python assert statement, as expected by pytest.
    """
    assert x, msg


@pytest.fixture(scope='module')
def ref():
    r = ReferenceTest(pytest_assert)
    return r

