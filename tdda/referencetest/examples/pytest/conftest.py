# -*- coding: utf-8 -*-
"""
conftest.py: example pytest configuration for tdda.referencetest

Source repository: http://github.com/tdda/tdda

License: MIT

Copyright (c) Stochastic Solutions Limited 2016-2018
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import pytest

from tdda.referencetest import referencepytest


@pytest.fixture(scope='module')
def ref(request):
    """
    Declare a fixture called 'ref' which will inject a ReferenceTest
    instance into a test. It's automatically configured to regenerate
    results if the ``--write-all`` or ``--write``  options are used on
    the command line, and in this example is automatically configured
    to locate all reference data files in the 'reference' directory above.
    """
    r = referencepytest.ref(request)
    this_dir = os.path.abspath(os.path.dirname(__file__))
    r.set_data_location(os.path.join(this_dir, '..', 'reference'))
    return r


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

