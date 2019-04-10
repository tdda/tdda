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

from tdda.referencetest.pytestconfig import (pytest_addoption,
                                             pytest_collection_modifyitems,
                                             set_default_data_location,
                                             ref)


set_default_data_location('../reference')

