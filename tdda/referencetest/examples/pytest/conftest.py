# -*- coding: utf-8 -*-
"""
conftest.py: example pytest configuration for tdda.referencetest

Source repository: http://github.com/tdda/tdda

License: MIT

Copyright (c) Stochastic Solutions Limited 2016
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
    results if the --W options is used on the command line, and in this
    example is automatically configured to locate all reference data
    files in the 'reference' directory above.
    """
    r = referencepytest.ref(request)
    this_dir = os.path.abspath(os.path.dirname(__file__))
    r.set_data_location(os.path.join(this_dir, '..', 'reference'))
    return r


def pytest_addoption(parser):
    """
    Extend pytest to include the --write and --write-all regeneration
    command-line options.
    """
    referencepytest.addoption(parser)

