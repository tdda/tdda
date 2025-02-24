"""
Run all TDDA tests
"""

import os
import sys

from tdda.referencetest import ReferenceTestCase

from tdda.constraints.testconstraints import *
from tdda.rexpy.testrexpy import *
from tdda.referencetest.tests.alltests import *
from tdda.serial.testserialmetadata import *

# Set the enviroment variable TDDA_CONFIG_TESTS to something (e.g. 1)
# to report on environment from within which tests are run
TDDA_CONFIG_TESTS = 'TDDA_CONFIG_TESTS' in os.environ


if TDDA_CONFIG_TESTS:
    print('Performing configuration tests (reporting)', file=sys.stderr)
    from tdda.testconfig import *
else:
    pass


def testall(module=None, argv=None):
    os.environ['TDDA_TESTING'] = 'TRUE'
    ReferenceTestCase.main(module=module, argv=argv)


if __name__ == '__main__':
    testall(argv=sys.argv)
