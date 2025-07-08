import copy

import pandas as pd
import polars as pl

from tdda.referencetest import ReferenceTestCase, tag

from tdda.serial import csv_to_pandas
from tdda.serial.converter import SerialConverter
from tdda.serial.metadata import SerialMetadata
from tdda.serial.reader import load_metadata

from tdda.serial.datautils import tiny_pandas_df, tiny_polars_df


from tdda.serial.testserial import (
    TESTDATADIR,
    tdpath,
    tmppath,
)

from tdda.serial import (
    serial_to_pandas_read_csv_args,
    serial_to_polars_read_csv_args,
    csv_to_polars,
)

from tdda.utils import testwarn

class TestDateSerialConversions(ReferenceTestCase):
    tiny1nd_serial = tdpath('tiny1nd.serial')
    weird_serial = tdpath('tiny1nd-weird.serial')
    IGL = ['tdda.serial-', 'writer']
    def testDeepCopy(self):
        md = load_metadata(self.tiny1nd_serial)
        md2 = copy.deepcopy(md)
        self.assertEqual(str(md), str(md2))
        self.assertIsNot(md.fields[0], md2.fields[0])

    def testCopySerial(self):
        md = load_metadata(self.tiny1nd_serial)
        md2 = md.copy_serial()
        self.assertEqual(str(md), str(md2))
        self.assertIsNot(md.fields[0], md2.fields[0])

    def testSerialToPandas(self):
        md = load_metadata(self.weird_serial)
        # Actually the same as the input
        self.assertStringCorrect(str(md), tdpath('tiny1nd-weird-out.serial'),
                                 ignore_lines=self.IGL)

    def testSerialToPandas(self):
        outpath = tmppath('tiny1nd-weird-pd.serial')
        refpath =  tdpath('tiny1nd-weird-pd-ref.serial')
        c = SerialConverter(self.weird_serial, outpath, out_format='pd.r')
        c.convert()
        self.assertFileCorrect(outpath, refpath, ignore_lines=self.IGL)

        df = csv_to_pandas(tdpath('tiny1nd-dot.csv:'))
        ref_df = tiny_pandas_df(nulls=True, nullable_types=True)
        self.assertDataFramesEqual(df, ref_df, type_matching='strict')


    def testSerialToPandasWeird(self):
        outpath = tmppath('tiny1nd-weird-pd.serial')
        refpath = tdpath('tiny1nd-weird-pd-ref.serial')
        c = SerialConverter(self.weird_serial, outpath, out_format='pd.r')
        c.convert()
        self.assertFileCorrect(outpath, refpath, ignore_lines=self.IGL)

        df = csv_to_pandas(tdpath('tiny1nd-weird.ssv:'))
        ref_df = tiny_pandas_df(nulls=True, nullable_types=True)
        ref_df.columns=['IAmBoolean', 'IAmInt', 'f', 'IAmString', 'IAmDate']
        self.assertDataFramesEqual(df, ref_df, type_matching='strict')

    def testSerialToPandasWeirdOriginal(self):
        outpath = tmppath('tiny1nd-weird-original-pd.serial')
        refpath = tdpath('tiny1nd-weird-pd-original-ref.serial')
        c = SerialConverter(self.weird_serial, outpath, out_format='pd.r',
                            backend='o')
        c.convert()
        self.assertFileCorrect(outpath, refpath, ignore_lines=self.IGL)

        refpath2 = tdpath('tiny1nd-weird-pd-original-ref-no-bool-type.serial')
        df = csv_to_pandas(tdpath('tiny1nd-weird.ssv'), refpath2)
        ref_df = tiny_pandas_df(nulls=True, nullable_types=True)
        ref_df.columns=['IAmBoolean', 'IAmInt', 'f', 'IAmString', 'IAmDate']
        self.assertDataFramesEqual(df, ref_df, type_matching='loose')


    def testSerialToPandasWeird_PyArrow(self):
        outpath = tmppath('tiny1nd-weird-pd.serial')
        refpath = tdpath('tiny1nd-weird-pd-pyarrow-ref.serial')
        c = SerialConverter(self.weird_serial, outpath, out_format='pd.r',
                            backend='pyarrow')
        c.convert()
        self.assertFileCorrect(outpath, refpath, ignore_lines=self.IGL)

        # pyarrow backend can't cope with Yes/No
        Warn, buf = testwarn()
        self.assertRaisesRegex(
            Exception, 'Failed to parse value',
            csv_to_pandas, tdpath('tiny1nd-weird.ssv:'), backend='a',
            warner=Warn
        )

        Warn, buf = testwarn()
        df = csv_to_pandas(tdpath('tiny1nd-weird.ssv'),
                tdpath('tiny1nd-weird-pa-fixes.serial'), backend='a',
                warner=Warn)
        f = lambda x: (
            None if pd.isnull(x)
            else False if x == 'n'
            else True if x == 'Yes'
            else 'error'
        )
        df['IAmBoolean'] = pd.Series(
            [f(v) for v in df['IAmBoolean'].to_list()],
            dtype='boolean[pyarrow]'
        )

        ref_df = tiny_pandas_df(nulls=True, nullable_types=True)
        ref_df.columns = ['IAmBoolean','IAmInt', 'f', 'IAmString', 'IAmDate']
        for (col, typ) in [('IAmBoolean', 'bool[pyarrow]'),
                           ('IAmInt', 'int64[pyarrow]'),
                           ('f', 'double[pyarrow]')]:
            ref_df[col] = ref_df[col].astype(typ)
        self.assertDataFramesEqual(df, ref_df, type_matching='strict')

    def testSerialToPandasWeird_Python_PyArrow(self):
        outpath = tmppath('tiny1nd-weird-pd.serial')
        refpath = tdpath('tiny1nd-weird-pd-pyarrow-ref.py')
        c = SerialConverter(self.weird_serial, outpath, out_format='pd.r',
                            backend='pyarrow')
        c.convert()
        # The Python code generated here does not work because
        # the PyArrow backend can't read the Yes/n booleans.
        self.assertFileCorrect(outpath, refpath, ignore_lines=self.IGL)

    def testSerialToPandasWeird_Python_Original(self):
        outpath = tmppath('tiny1nd-weird-pd-original.serial')
        refpath = tdpath('tiny1nd-weird-pd-original-ref.py')
        c = SerialConverter(self.weird_serial, outpath, out_format='pd.r',
                            backend='o')
        c.convert()
        # The Python code generated here does not work because
        # the PyArrow backend can't read the Yes/n booleans.
        self.assertFileCorrect(outpath, refpath, ignore_lines=self.IGL)

    def testSerialToPandasWeirdCLI(self):
        outpath = tmppath('tiny1nd-weird-pd.serial')
        refpath = tdpath('tiny1nd-weird-pd-ref.serial')
        c = SerialConverter(
            cli_args=[self.weird_serial, outpath, '--to', 'pd.r']
        )
        c.convert()
        self.assertFileCorrect(outpath, refpath, ignore_lines=self.IGL)

    def testSerialToPandasWeirdPythonCLI(self):
        outpath = tmppath('tiny1nd-weird-pd.py')
        refpath = tdpath('tiny1nd-weird-pd-ref.py')
        c = SerialConverter(
            cli_args=[self.weird_serial, outpath, '--to', 'pd.r']
        )
        c.convert()
        self.assertFileCorrect(outpath, refpath, ignore_lines=self.IGL)

    def testSerialToPolarsWeird(self):
        outpath = tmppath('tiny1nd-weird-pl.serial')
        refpath = tdpath('tiny1nd-weird-pl-ref.serial')
        c = SerialConverter(self.weird_serial, outpath, out_format='pl.r')
        Warn, buf = testwarn()
        c.convert(warner=Warn)
        self.assertFileCorrect(outpath, refpath, ignore_lines=self.IGL)
        self.assertEqual(buf,[
  'Polars does not understand escape characters.\nIgnoring escape value: `\n',
  'Field IAmBoolean booleans Yes, y, No, n will not be understood by Polars.\n'
  'If they are present, you may need to set them to pl.String.\n'
  '(Use map_other_bools_to_string=True.)\n',
  'Field IAmDate date format %d/%m/%Y will not be understood by Polars.\n'
  'Setting to pl.String.'
        ])

    def testSerialToPolarsPythonWeird(self):
        outpath = tmppath('tiny1nd-weird-pl.py')
        refpath = tdpath('tiny1nd-weird-pl-ref.py')
        c = SerialConverter(self.weird_serial, outpath, out_format='pl.r')
        Warn, buf = testwarn()
        c.convert(warner=Warn)
        self.assertFileCorrect(outpath, refpath, ignore_lines=self.IGL)
        self.assertEqual(len(buf), 3)  # Escape; Booleans; date format

    def testCSVWToSerial(self):
        csvwpath = tdpath('tiny1nd-weird-no-rename-metadata.json')
        outpath = tmppath('tiny1nd-weird-no-rename-from-csvw.serial')
        refpath =  tdpath('tiny1nd-weird-no-rename-from-csvw.serial')

        c = SerialConverter(csvwpath, outpath)
        Warn, buf = testwarn()
        c.convert(warner=Warn)
        self.assertFileCorrect(outpath, refpath)
        self.assertEqual(buf, [])


    def testCSVWToSerialPandas(self):
        csvwpath = tdpath('tiny1nd-weird-no-rename-metadata.json')
        outpath_pd = tmppath('tiny1nd-weird-no-rename-from-csvw-pd.serial')
        refpath_pd =  tdpath('tiny1nd-weird-no-rename-from-csvw-pd.serial')

        outpath_py = tmppath('tiny1nd-weird-no-rename-from-csvw-pd.py')
        refpath_py =  tdpath('tiny1nd-weird-no-rename-from-csvw-pd.py')

        c = SerialConverter(csvwpath, outpath_pd, out_format='pd.r')
        c.convert()
        self.assertFileCorrect(outpath_pd, refpath_pd, ignore_lines=self.IGL)

        c = SerialConverter(csvwpath, outpath_py, out_format='pd.r')
        c.convert()
        self.assertFileCorrect(outpath_py, refpath_py, ignore_lines=self.IGL)

        df = csv_to_pandas(tdpath('tiny1nd-weird.ssv'), refpath_pd)
        ref_df = tiny_pandas_df(nulls=True, nullable_types=True)
        self.assertDataFramesEqual(df, ref_df, type_matching='strict')

    @tag
    def testCSVWToSerialPolars(self):
        csvwpath = tdpath('tiny1nd-weird-no-rename-metadata.json')
        outpath_pl = tmppath('tiny1nd-weird-no-rename-from-csvw-pl.serial')
        refpath_pl =  tdpath('tiny1nd-weird-no-rename-from-csvw-pl.serial')
        refpath_pl2 = tdpath('tiny1nd-weird-no-rename-from-csvw-pl2.serial')

        outpath_py = tmppath('tiny1nd-weird-no-rename-from-csvw-pl.py')
        refpath_py =  tdpath('tiny1nd-weird-no-rename-from-csvw-pl.py')

        Warn, buf = testwarn()
        c = SerialConverter(csvwpath, outpath_pl, out_format='pl.r')
        c.convert(warner=Warn)
        self.assertFileCorrect(outpath_pl, refpath_pl, ignore_lines=self.IGL)
        self.assertEqual(buf, [
  'Polars will not understand the following boolean values:\n'
  ' Yes, n.\n'
  'If they actually occur in the file, fields will need to be set to string.\n'
  '(Use map_other_bools_to_string=True.)\n',
  'Field t date format %d/%m/%Y will not be understood by Polars.\n'
  'Setting to pl.String.']
        )

        Warn, buf = testwarn()
        c = SerialConverter(csvwpath, outpath_py, out_format='pl.r')
        c.convert(warner=Warn)
        self.assertFileCorrect(outpath_py, refpath_py, ignore_lines=self.IGL)
        self.assertEqual(len(buf), 2)  # boleans, date


        Warn, buf = testwarn()
        c = SerialConverter(csvwpath, outpath_pl, out_format='pl.r',
                            map_other_bools_to_string=True)
        c.convert(warner=Warn)
        self.assertFileCorrect(outpath_pl, refpath_pl2, ignore_lines=self.IGL)

        Warn, buf = testwarn()
        df = csv_to_polars(tdpath('tiny1nd-weird.ssv'), refpath_pl2,
                           warner=Warn)
        ref_df = tiny_polars_df(nulls=True, sNullNull=True,
                                euroStrDates=True, sBools=True)
        self.assertDataFramesEqual(df, ref_df, type_matching='strict')



if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
