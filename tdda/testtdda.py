"""
Run all TDDA tests
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import sys

from tdda.referencetest import ReferenceTestCase

from tdda.constraints.testconstraints import *
from tdda.rexpy.testrexpy import *
from tdda.referencetest.tests.alltests import *


def testall(module=None, argv=None):
    ReferenceTestCase.main(module=module, argv=argv)


if __name__ == '__main__':
    testall(argv=sys.argv)
