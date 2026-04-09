from tdda.referencetest import ReferenceTestCase, tag

from tdda.serial.testcommonserial import *
from tdda.serial.testpdserial import *
from tdda.serial.testplserial import *
from tdda.serial.testconversion import *
from tdda.serial.testbookserial import *


if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
