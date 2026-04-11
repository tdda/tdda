# -*- coding: utf-8 -*-
import sys
import unittest

from tdda.constraints.testbase import *
from tdda.referencetest import ReferenceTestCase

from tdda.constraints.pd.testpdconstraints import *
from tdda.constraints.test_discover_bookex12 import *
from tdda.constraints.test_verify_bookex13 import *
from tdda.constraints.test_detect_bookex17 import *

# try:
if 1:
    from tdda.constraints.db.testdbconstraints import (
        TestSQLiteDB,
        TestPostgresDB,
        TestMySQLDB,
    )
    # The individual imports of the database driver libraries
    # are now all protected with try...except blocks,
    # so this try...except is probably now unnecessary.
# except ImportError:
#    print('Skipping Database tests', file=sys.stderr)


from tdda.constraints.testcommonconstraints import *

if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
