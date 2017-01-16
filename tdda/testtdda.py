"""
Run all TDDA tests
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import


import unittest

try:
    import pandas
except ImportError:
    pandas = None

if pandas:
    from tdda.constraints.testpdconstraints import *
from tdda.rexpy.testrexpy import *
from tdda.referencetest.tests.alltests import *


if __name__ == '__main__':
     unittest.main()
