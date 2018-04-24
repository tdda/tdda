# -*- coding: utf-8 -*-
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

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
except ImportError:
    print('Skipping Database tests', file=sys.stderr)


if __name__ == '__main__':
    ReferenceTestCase.main()
