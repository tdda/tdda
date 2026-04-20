# -*- coding: utf-8 -*-
#
# Run all the unit-tests for the referencetest module.
#


from tdda.referencetest import ReferenceTestCase

from tdda.referencetest.tests.testbase import *
from tdda.referencetest.tests.teststrings import *
from tdda.referencetest.tests.testfiles import *
from tdda.referencetest.tests.testpandas import *
from tdda.referencetest.tests.testpolars import *
from tdda.referencetest.tests.testreftestutils import *
from tdda.referencetest.tests.testregeneration import *
from tdda.referencetest.tests.testpddfcomparisons import *
from tdda.referencetest.tests.testpldfcomparisons import *
from tdda.referencetest.tests.testutils import *


if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
