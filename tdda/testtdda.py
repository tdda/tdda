"""
Run all TDDA tests
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

from tdda.referencetest import ReferenceTestCase

from tdda.constraints.testconstraints import *
from tdda.rexpy.testrexpy import *
from tdda.referencetest.tests.alltests import *


if __name__ == '__main__':
    ReferenceTestCase.main()

