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
def ref():
    r = referencepytest.ref()
    this_dir = os.path.abspath(os.path.dirname(__file__))
    r.set_data_location(os.path.join(this_dir, '..', 'reference'))
    return r


#pytest_plugins = 'tdda.referencetest'

def pytest_addoption(parser):
    pass
    
