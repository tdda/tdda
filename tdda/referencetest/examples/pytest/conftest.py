# -*- coding: utf-8 -*-
"""
conftest.py: example pytest configuration for tdda.referencetest

Source repository: http://github.com/tdda/tdda

License: MIT

Copyright (c) Stochastic Solutions Limited 2016-2018
"""


from tdda.referencetest.pytestconfig import (pytest_addoption,
                                             pytest_collection_modifyitems,
                                             pytest_runtest_logreport,
                                             pytest_sessionfinish,
                                             set_default_data_location,
                                             ref)


set_default_data_location('../reference')

