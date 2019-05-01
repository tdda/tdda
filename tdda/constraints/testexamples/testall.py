from tdda.referencetest import ReferenceTestCase

from test_detect import TestDETECT
from test_discover1k import TestDISCOVER1K
from test_discover25k import TestDISCOVER25K
from test_examples import TestEXAMPLES
from test_verify import TestVERIFY
from test_verify2 import TestVERIFY2
from test_verify_fail import TestVERIFY_FAIL
from test_verify_fail2 import TestVERIFY_FAIL2

if __name__ == '__main__':
    ReferenceTestCase.main()
