# -*- coding: utf-8 -*-
import sys
import unittest

from tdda.constraints.testbase import *
from tdda.referencetest import ReferenceTestCase

try:
    from tdda.constraints.pd.testpdconstraints import *
except ImportError:
    print('Skipping Pandas tests', file=sys.stderr)

try:
    from tdda.constraints.db.testdbconstraints import *
    # The individual imports of the database driver libraries
    # are now all protected with try...except blocks,
    # so this try...except is probably now unnecessary.
except ImportError:
    print('Skipping Database tests', file=sys.stderr)


if __name__ == '__main__':
    ReferenceTestCase.main()
