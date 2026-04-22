from tdda.referencetest import ReferenceTestCase, tag

from tdda.serial.testcommonserial import *
from tdda.serial.testpdserial import *
from tdda.serial.testplserial import *
from tdda.serial.testconversion import *
from tdda.serial.testinference import *
from tdda.serial.testbookserial import *
from tdda.serial.testdateformats import *


if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
