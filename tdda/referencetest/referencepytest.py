# -*- coding: utf-8 -*-

"""
This provides all of the methods in the
:py:class:`~tdda.referencetest.referencetest.ReferenceTest` class,
but as module functions rather than class methods, using Python's native
:py:func:`assert` mechanism as its means of making assertions.

This allows these functions to be called from tests running from the
``pytest`` framework.

For example::

    from tdda.referencetest import referencepytest
    import my_module

    def test_my_csv_function(ref):
        resultfile = my_module.my_csv_function(ref.tmp_dir)
        ref.assertCSVFileCorrect(resultfile, 'result.csv')

    def test_my_pandas_dataframe_function(ref):
        resultframe = my_modile.my_dataframe_function()
        ref.assertDataFrameCorrect(resultframe, 'result.csv')

    def test_my_table_function(ref):
        result = my_module.my_table_function()
        ref.assertStringCorrect(result, 'table.txt', kind='table')

    def test_my_graph_function(ref):
        result = my_module.my_graph_function()
        ref.assertStringCorrect(result, 'graph.txt', kind='graph')

with a ``conftest.py`` containing::

    import pytest
    from tdda.referencetest import referencepytest

    def pytest_addoption(parser):
        referencepytest.addoption(parser)

    @pytest.fixture(scope='module')
    def ref(request):
        r = referencepytest.ref(request)
        r.set_data_location('testdata')
        return r

To regenerate all reference results (or generate them for the first time)::

    pytest -s --write-all

To regenerate just a particular kind of reference (e.g. table results)::

    pytest -s --write table

To regenerate a number of different kinds of reference (e.g. both table
and graph results)::

    pytest -s --write table graph


If the **-s** option is also provided (to disable ``pytest``
output capturing), it will report the names of all the files it has
regenerated.

``pytest`` Integration Details
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In addition to all of the methods from
:py:class:`~tdda.referencetest.referencetest.ReferenceTest`,
the following functions are provided, to allow easier integration
with the ``pytest`` framework.
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import sys

import pytest

from tdda.referencetest.referencetest import ReferenceTest


def pytest_assert(x, msg):
    # assertion using standard python assert statement, as expected by pytest.
    assert x, msg


def ref(request):
    """
    Support for dependency injection via a ``pytest`` fixture.

    A test's conftest.py should define a fixture function for injecting
    a :py:class:`~tdda.referencetest.referencetest.ReferenceTest` instance,
    which should just call this function.

    This allows tests to get access to a private instance of that class.
    """
    if request.config.getoption('--wquiet'):
        ReferenceTest.set_default(verbose=False)
    if request.config.getoption('--write-all'):
        ReferenceTest.set_regeneration()
    else:
        regen = request.config.getoption('--write')
        if regen:
            for r in regen:
                for kind in r.split(','):
                    ReferenceTest.set_regeneration(kind)
    return ReferenceTest(pytest_assert)


def set_defaults(**kwargs):
    """
    This provides a mechanism for setting default attributes in
    the :py:class:`~tdda.referencetest.referencetest.ReferenceTest` class.

    It takes the same parameters as
    :py:meth:`tdda.referencetest.referencetest.ReferenceTest.set_defaults`,
    and can be used for setting parameters such as the *tmp_dir* property.

    If you want the same defaults for all your tests, it can be easier to
    set them with a call to this function, rather than having to set them
    explicitly in each test (or in your ``@pytest.fixture`` *ref* definition
    in your ``conftest.py`` file).
    """
    ReferenceTest.set_defaults(**kwargs)


def set_default_data_location(location, kind=None):
    """
    This provides a mechanism for setting the default reference data
    location in the :py:class:`~tdda.referencetest.referencetest.ReferenceTest`
    class.

    It takes the same parameters as
    :py:meth:`tdda.referencetest.referencetest.ReferenceTest.set_default_data_location`.

    If you want the same data locations for all your tests, it can be easier
    to set them with calls to this function, rather than having to set them
    explicitly in each test (or using
    :py:meth:`~tdda.referencetest.referencetest.ReferenceTest.set_data_location`
    in your ``@pytest.fixture`` *ref* definition in your ``conftest.py`` file).
    """
    ReferenceTest.set_default_data_location(location, kind=kind)


def addoption(parser):
    """
    Support for the --write and --write-all command-line options.

    A test's ``conftest.py`` file should declare extra options by
    defining a ``pytest_addoption`` function which should just call this.

    It extends pytest to include **--write** and **--write-all** option
    flags which can be used to control regeneration of reference results.

    """
    try:
        parser.addoption('--write', action='store', nargs='+', default=None,
                         help='--write: rewrite named reference results kinds')
        parser.addoption('--write-all', action='store_true',
                         help='--write-all: rewrite all reference results')
        parser.addoption('--wquiet', action='store_true',
                         help='--wquiet: when rewriting results, do so quietly')
    except ValueError:
        # ignore attempts to add parser options multiple times
        pass

