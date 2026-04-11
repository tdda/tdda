import copy
import json

from collections import namedtuple

import pandas as pd
import polars as pl

from tdda.referencetest import ReferenceTestCase, tag

from tdda.serial import csv_to_pandas
from tdda.serial.converter import SerialConverter
from tdda.serial.csvw import serial_to_csvw, CSVWMetadata
from tdda.serial.datautils import tiny_pandas_df, tiny_polars_df
from tdda.serial.frictionless import (
    serial_to_frictionless,
    FrictionlessMetadata,
)
from tdda.serial.metadata import SerialMetadata, FieldType
from tdda.serial.reader import load_metadata
from tdda.serial.infer import (
    analyse_values,
    careful_split,
    infer_format_from_flat_file,
)


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

TDDA_SERIAL_VERSION_RE = r'tdda\.serial\-[0-9]+.[0-9]+\.[0-9]+[rc0-9]*'

Spec = namedtuple('Spec', 'generate formats broad_out inpath outpath')


class TestSerialConversions(ReferenceTestCase):
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
        self.assertStringCorrect(
            str(md), tdpath('tiny1nd-weird-out.serial'), ignore_lines=self.IGL
        )

    def testSerialToPandas2(self):
        name = 'tiny1nd-weird-pd.serial'
        outpath = tmppath(name)
        refpath = tdpath(name)
        c = SerialConverter(self.weird_serial, outpath, out_format='pd.r')
        c.convert()
        self.assertFileCorrect(outpath, refpath, ignore_lines=self.IGL)

        df = csv_to_pandas(tdpath('tiny1nd-dot.csv:'))
        ref_df = tiny_pandas_df(nulls=True, nullable_types=True)
        self.assertDataFramesEqual(df, ref_df, type_matching='strict')

    def testSerialToPandasWeird(self):
        # serial to serial specifying pd.r
        name = 'tiny1nd-weird-pd.serial'
        outpath = tmppath(name)
        refpath = tdpath(name)
        c = SerialConverter(self.weird_serial, outpath, out_format='pd.r')
        c.convert()
        self.assertFileCorrect(outpath, refpath, ignore_lines=self.IGL)

        df = csv_to_pandas(tdpath('tiny1nd-weird.ssv:'))
        ref_df = tiny_pandas_df(
            nulls=True, nullable_types=True, longNames=True
        )
        self.assertDataFramesEqual(df, ref_df, type_matching='strict')

    def testSerialToPandasWeirdOriginal(self):
        name = 'tiny1nd-weird-original-pd.serial'
        outpath = tmppath(name)
        refpath = tdpath(name)
        c = SerialConverter(
            self.weird_serial, outpath, out_format='pd.r', backend='o'
        )
        c.convert()
        self.assertFileCorrect(outpath, refpath, ignore_lines=self.IGL)

        refpath2 = tdpath('tiny1nd-weird-pd-original-no-bool-type.serial')
        df = csv_to_pandas(tdpath('tiny1nd-weird.ssv'), refpath2)
        ref_df = tiny_pandas_df(
            nulls=True, nullable_types=True, longNames=True
        )

        self.assertDataFramesEqual(df, ref_df, type_matching='loose')

    def testSerialToPandasWeird_PyArrow(self):
        name = 'tiny1nd-weird-pd-pyarrow.serial'
        outpath = tmppath(name)
        refpath = tdpath(name)
        c = SerialConverter(
            self.weird_serial, outpath, out_format='pd.r', backend='pyarrow'
        )
        c.convert()
        self.assertFileCorrect(outpath, refpath, ignore_lines=self.IGL)

        # pyarrow backend can't cope with Yes/No
        Warn, buf = testwarn()
        self.assertRaisesRegex(
            Exception,
            'Failed to parse value',
            csv_to_pandas,
            tdpath('tiny1nd-weird.ssv:'),
            backend='a',
            warner=Warn,
        )

        Warn, buf = testwarn()
        df = csv_to_pandas(
            tdpath('tiny1nd-weird.ssv'),
            tdpath('tiny1nd-weird-pa-fixes.serial'),
            backend='a',
            warner=Warn,
        )
        f = lambda x: (
            None
            if pd.isnull(x)
            else False
            if x == 'n'
            else True
            if x == 'Yes'
            else 'error'
        )
        df['IAmBoolean'] = pd.Series(
            [f(v) for v in df['IAmBoolean'].to_list()],
            dtype='boolean[pyarrow]',
        )

        ref_df = tiny_pandas_df(
            nulls=True, nullable_types=True, longNames=True
        )
        for col, typ in [
            ('IAmBoolean', 'bool[pyarrow]'),
            ('IAmInt', 'int64[pyarrow]'),
            ('f', 'double[pyarrow]'),
        ]:
            ref_df[col] = ref_df[col].astype(typ)
        self.assertDataFramesEqual(df, ref_df, type_matching='strict')

    def testSerialToPandasWeird_Python_PyArrow(self):
        name = 'tiny1nd_weird_pd_pyarrow.py'
        outpath = tmppath(name)
        refpath = tdpath(name)
        c = SerialConverter(
            self.weird_serial, outpath, out_format='pd.r', backend='pyarrow'
        )
        c.convert()
        # The Python code generated here does not work because
        # the PyArrow backend can't read the Yes/n booleans.
        self.assertFileCorrect(outpath, refpath, ignore_lines=self.IGL)

        # Would now try running the generated code.

        # But this fails, because the PyArrow backend can't read
        # Yes/n booleans.
        # Not much point checking for the Exception here

    def testSerialToPandasWeird_Python_Original(self):
        name = 'tiny1nd_weird_pd_original.py'
        outpath = tmppath(name)
        refpath = tdpath(name)
        c = SerialConverter(
            self.weird_serial, outpath, out_format='pd.r', backend='o'
        )
        c.convert()
        self.assertFileCorrect(outpath, refpath)

        # Now actually run the generated code (well, code that's
        # identical to the generated code)

        from tdda.serial.testdata.tiny1nd_weird_pd_original import read_data

        df = read_data(tdpath('tiny1nd-weird.ssv'))

        # Dataframe is correct except for string IAmBoolean
        ref_df = tiny_pandas_df(
            nulls=True, nullable_types=False, sBools=True, longNames=True
        )
        self.assertDataFramesEqual(df, ref_df, type_matching='strict')

    def testSerialToPandasWeirdCLI(self):
        name = 'tiny1nd-weird-pd.serial'
        outpath = tmppath(name)
        refpath = tdpath(name)
        c = SerialConverter(
            cli_args=[self.weird_serial, outpath, '--to', 'pd.r']
        )
        c.convert()
        self.assertFileCorrect(outpath, refpath, ignore_lines=self.IGL)

    def testSerialToPandasWeirdPythonCLI(self):
        name = 'tiny1nd_weird_pd.py'
        outpath = tmppath(name)
        refpath = tdpath(name)
        c = SerialConverter(
            cli_args=[self.weird_serial, outpath, '--to', 'pd.r']
        )
        c.convert()
        self.assertFileCorrect(outpath, refpath)

        # Run the 'generated' code
        from tdda.serial.testdata.tiny1nd_weird_pd import read_data

        df = read_data(tdpath('tiny1nd-weird.ssv'))
        ref_df = tiny_pandas_df(
            nulls=True, nullable_types=True, longNames=True
        )
        self.assertDataFramesEqual(df, ref_df, type_matching='strict')

    def testSerialToPolarsWeird(self):
        name = 'tiny1nd-weird-pl.serial'
        outpath = tmppath(name)
        refpath = tdpath(name)
        c = SerialConverter(self.weird_serial, outpath, out_format='pl.r')
        Warn, buf = testwarn()
        c.convert(warner=Warn)
        self.assertFileCorrect(outpath, refpath, ignore_lines=self.IGL)
        self.assertEqual(
            buf,
            [
                'Polars does not understand escape characters.\nIgnoring escape value: `\n',
                'Field IAmBoolean booleans Yes, y, No, n will not be understood by Polars.\n'
                'If they are present, you may need to set them to pl.String.\n'
                '(Use map_other_bools_to_string=True.)\n',
                'Field IAmDate date format %d/%m/%Y will not be understood by Polars read_csv.\n'
                'Will parse post-read using str.to_datetime.',
            ],
        )

    def testSerialToPolarsPythonWeird(self):
        name = 'tiny1nd_weird_pl.py'
        outpath = tmppath(name)
        refpath = tdpath(name)
        c = SerialConverter(self.weird_serial, outpath, out_format='pl.r')
        Warn, buf = testwarn()
        c.convert(warner=Warn)
        self.assertFileCorrect(outpath, refpath, ignore_lines=self.IGL)
        self.assertEqual(len(buf), 3)  # Escape; Booleans; date format

    def testInferMetadataWeird(self):
        md = infer_format_from_flat_file(
            tdpath('tiny1nd-weird.ssv'), verbosity=0
        )
        self.assertStringCorrect(
            md.to_json(),
            tdpath('tiny1nd-weird-inferred.serial'),
            ignore_lines=self.IGL,
        )

    def testInferMetadataTiny1cdq(self):
        md = infer_format_from_flat_file(tdpath('tiny1ndq.csv'), verbosity=0)
        # self.assertStringCorrect(md.to_json(),
        #                          tdpath('tiny1nd-weird-inferred.serial'),
        #                          ignore_lines=self.IGL)

    def test_careful_split(self):
        # Trivial cases
        c = lambda s: careful_split(s, ',', '"', '\\')
        self.assertEqual(c(''), [''])
        self.assertEqual(c('1'), ['1'])
        self.assertEqual(
            c(
                '1,2',
            ),
            ['1', '2'],
        )
        self.assertEqual(c('"a"'), ['"a"'])
        self.assertEqual(c('"a","b"'), ['"a"', '"b"'])

        self.assertEqual(c('"a,b"'), ['"a,b"'])
        self.assertEqual(c('"a,b","1,2,3"'), ['"a,b"', '"1,2,3"'])

        self.assertEqual(c('"a""b","1,2,3"'), ['"a""b"', '"1,2,3"'])
        self.assertEqual(c('"a"b","1,2,3"'), ['"a"b"', '"1,2,3"'])

        # escape handling done before
        self.assertEqual(c(r'"a\,b","1,2,3"'), [r'"a\,b"', '"1,2,3"'])

    def testInferMetadataWeirdCLI(self):
        inpath = tdpath('tiny1nd-weird.ssv')
        outpath = tmppath('tiny1nd-weird-inferred2.serial')
        c = SerialConverter(cli_args=[inpath, outpath, '-g', '-q'])
        c.convert()
        self.assertFileCorrect(
            outpath,
            tdpath('tiny1nd-weird-inferred.serial'),
            ignore_lines=self.IGL,
        )

    def testCSVWToSerial(self):
        csvwpath = tdpath('tiny1nd-weird-no-rename-metadata.json')
        outpath = tmppath('tiny1nd-weird-no-rename-from-csvw.serial')
        refpath = tdpath('tiny1nd-weird-no-rename-from-csvw.serial')

        c = SerialConverter(csvwpath, outpath, verbosity=1)
        Warn, buf = testwarn()
        c.convert(warner=Warn)
        self.assertFileCorrect(
            outpath, refpath, ignore_patterns=[TDDA_SERIAL_VERSION_RE]
        )
        self.assertEqual(buf, [])

    def testCSVWToSerialPandas(self):
        csvwpath = tdpath('tiny1nd-weird-no-rename-metadata.json')
        outpath_pd = tmppath('tiny1nd-weird-no-rename-from-csvw-pd.serial')
        refpath_pd = tdpath('tiny1nd-weird-no-rename-from-csvw-pd.serial')

        outpath_py = tmppath('tiny1nd_weird_no_rename_from_csvw_pd.py')
        refpath_py = tdpath('tiny1nd_weird_no_rename_from_csvw_pd.py')

        c = SerialConverter(csvwpath, outpath_pd, out_format='pd.r')
        c.convert()
        self.assertFileCorrect(outpath_pd, refpath_pd, ignore_lines=self.IGL)

        c = SerialConverter(csvwpath, outpath_py, out_format='pd.r')
        c.convert()
        self.assertFileCorrect(outpath_py, refpath_py, ignore_lines=self.IGL)

        df = csv_to_pandas(tdpath('tiny1nd-weird.ssv'), refpath_pd)
        ref_df = tiny_pandas_df(nulls=True, nullable_types=True)
        self.assertDataFramesEqual(df, ref_df, type_matching='strict')

        from tdda.serial.testdata.tiny1nd_weird_no_rename_from_csvw_pd import (
            read_data,
        )

        df = read_data(tdpath('tiny1nd-weird.ssv'))
        self.assertDataFramesEqual(df, ref_df, type_matching='strict')

    def testCSVWToSerialPolars(self):
        # Without different field names in CSVW from flat file
        csvwpath = tdpath('tiny1nd-weird-no-rename-metadata.json')

        name = 'tiny1nd-weird-no-rename-from-csvw-pl.serial'
        outpath_pl = tmppath(name)
        refpath_pl = tdpath(name)

        Warn, buf = testwarn()
        c = SerialConverter(csvwpath, outpath_pl, out_format='pl.r')
        c.convert(warner=Warn)
        self.assertFileCorrect(outpath_pl, refpath_pl, ignore_lines=self.IGL)
        self.assertEqual(
            buf,
            [
                'Polars will not understand the following boolean values:\n'
                ' Yes, n.\n'
                'If they actually occur in the file, fields will need to be set to string.\n'
                '(Use map_other_bools_to_string=True.)\n',
                'Field t date format %d/%m/%Y will not be understood by Polars read_csv.\n'
                'Will parse post-read using str.to_date.',
            ],
        )

    def testCSVWToSerialPolarsPython(self):
        csvwpath = tdpath('tiny1nd-weird-no-rename-metadata.json')
        py_name = 'tiny1nd_weird_no_rename_from_csvw_pl.py'
        outpath_py = tmppath(py_name)
        refpath_py = tdpath(py_name)

        Warn, buf = testwarn()
        c = SerialConverter(csvwpath, outpath_py, out_format='pl.r')
        c.convert(warner=Warn)
        self.assertFileCorrect(outpath_py, refpath_py, ignore_lines=self.IGL)
        self.assertEqual(len(buf), 2)  # booleans, date
        # ^^^ Code doesn't work because of booleans. But does warn.

    def testCSVWToSerialPolars2(self):
        csvwpath = tdpath('tiny1nd-weird-no-rename-metadata.json')
        name2 = 'tiny1nd-weird-no-rename-from-csvw-pl2.serial'
        outpath_pl2 = tmppath(name2)
        refpath_pl2 = tdpath(name2)

        Warn, buf = testwarn()
        c = SerialConverter(
            csvwpath,
            outpath_pl2,
            out_format='pl.r',
            map_other_bools_to_string=True,
        )
        c.convert(warner=Warn)
        self.assertFileCorrect(outpath_pl2, refpath_pl2, ignore_lines=self.IGL)

        Warn, buf = testwarn()
        df = csv_to_polars(
            tdpath('tiny1nd-weird.ssv'), refpath_pl2, warner=Warn
        )
        ref_df = tiny_polars_df(
            nulls=True, sNullNull=True, euroStrDates=True, sBools=True
        )
        self.assertDataFramesEqual(df, ref_df, type_matching='strict')

    def testCSVWToSerialPolarsWithRename(self):
        csvwpath = tdpath('tiny1nd-weird-metadata.json')

        name = 'tiny1nd-weird-from-csvw-pl.serial'
        outpath_pl = tmppath(name)
        refpath_pl = tdpath(name)

        Warn, buf = testwarn()
        c = SerialConverter(csvwpath, outpath_pl, out_format='pl.r')
        c.convert(warner=Warn)
        self.assertFileCorrect(outpath_pl, refpath_pl, ignore_lines=self.IGL)
        self.assertEqual(
            buf,
            [
                'Polars will not understand the following boolean values:\n'
                ' Yes, n.\n'
                'If they actually occur in the file, fields will need to be set to string.\n'
                '(Use map_other_bools_to_string=True.)\n',
                'Field IAmDate date format %d/%m/%Y will not be understood by Polars read_csv.\n'
                'Will parse post-read using str.to_date.',
            ],
        )

    def testCSVWToSerialPolarsWithRenamePython(self):
        csvwpath = tdpath('tiny1nd-weird-metadata.json')
        py_name = 'tiny1nd_weird_from_csvw_pl.py'
        outpath_py = tmppath(py_name)
        refpath_py = tdpath(py_name)

        Warn, buf = testwarn()
        c = SerialConverter(csvwpath, outpath_py, out_format='pl.r')
        c.convert(warner=Warn)
        self.assertFileCorrect(outpath_py, refpath_py)
        self.assertEqual(len(buf), 2)  # booleans, date
        # ^^^ Code doesn't work because of booleans. But does warn.

    def testCSVWToSerialPolarsWithRename2(self):
        csvwpath = tdpath('tiny1nd-weird-metadata.json')
        name2 = 'tiny1nd-weird-from-csvw-pl2.serial'
        outpath_pl2 = tmppath(name2)
        refpath_pl2 = tdpath(name2)

        Warn, buf = testwarn()
        c = SerialConverter(
            csvwpath,
            outpath_pl2,
            out_format='pl.r',
            map_other_bools_to_string=True,
        )
        c.convert(warner=Warn)
        self.assertFileCorrect(outpath_pl2, refpath_pl2, ignore_lines=self.IGL)

        Warn, buf = testwarn()
        df = csv_to_polars(
            tdpath('tiny1nd-weird.ssv'), refpath_pl2, warner=Warn
        )
        ref_df = tiny_polars_df(
            nulls=True,
            sNullNull=True,
            euroStrDates=True,
            sBools=True,
            longNames=True,
        )
        self.assertDataFramesEqual(df, ref_df, type_matching='strict')

    def testInferMetadataSimple(self):
        md = infer_format_from_flat_file(tdpath('simple.csv'), verbosity=1)
        self.assertStringCorrect(
            md.to_json(),
            tdpath('simple-inferred.serial'),
            ignore_lines=self.IGL,
        )

    def testInferMetadataMinimal(self):
        md = infer_format_from_flat_file(tdpath('minimal.csv'), verbosity=1)
        self.assertStringCorrect(
            md.to_json(),
            tdpath('minimal-inferred.serial'),
            ignore_lines=self.IGL,
        )

    def testConversionToCSVWObject(self):
        tiny1nd_serial = tdpath('tiny1nd.serial')
        md = load_metadata(self.tiny1nd_serial)
        csvw = serial_to_csvw(md, 'tiny1nd.csv')
        csvw_ref = tdpath('tiny1nd-metadata.json')
        self.assertStringCorrect(
            csvw.to_json(), csvw_ref, ignore_lines=self.IGL
        )

    def testConversionToCSVW_t1nds(self):
        tiny1nd_serial = tdpath('tiny1nd.serial')
        md = load_metadata(self.tiny1nd_serial)
        csvw_md = serial_to_csvw(md)
        csvw_json = csvw_md.to_csvw_json('tiny1nd.csv')
        self.assertStringCorrect(
            csvw_json, tdpath('tiny1nd-metadata.json'), ignore_lines=self.IGL
        )

    def testConversionToCSVW_t1nds_file(self):
        tiny1nd_serial = tdpath('tiny1nd.serial')
        md = load_metadata(self.tiny1nd_serial)
        csvw_md = serial_to_csvw(md)
        outpath = tmppath('tiny1nd-metadata.json')
        csvw_md.write_csvw(outpath)
        self.assertFileCorrect(
            outpath, tdpath('tiny1nd-metadata.json'), ignore_lines=self.IGL
        )

    def testConversionToCSVW_t1nds_file_cli(self):
        tiny1nd_serial = tdpath('tiny1nd.serial')
        outpath = tmppath('tiny1nd-metadata.json')
        c = SerialConverter(cli_args=[tiny1nd_serial, outpath])
        c.convert()
        self.assertFileCorrect(
            outpath, tdpath('tiny1nd-metadata.json'), ignore_lines=self.IGL
        )

    def testFrictionlessPackageToSerialYAML(self):
        frictionlesspath = tdpath(f'tiny1nd-weird-no-rename.package.yaml')
        name = 'tiny1nd-weird-no-rename-from-fless-package.serial'
        yname = 'tiny1nd-weird-no-rename-from-fless-yaml.package.serial'
        outpath = tmppath(yname)
        refpath = tdpath(name)

        c = SerialConverter(frictionlesspath, outpath)
        Warn, buf = testwarn()
        c.convert(warner=Warn)
        self.assertFileCorrect(
            outpath, refpath, ignore_patterns=[TDDA_SERIAL_VERSION_RE]
        )
        self.assertEqual(buf, [])

    def testFrictionlessResourceToSerialYAML(self):
        frictionlesspath = tdpath('tiny1nd-weird-no-rename.resource.yaml')
        name = 'tiny1nd-weird-no-rename-from-fless-resource.serial'
        yname = 'tiny1nd-weird-no-rename-from-fless-yaml.resource.serial'
        outpath = tmppath(yname)
        refpath = tdpath(name)

        c = SerialConverter(frictionlesspath, outpath)
        Warn, buf = testwarn()
        c.convert(warner=Warn)
        self.assertFileCorrect(
            outpath, refpath, ignore_patterns=[TDDA_SERIAL_VERSION_RE]
        )
        self.assertEqual(buf, [])

    def testFrictionlessPackageToSerialJSON(self):
        frictionlesspath = tdpath(f'tiny1nd-weird-no-rename.package.json')
        name = 'tiny1nd-weird-no-rename-from-fless-package.serial'
        jname = 'tiny1nd-weird-no-rename-from-fless-json.package.serial'
        outpath = tmppath(jname)
        refpath = tdpath(name)

        c = SerialConverter(frictionlesspath, outpath)
        Warn, buf = testwarn()
        c.convert(warner=Warn)
        self.assertFileCorrect(
            outpath, refpath, ignore_patterns=[TDDA_SERIAL_VERSION_RE]
        )
        self.assertEqual(buf, [])

    def testFrictionlessResourceToSerialJSON(self):
        frictionlesspath = tdpath('tiny1nd-weird-no-rename.resource.json')
        name = 'tiny1nd-weird-no-rename-from-fless-resource.serial'
        jname = 'tiny1nd-weird-no-rename-from-fless-json.resource.serial'
        outpath = tmppath(jname)
        refpath = tdpath(name)

        c = SerialConverter(frictionlesspath, outpath)
        Warn, buf = testwarn()
        c.convert(warner=Warn)
        self.assertFileCorrect(
            outpath, refpath, ignore_patterns=[TDDA_SERIAL_VERSION_RE]
        )
        self.assertEqual(buf, [])

    def testFrictionlessToSerialPandas(self):
        frictionlesspath = tdpath('tiny1nd-weird-no-rename.resource.json')
        outpath_pd = tmppath('tiny1nd-weird-no-rename-from-fless-pd.serial')
        refpath_pd = tdpath('tiny1nd-weird-no-rename-from-fless-pd.serial')

        outpath_py = tmppath('tiny1nd_weird_no_rename_from_fless_pd.py')
        refpath_py = tdpath('tiny1nd_weird_no_rename_from_fless_pd.py')

        c = SerialConverter(frictionlesspath, outpath_pd, out_format='pd.r')
        c.convert()
        self.assertFileCorrect(outpath_pd, refpath_pd, ignore_lines=self.IGL)

        c = SerialConverter(frictionlesspath, outpath_py, out_format='pd.r')
        c.convert()
        self.assertFileCorrect(outpath_py, refpath_py, ignore_lines=self.IGL)

        df = csv_to_pandas(tdpath('tiny1nd-weird.ssv'), refpath_pd)
        ref_df = tiny_pandas_df(nulls=True, nullable_types=True)
        self.assertDataFramesEqual(df, ref_df, type_matching='strict')

        from tdda.serial.testdata.tiny1nd_weird_no_rename_from_fless_pd import (
            read_data,
        )

        df = read_data(tdpath('tiny1nd-weird.ssv'))
        self.assertDataFramesEqual(df, ref_df, type_matching='strict')

    def testFrictionlessToSerialPolars(self):
        # Without different field names in Frictionless from flat file
        frictionlesspath = tdpath('tiny1nd-weird-no-rename.package.json')

        name = 'tiny1nd-weird-no-rename-from-fless-pl.serial'
        outpath_pl = tmppath(name)
        refpath_pl = tdpath(name)

        Warn, buf = testwarn()
        c = SerialConverter(frictionlesspath, outpath_pl, out_format='pl.r')
        c.convert(warner=Warn)
        self.assertFileCorrect(outpath_pl, refpath_pl, ignore_lines=self.IGL)
        self.assertEqual(
            buf,
            [
                'Field b booleans Yes, y, No, n will not be understood by Polars.\n'
                'If they are present, you may need to set them to pl.String.\n'
                '(Use map_other_bools_to_string=True.)\n',
                'Field t date format %d/%m/%Y will not be understood by Polars read_csv.\n'
                'Will parse post-read using str.to_date.',
            ],
        )

    def testFrictionlessToSerialPolarsPython(self):
        frictionlesspath = tdpath('tiny1nd-weird-no-rename.resource.yaml')
        py_name = 'tiny1nd_weird_no_rename_from_fless_pl.py'
        outpath_py = tmppath(py_name)
        refpath_py = tdpath(py_name)

        Warn, buf = testwarn()
        c = SerialConverter(frictionlesspath, outpath_py, out_format='pl.r')
        c.convert(warner=Warn)
        self.assertFileCorrect(outpath_py, refpath_py, ignore_lines=self.IGL)
        self.assertEqual(len(buf), 2)  # booleans, date
        # ^^^ Code doesn't work because of booleans. But does warn.

    def testFrictionlessToSerialPolars2(self):
        frictionlesspath = tdpath('tiny1nd-weird-no-rename.package.json')
        name2 = 'tiny1nd-weird-no-rename-from-fless-pl2.serial'
        outpath_pl2 = tmppath(name2)
        refpath_pl2 = tdpath(name2)

        Warn, buf = testwarn()
        c = SerialConverter(
            frictionlesspath,
            outpath_pl2,
            out_format='pl.r',
            map_other_bools_to_string=True,
        )
        c.convert(warner=Warn)
        self.assertFileCorrect(outpath_pl2, refpath_pl2, ignore_lines=self.IGL)

        Warn, buf = testwarn()
        df = csv_to_polars(
            tdpath('tiny1nd-weird.ssv'), refpath_pl2, warner=Warn
        )
        ref_df = tiny_polars_df(
            nulls=True, sNullNull=True, euroStrDates=True, sBools=True
        )
        self.assertDataFramesEqual(df, ref_df, type_matching='strict')

    def atestFrictionlessToSerialPolarsWithRename(self):
        frictionlesspath = tdpath('tiny1nd-weird-package.json')

        name = 'tiny1nd-weird-from-fless-pl.serial'
        outpath_pl = tmppath(name)
        refpath_pl = tdpath(name)

        Warn, buf = testwarn()
        c = SerialConverter(frictionlesspath, outpath_pl, out_format='pl.r')
        c.convert(warner=Warn)
        self.assertFileCorrect(outpath_pl, refpath_pl, ignore_lines=self.IGL)
        self.assertEqual(
            buf,
            [
                'Polars will not understand the following boolean values:\n'
                ' Yes, n.\n'
                'If they actually occur in the file, fields will need to be set to string.\n'
                '(Use map_other_bools_to_string=True.)\n',
                'Field IAmDate date format %d/%m/%Y will not be understood by Polars read_csv.\n'
                'Will parse post-read using str.to_date.',
            ],
        )

    def atestFrictionlessToSerialPolarsWithRenamePython(self):
        frictionlesspath = tdpath('tiny1nd-weird-metadata.json')
        py_name = 'tiny1nd_weird_from_fless_pl.py'
        outpath_py = tmppath(py_name)
        refpath_py = tdpath(py_name)

        Warn, buf = testwarn()
        c = SerialConverter(frictionlesspath, outpath_py, out_format='pl.r')
        c.convert(warner=Warn)
        self.assertFileCorrect(outpath_py, refpath_py)
        self.assertEqual(len(buf), 2)  # booleans, date
        # ^^^ Code doesn't work because of booleans. But does warn.

    def atestFrictionlessToSerialPolarsWithRename2(self):
        frictionlesspath = tdpath('tiny1nd-weird-metadata.json')
        name2 = 'tiny1nd-weird-from-fless-pl2.serial'
        outpath_pl2 = tmppath(name2)
        refpath_pl2 = tdpath(name2)

        Warn, buf = testwarn()
        c = SerialConverter(
            frictionlesspath,
            outpath_pl2,
            out_format='pl.r',
            map_other_bools_to_string=True,
        )
        c.convert(warner=Warn)
        self.assertFileCorrect(outpath_pl2, refpath_pl2, ignore_lines=self.IGL)

        Warn, buf = testwarn()
        df = csv_to_polars(
            tdpath('tiny1nd-weird.ssv'), refpath_pl2, warner=Warn
        )
        ref_df = tiny_polars_df(
            nulls=True,
            sNullNull=True,
            euroStrDates=True,
            sBools=True,
            longNames=True,
        )
        self.assertDataFramesEqual(df, ref_df, type_matching='strict')

    def testConversionToFrictionlessObject(self):
        tiny1nd_serial = tdpath('tiny1nd.serial')
        md = load_metadata(self.tiny1nd_serial)
        frictionless = serial_to_frictionless(md)
        # Just check this hasn't broken anything serious
        # This isn't testing Frictionless!!!
        self.assertStringCorrect(
            frictionless.to_json(), tiny1nd_serial, ignore_lines=self.IGL
        )

    def testConversionToFrictionless_t1nds(self):
        tiny1nd_serial = tdpath('tiny1nd.serial')
        md = load_metadata(self.tiny1nd_serial)
        frictionless_md = serial_to_frictionless(md)
        frictionless_dict = frictionless_md.to_frictionless_dict('tiny1nd.csv')
        frictionless_json = json.dumps(frictionless_dict, indent=4)
        self.assertStringCorrect(
            frictionless_json,
            tdpath('tiny1nd.resource.json'),
            ignore_patterns=['(UTF-8|utf-8)'],
        )

    def testConversionToFrictionless_t1nds_file(self):
        tiny1nd_serial = tdpath('tiny1nd.serial')
        md = load_metadata(self.tiny1nd_serial)
        frictionless_md = serial_to_frictionless(md)
        outpath = tmppath('tiny1nd.package.json')
        frictionless_md.write_frictionless(outpath)
        self.assertFileCorrect(
            outpath, tdpath('tiny1nd.package.json'), ignore_lines=self.IGL
        )

    def testConversionToFrictionless_t1nds_file_cli(self):
        tiny1nd_serial = tdpath('tiny1nd.serial')
        outpath = tmppath('tiny1nd.resource.json')
        c = SerialConverter(cli_args=[tiny1nd_serial, outpath])
        c.convert()
        self.assertFileCorrect(
            outpath,
            tdpath('tiny1nd.resource.json'),
            ignore_patterns=['(UTF-8|utf-8)'],
        )

    def testSerialToFrictionlessFrictionlessJSONExtra(self):
        outpath = tmppath('tiny1nd-ref.package.json')
        refpath = tdpath('tiny1nd-ref.package.json')
        c = SerialConverter(
            self.tiny1nd_serial, outpath, for_csv='tiny1nd.csv'
        )
        Warn, buf = testwarn()
        c.convert(warner=Warn)
        self.assertFileCorrect(outpath, refpath)
        self.assertEqual(buf, [])

    def testSerialToFrictionlessFrictionlessYAMLExtra(self):
        outpath = tmppath('tiny1nd-ref.resource.yaml')
        refpath = tdpath('tiny1nd-ref.resource.yaml')
        c = SerialConverter(
            self.tiny1nd_serial, outpath, for_csv='tiny1nd.csv'
        )
        Warn, buf = testwarn()
        c.convert(warner=Warn)
        self.assertFileCorrect(outpath, refpath)
        self.assertEqual(buf, [])


