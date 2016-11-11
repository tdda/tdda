"""
Run all TDDA tests
"""

from __future__ import division

import unittest

try:
    import pandas
except ImportError:
    pandas = None

from tdda.constraints.testconstraints import *
if pandas:
    from tdda.constraints.testpdconstraints import *
from tdda.rexpy.testrexpy import *


if __name__ == '__main__':
     unittest.main()
