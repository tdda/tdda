"""
Run all TDDA tests
"""

import os
import sys

from tdda.state import set_testing
from tdda.referencetest import ReferenceTestCase

from tdda.constraints.testconstraints import *
from tdda.rexpy.testrexpy import *
from tdda.referencetest.tests.alltests import *
from tdda.serial.testserialmetadata import *
from tdda.testutils import *

# Set the enviroment variable TDDA_CONFIG_TESTS to something (e.g. 1)
# to report on environment from within which tests are run
TDDA_CONFIG_TESTS = 'TDDA_CONFIG_TESTS' in os.environ
set_testing(True)


if TDDA_CONFIG_TESTS:
    print('Performing configuration tests (reporting)', file=sys.stderr)
    from tdda.testconfig import *
else:
    pass


def run_all_tests(module=None, argv=None):
    ReferenceTestCase.main(module=module, argv=argv, testtdda=True)


if __name__ == '__main__':
    run_all_tests(argv=sys.argv)
