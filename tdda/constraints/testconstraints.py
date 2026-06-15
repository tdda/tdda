# -*- coding: utf-8 -*-
import sys
import unittest

from tdda.constraints.testbase import *
from tdda.referencetest import ReferenceTestCase

from tdda.constraints.df.testdfconstraints import *
from tdda.constraints.df.testpdconstraints import *
from tdda.constraints.df.testplconstraints import *
from tdda.constraints.test_discover_bookex12 import *
from tdda.constraints.test_verify_bookex13 import *
from tdda.constraints.test_detect_bookex17 import *

from tdda.constraints.db.testdbconstraints import (
    TestSQLiteDB,
    TestPostgresDB,
    TestMySQLDB,
)


from tdda.constraints.testcommonconstraints import *

if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