class TestSerialUtilityFunction(ReferenceTestCase):
    def testTypeInference(self):
        self.assertEqual(
            analyse_values('b', ['True', 'false', 'TRUE']).most_likely_type,
            FieldType.BOOL,
        )
        self.assertEqual(
            analyse_values('t', ['1000', '-1', '0']).most_likely_type,
            FieldType.INT,
        )
        self.assertEqual(
            analyse_values(
                'f', ['1000', '-1', '0', '0.5', '2.1e3']
            ).most_likely_type,
            FieldType.FLOAT,
        )
        self.assertEqual(
            analyse_values('f', ['inf', 'nan', 'nan']).most_likely_type,
            FieldType.FLOAT,
        )  # !!!

        self.assertEqual(
            analyse_values(
                'd', ['2000.01.01', '31-12-2000', '12/31/2000', '999-999-999']
            ).most_likely_type,  # !!!
            FieldType.DATE,
        )

        self.assertEqual(
            analyse_values(
                'd',
                [
                    '2000.01.01',
                    '31-12-2000',
                    '12/31/2000',
                    '999-999-999',
                    '2000.jan.01',
                    '31-feb-2000',
                    'dec-31/2000',
                    'zzz-999-999',
                ],
            ).most_likely_type,  # !!!
            FieldType.DATE,
        )

        self.assertEqual(
            analyse_values(
                'd',
                [
                    '2000.01.01T12:34:56',
                    '31-12-2000 12:34:56+0100',
                    '999-999-999 99:99:99ksjdhfkZ',
                ],
            ).most_likely_type,
            FieldType.DATETIME,
        )

        self.assertEqual(
            analyse_values(
                'd',
                [
                    '20000.01.01T12:34:56',
                    '31-12-2000 12:34:56+0100',
                    '999-999-999 99:99:99ksjdhfkZ',
                ],
            ).most_likely_type,
            FieldType.DATETIME,
        )

        self.assertEqual(
            analyse_values(
                'b', ['true', 'false', 'false', '']
            ).most_likely_type,
            FieldType.BOOL,
        )

        self.assertEqual(
            analyse_values('b', ['Yes', 'n', '']).most_likely_type,
            FieldType.STRING,
        )

    def testCSVWNameInference(self):
        for sep, L in ((',', 'c'), ('\t', 't'), ('|', 'p'), (';', 's')):
            m = CSVWMetadata()
            m.delimiter = sep
            expected = f'a.{L}sv'
            self.assertEqual(m.choose_csv_from_csvw_name('a.json'), expected)
            self.assertEqual(
                m.choose_csv_from_csvw_name('/d/a.json'), expected
            )
            self.assertEqual(
                m.choose_csv_from_csvw_name('~/d/a.json'), expected
            )

            self.assertEqual(
                m.choose_csv_from_csvw_name('b-metadata.json'), f'b.{L}sv'
            )
            self.assertEqual(
                m.choose_csv_from_csvw_name('b.metadata.json'), f'b.{L}sv'
            )
            self.assertEqual(
                m.choose_csv_from_csvw_name('b-csvmetadata.json'), f'b.{L}sv'
            )
            self.assertEqual(
                m.choose_csv_from_csvw_name('b-csv-metadata.json'), f'b.{L}sv'
            )
            self.assertEqual(
                m.choose_csv_from_csvw_name('b.csv.metadata.json'), f'b.{L}sv'
            )
            self.assertEqual(
                m.choose_csv_from_csvw_name('b-csv.metadata.json'), f'b.{L}sv'
            )
            self.assertEqual(
                m.choose_csv_from_csvw_name('b-csv.metadata.json'), f'b.{L}sv'
            )
            self.assertEqual(
                m.choose_csv_from_csvw_name('b-psv.metadata.json'),
                f'b-psv.{L}sv',
            )

        m = CSVWMetadata()
        m.delimiter = '/'
        expected = f'a.txt'
        self.assertEqual(m.choose_csv_from_csvw_name('a.json'), expected)
        self.assertEqual(m.choose_csv_from_csvw_name('/d/a.json'), expected)
        self.assertEqual(m.choose_csv_from_csvw_name('~/d/a.json'), expected)

        self.assertEqual(
            m.choose_csv_from_csvw_name('b-metadata.json'), f'b.txt'
        )

    def testFrictionlessNameInference(self):
        for sep, L in ((',', 'c'), ('\t', 't'), ('|', 'p'), (';', 's')):
            m = FrictionlessMetadata()
            m.delimiter = sep
            expected = f'a.{L}sv'
            self.assertEqual(
                m.choose_csv_from_frictionless_name('a.json'), expected
            )
            self.assertEqual(
                m.choose_csv_from_frictionless_name('/d/a.json'), expected
            )
            self.assertEqual(
                m.choose_csv_from_frictionless_name('~/d/a.json'), expected
            )
            self.assertEqual(
                m.choose_csv_from_frictionless_name('b.package.json'),
                f'b.{L}sv',
            )
            self.assertEqual(
                m.choose_csv_from_frictionless_name('b.resource.json'),
                f'b.{L}sv',
            )
            self.assertEqual(
                m.choose_csv_from_frictionless_name('b.schema.json'),
                f'b.{L}sv',
            )
            self.assertEqual(
                m.choose_csv_from_frictionless_name('b-package.json'),
                f'b.{L}sv',
            )

        m = FrictionlessMetadata()
        m.delimiter = '/'
        expected = f'a.txt'
        self.assertEqual(
            m.choose_csv_from_frictionless_name('a.json'), expected
        )
        self.assertEqual(
            m.choose_csv_from_frictionless_name('/d/a.json'), expected
        )
        self.assertEqual(
            m.choose_csv_from_frictionless_name('~/d/a.json'), expected
        )

        self.assertEqual(
            m.choose_csv_from_frictionless_name('b.resource.json'), f'b.txt'
        )

    def testConversionSpecifcationCLI(self):
        # tests that the validator figures out what to do correctly
        # from command line args.

        expected = {
            ('a.csv', 'a.serial'): Spec(
                generate=True,
                formats=['tdda.serial'],
                broad_out='tdda.serial',
                inpath='a.csv',
                outpath='a.serial',
            )
        }

        for args, expected in expected.items():
            c = SerialConverter(cli_args=list(args))
            actual = Spec(
                c.generate, c.out_formats, c.broad_out, c.inpath, c.outpath
            )
            self.assertEqual((args, actual), (args, expected))


if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
