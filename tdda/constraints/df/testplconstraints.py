# -*- coding: utf-8 -*-

"""
Concrete polars test classes for DataFrame constraint tests.
Populated incrementally as each operation is implemented.
"""

from tdda.referencetest import ReferenceTestCase, tag

from tdda.constraints.df.dftestbase import (
    DFVerifyBase,
    DFDiscoverBase,
    DFDetectBase,
    DFCommandBase,
)
from tdda.utils import CONSTRAINTSTESTDATADIR as TESTDATADIR


class TestPolarsVerify(ReferenceTestCase, DFVerifyBase):
    engine = 'polars'

TestPolarsVerify.set_default_data_location(TESTDATADIR)


class TestPolarsDiscover(ReferenceTestCase, DFDiscoverBase):
    engine = 'polars'

TestPolarsDiscover.set_default_data_location(TESTDATADIR)


@tag
class TestPolarsDetect(ReferenceTestCase, DFDetectBase):
    engine = 'polars'

TestPolarsDetect.set_default_data_location(TESTDATADIR)


if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
