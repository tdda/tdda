# -*- coding: utf-8 -*-
#
# Run all the unit-tests for the referencetest module.
#

from __future__ import absolute_import
from __future__ import unicode_literals

import unittest

from tdda.referencetest.tests.testbase import *
from tdda.referencetest.tests.teststrings import *
from tdda.referencetest.tests.testfiles import *
from tdda.referencetest.tests.testpandas import *
from tdda.referencetest.tests.testregeneration import *

if __name__ == '__main__':
    unittest.main()

