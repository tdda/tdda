import copy

from tdda.referencetest import ReferenceTestCase, tag

from tdda.serial.converter import SerialConverter
from tdda.serial.metadata import SerialMetadata
from tdda.serial.reader import load_metadata


from tdda.serial.testserial import (
    TESTDATADIR,
    tdpath,
    tmppath,
)

class TestDateSerialConversions(ReferenceTestCase):
    tiny1cd_serial = tdpath('tiny1cd.serial')
    weird_serial = tdpath('tiny1weird.serial')
    IGL = ['tdda.serial-', 'writer']
    def testDeepCopy(self):
        md = load_metadata(self.tiny1cd_serial)
        md2 = copy.deepcopy(md)
        self.assertEqual(str(md), str(md2))
        self.assertIsNot(md.fields[0], md2.fields[0])

    def testCopySerial(self):
        md = load_metadata(self.tiny1cd_serial)
        md2 = md.copy_serial()
        self.assertEqual(str(md), str(md2))
        self.assertIsNot(md.fields[0], md2.fields[0])

    def testSerialToPandas(self):
        md = load_metadata(self.weird_serial)
        # Actually the same as the input
        self.assertStringCorrect(str(md), tdpath('weird-out.serial'),
                                 ignore_lines=self.IGL)

    def testSerialToPandas(self):
        outpath = tmppath('weird-pd1.serial')
        refpath = tdpath('weird-pd1-ref.serial')
        c = SerialConverter(self.weird_serial, outpath, out_format='pd.r')
        c.convert()
        self.assertFileCorrect(outpath, refpath, ignore_lines=self.IGL)


    def testSerialToPandasWeird(self):
        outpath = tmppath('weird-pd1.serial')
        refpath = tdpath('weird-pd1-ref.serial')
        c = SerialConverter(self.weird_serial, outpath, out_format='pd.r')
        c.convert()
        self.assertFileCorrect(outpath, refpath, ignore_lines=self.IGL)

    def testSerialToPandasWeirdCLI(self):
        outpath = tmppath('weird-pd1.serial')
        refpath = tdpath('weird-pd1-ref.serial')
        c = SerialConverter(
            cli_args=[self.weird_serial, outpath, '--to', 'pd.r']
        )
        c.convert()
        self.assertFileCorrect(outpath, refpath, ignore_lines=self.IGL)

if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
