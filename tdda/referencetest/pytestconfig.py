# -*- coding: utf-8 -*-

"""
Standard configuration boilerplate for use with pytest.

The conftest.py configuration file in a test suite should enable reference
tests by including the following two lines:

    from tdda.referencetest.pytestconfig import *

    set_default_data_location('/directory/where/my/reference/test/data/lives')
"""

import pytest

from tdda.referencetest import referencepytest

def pytest_addoption(parser):
    """
    Extend pytest to include the --write, --write-all regeneration
    command-line options, and the --tagged and --istagged tagging options.
    """
    referencepytest.addoption(parser)


def pytest_collection_modifyitems(session, config, items):
    """
    Extend pytest to only run tagged tests if run with --tagged,
    and to report tagged tests if run with --istagged (and -s).
    """
    referencepytest.tagged(config, items)


@pytest.fixture(scope='module')
def ref(request):
    """
    Declare a fixture called 'ref' which will inject a ReferenceTest
    instance into a test. It's automatically configured to regenerate
    results if the ``--write-all`` or ``--write``  options are used on
    the command line.
    """
    return referencepytest.ref(request)


def set_default_data_location(location, kind=None):
    """
    Expose the referencepytest.set_default_data_location function here,
    so that it's easy to use from a conftest.py thst imports this file.
    """
    referencepytest.set_default_data_location(location, kind=kind)

