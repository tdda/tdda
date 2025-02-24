import datetime
import inspect
import json
import os
import re

import numpy as np
import pandas as pd

from tdda.referencetest import ReferenceTestCase, tag

from tdda.serial.base import RE_ISO8601
from tdda.serial.csvw import CSVWMetadata, csvw_date_format_to_md_date_format
from tdda.serial.pandasio import gen_pandas_kwargs
from tdda.serial.reader import (
    csv2pandas, poss_upgrade_to_int, load_metadata, to_pandas_read_csv_args
)


THISDIR = os.path.abspath(os.path.dirname(__file__))
TESTDATADIR = os.path.join(THISDIR, 'testdata')


def tdpath(path):
    return os.path.join(TESTDATADIR, path)


def dfEqual(self, df, exp):
    self.assertEqual(len(df), len(exp))
    self.assertEqual(list(df), list(exp))
    for col in df:
        self.assertEqual(
            ('values', col, np.sum(df[col] == exp[col]).item()),
            ('values', col, len(df)))
        self.assertEqual(
            ('types', col, str(df[col].dtype)),
            ('types', col, str(exp[col].dtype))
        )



class TestDateSanityRE(ReferenceTestCase):
    def testISO8601RE(self):
        self.assertIsNotNone(re.match(RE_ISO8601, '%Y-%m-%d'))

        self.assertIsNotNone(re.match(RE_ISO8601, '%Y-%m-%dT%H:%M:%S'))
        self.assertIsNotNone(re.match(RE_ISO8601, '%Y-%m-%d %H:%M:%S'))
        self.assertIsNotNone(re.match(RE_ISO8601, '%Y-%m-%dT%H:%M:%S.%f'))
        self.assertIsNotNone(re.match(RE_ISO8601, '%Y-%m-%d %H:%M:%S.%f'))

        self.assertIsNone(re.match(RE_ISO8601, '%Y-%M-%d'))
        self.assertIsNone(re.match(RE_ISO8601, 'yyyy-MM-dd'))

    def testDateFormatsMapping(self):
        map_date_format = csvw_date_format_to_md_date_format
        self.assertEqual(map_date_format('yyyy-MM-dd'), 'ISO8601')
        self.assertEqual(map_date_format('yyyyMMdd'), '%Y%m%d')
        self.assertEqual(map_date_format('dd-MM-yyyy'), '%d-%m-%Y')
        self.assertEqual(map_date_format('d-M-yyyy'), '%d-%m-%Y')
        self.assertEqual(map_date_format('MM-dd-yyyy'), '%m-%d-%Y')
        self.assertEqual(map_date_format('M-d-yyyy'), '%m-%d-%Y')
        self.assertEqual(map_date_format('dd/MM/yyyy'), '%d/%m/%Y')
        self.assertEqual(map_date_format('d/M/yyyy'), '%d/%m/%Y')
        self.assertEqual(map_date_format('MM/dd/yyyy'), '%m/%d/%Y')
        self.assertEqual(map_date_format('M/d/yyyy'), '%m/%d/%Y')
        self.assertEqual(map_date_format('dd.MM.yyyy'), '%d.%m.%Y')
        self.assertEqual(map_date_format('d.M.yyyy'), '%d.%m.%Y')
        self.assertEqual(map_date_format('MM.dd.yyyy'), '%m.%d.%Y')
        self.assertEqual(map_date_format('M.d.yyyy'), '%m.%d.%Y')

        self.assertEqual(map_date_format('yyyy-MM-ddTHH:mm:ss.S'), 'ISO8601')
        self.assertEqual(map_date_format('yyyy-MM-ddTHH:mm:ss'), 'ISO8601')
        self.assertEqual(map_date_format('yyyy-MM-ddTHH:mm'), '%Y-%m-%dT%H:%M')

        self.assertEqual(map_date_format('yyyy-MM-dd HH:mm:ss.S'), 'ISO8601')
        self.assertEqual(map_date_format('yyyy-MM-dd HH:mm:ss'), 'ISO8601')
        self.assertEqual(map_date_format('yyyy-MM-dd HH:mm'),
                                         '%Y-%m-%d %H:%M')

        self.assertEqual(map_date_format('dd-MM-yyyy HH:mm:ss.S'),
                                         '%d-%m-%Y %H:%M:%S.%f')
        self.assertEqual(map_date_format('MM-dd-yyyy HH:mm:ss'),
                                         '%m-%d-%Y %H:%M:%S')
        self.assertEqual(map_date_format('dd-MM-yy HH:mm'),
                                         '%d-%m-%y %H:%M')



class TestPandasKeywordArgsGeneration(ReferenceTestCase):
    def test_isodate(self):
        mdpath = os.path.join(TESTDATADIR, 'isod-metadata.json')
        self.assertEqual(gen_pandas_kwargs(mdpath), {
            'dtype': {'row': 'Int64'},
            'date_format': {'date': 'ISO8601'},
            'parse_dates': ['date'],
            'encoding': 'utf-8',
        })

    def test_simple(self):
        mdpath = os.path.join(TESTDATADIR, 'simple-metadata.json')
        self.assertEqual(gen_pandas_kwargs(mdpath), {
            'date_format': {'LastIn2024': 'ISO8601', 'LastInFeb': 'ISO8601'},
            'dtype': {
                'Even': 'boolean',
                'Index': 'Int64',
                'Name': 'string',
                'Odd': 'boolean',
                'Real': 'float'},
            'encoding': 'utf-8',
            'parse_dates': ['LastInFeb', 'LastIn2024']
        })

    def test_isodate_tsv(self):
        mdpath = os.path.join(TESTDATADIR, 'isodt-tsv-metadata.json')
        self.assertEqual(gen_pandas_kwargs(mdpath), {
            'dtype': {'row': 'Int64'},
            'date_format': {'time': 'ISO8601'},
            'parse_dates': ['time'],
            'sep': '\t',
            'encoding': 'utf-8',
        })

    def test_eurodate(self):
        mdpath = os.path.join(TESTDATADIR, 'eurod-metadata.json')
        self.assertEqual(gen_pandas_kwargs(mdpath), {
            'dtype': {'row': 'Int64'},
            'date_format': {'date': '%d/%m/%Y'},
            'parse_dates': ['date'],
            'encoding': 'utf-8',
        })



class TestConversion(ReferenceTestCase):
    dfEqual = dfEqual

    def test_isodate2pd(self):
        mdpath = os.path.join(TESTDATADIR, 'isod-metadata.json')
        csvpath = os.path.join(TESTDATADIR, 'isod.csv')

        df = pd.read_csv(csvpath, **gen_pandas_kwargs(mdpath))

        self.assertEqual(df.row.dtype, 'Int64')
        self.assertEqual(df.date.dtype, 'datetime64[ns]')

        expected = pd.DataFrame({
            'row': pd.Series([1, 15], dtype='Int64'),
            'date': [
                datetime.datetime(2024, 1, 1),
                datetime.datetime(2024, 1, 15)
            ]
        })
        self.dfEqual(df, expected)

    def test_simple2metadata(self):
        mdpath = os.path.join(TESTDATADIR, 'simple-metadata.json')
        md = CSVWMetadata(mdpath)
        self.assertStringCorrect(str(md), tdpath('expected/simple-md.json'),
                                 ignore_substrings=[
                                    'metadata_source_path',
                                    'metadata_source_dir'
                                 ])

    def test_simple2pd(self):
        mdpath = os.path.join(TESTDATADIR, 'simple-metadata.json')
        csvpath = os.path.join(TESTDATADIR, 'simple.csv')

        kw = gen_pandas_kwargs(mdpath)
        self.assertEqual(kw, {
            'date_format': {
                'LastIn2024': 'ISO8601',
                'LastInFeb': 'ISO8601'
            },
            'dtype': {
                 'Even': 'boolean',
                 'Index': 'Int64',
                 'Name': 'string',
                 'Odd': 'boolean',
                 'Real': 'float'
            },
            'encoding': 'utf-8',
            'parse_dates': [
                'LastInFeb',
                'LastIn2024'
            ]
        })
        df = pd.read_csv(csvpath, **kw)

        expected = pd.DataFrame({
            'Index': pd.Series([0, 1, 2], dtype='Int64'),
            'Odd': pd.Series([False, True, False], dtype='boolean'),
            'Even': pd.Series([True, False, True], dtype='boolean'),
            'Real': pd.Series([0.0, 1.125, 2.25], dtype='float64'),
            'Name': pd.Series(['zero', 'one', 'two'], dtype='string'),
            'LastInFeb': pd.Series([
                datetime.datetime(2024, 2, 20),
                datetime.datetime(2024, 2, 21),
                datetime.datetime(2024, 2, 22),
            ], dtype='datetime64[ns]'),
            'LastIn2024': pd.Series([
                datetime.datetime(2024, 2, 29, 23, 59, 50),
                datetime.datetime(2024, 2, 29, 23, 59, 51),
                datetime.datetime(2024, 2, 29, 23, 59, 52),
            ], dtype='datetime64[ns]'),
        })

        self.dfEqual(df, expected)

    def test_isodate_tsv2pd(self):
        mdpath = os.path.join(TESTDATADIR, 'isodt-tsv-metadata.json')
        csvpath = os.path.join(TESTDATADIR, 'isodt.tsv')

        df = pd.read_csv(csvpath, **gen_pandas_kwargs(mdpath))

        expected = pd.DataFrame({
            'row': pd.Series([1, 15], dtype='Int64'),
            'time': [
                datetime.datetime(2024, 1, 1, 11, 11, 11),
                datetime.datetime(2024, 1, 15, 22, 22, 22)
            ]
        })
        self.dfEqual(df, expected)

    def test_eurodate2pd(self):
        mdpath = os.path.join(TESTDATADIR, 'eurod-metadata.json')
        csvpath = os.path.join(TESTDATADIR, 'eurod.csv')
        kw = gen_pandas_kwargs(mdpath)
        df = pd.read_csv(csvpath, **gen_pandas_kwargs(mdpath))

        expected = pd.DataFrame({
            'row': pd.Series([1, 15], dtype='Int64'),
            'date': pd.Series([
                datetime.datetime(2024, 1, 1),
                datetime.datetime(2024, 1, 15)
            ], dtype='datetime64[ns]')
        })
        self.dfEqual(df, expected)


class TestPandasLoad(ReferenceTestCase):
    @classmethod
    def setUpClass(cls):

        # This is the dataframe that is read by pd.read_csv
        # with no kwargs
        cls.default_read_csv_df = pd.DataFrame({
            'i1': [1, 2, 3],
            'i2': [1.0, np.nan, 3.0],
            'i3': [-1.0, -2.0, np.nan],
            'f1': [1.5, np.nan, 3.5],
            'f2': [-1.5, -2.5, np.nan],
            'b1': [True, np.nan, True],
            'b2': [False, False, np.nan],
            's1': ['hello', np.nan, 'goodbye'],
            's2': ['àçéèïöô', 'aceeioo', np.nan],
            'dti': ['1999-12-31T23:59:59', np.nan, '2003-03-03T03:03:03'],
            'dte': ['31/12/1999 23:59:59', '02/02/2002 02:02:02', np.nan],
            'dtu': ['12/31/1999 11:59:59p', np.nan, '04/03/2005 03:02:01a'],
            'di': ['1999-12-31', '2002-01-02', np.nan],
            'de': ['31/12/1999', np.nan, '03/03/2003'],
            'du': ['12/31/1999', '01/02/2002', np.nan],
            # 'dtzi': ['1999-12-31T23:59:59+01:00', np.nan,
            #          '2003-03-03T03:02:01+01:00'],
            # 'dtze': [
            #     '31/12/1999 23:59:59+0100',
            #     '02/01/2002 03:02:01+0100',
            #     np.nan
            # ],
            # 'dtzu': [
            #     '12/31/1999 11:59:59p-0500',
            #     np.nan,
            #     '03/03/2003 05:04:03p-0800'
            # ],
        })

        fromiso = datetime.datetime.fromisoformat
        dt_m1 = datetime.datetime(1999, 12, 31, 23, 59, 59)
        d_m1 = datetime.date(1999, 12, 31)
        d_212= datetime.date(2002, 1, 2)
        d_543= datetime.date(2005, 4, 3)
        d_333= datetime.date(2003, 3, 3)
        dt_333333 = datetime.datetime(2003, 3, 3, 3, 3, 3)
        dt_222222 = datetime.datetime(2002, 2, 2, 2, 2, 2)
        dt_543_321 = datetime.datetime(2005, 4, 3, 3, 2, 1)
        dtz_m1_1 = fromiso('1999-12-31T23:59:59+01:00')
        dtz_333_321_1 = fromiso('2003-03-03T03:02:01+01:00')
        dtz_212_321_1 = fromiso('2002-01-02T03:02:01+01:00')
        dtz_m1_m5 = fromiso('1999-12-31T23:59:59-05:00')
        dtz_333_543_m8 = fromiso('2003-03-03T05:04:03-08:00')

        cls.correct_df = pd.DataFrame({
            'i1': pd.Series([1, 2, 3], dtype='Int64'),
            'i2': pd.Series([1, np.nan, 3], dtype='Int64'),
            'i3': pd.Series([-1, -2, np.nan], dtype='Int64'),
            'f1': pd.Series([1.5, np.nan, 3.5], dtype='float'),
            'f2': pd.Series([-1.5, -2.5, np.nan], dtype='float'),
            'b1': pd.Series([True, np.nan, True], dtype='boolean'),
            'b2': pd.Series([False, False, np.nan], dtype='boolean'),
            's1': pd.Series(['hello', pd.NA, 'goodbye'], dtype='string'),
            's2': pd.Series(['àçéèïöô', 'aceeioo', pd.NA], dtype='string'),
            'dti': pd.Series([dt_m1, pd.NaT, dt_333333],
                             dtype='datetime64[ns]'),
            'dte': pd.Series([dt_m1, dt_222222, pd.NaT],
                             dtype='datetime64[ns]'),
            'dtu': pd.Series([dt_m1, pd.NaT, dt_543_321],
                             dtype='datetime64[ns]'),
            'di': pd.Series([d_m1, d_212, pd.NaT], dtype='datetime64[ns]'),
            'de': pd.Series([d_m1, pd.NaT, d_333], dtype='datetime64[ns]'),
            'du': pd.Series([d_m1, d_212, pd.NaT], dtype='datetime64[ns]'),
            # 'dtzi': pd.Series([dtz_m1_1, pd.NaT, dtz_333_321_1],
            #                    dtype='datetime64[ns]'),
            # 'dtze': pd.Series([dtz_m1_1, dtz_212_321_1, pd.NaT],
            #                    dtype='datetime64[ns]'),
            # 'dtzu': pd.Series([dtz_m1_m5, pd.NaT, dtz_333_543_m8],
            #                   dtype='datetime64[ns]'),
        })

    def test_default_load_small(self):
        # Test loading of small.csv with pandas read_csv defaults
        # No date parsing so all date/datetime fields end up as strings
        csvpath = os.path.join(TESTDATADIR, 'small.csv')
        df = pd.read_csv(csvpath)
        self.assertDataFramesEqual(df, self.default_read_csv_df,
                                   type_matching='medium')

    def test_csvw_load_small(self):
        # Test loading of small.csv with correct CSVW associated
        # metadata. All types now come in correctly
        csvpath = os.path.join(TESTDATADIR, 'small.csv')
        mdpath = os.path.join(TESTDATADIR, 'small-metadata.json')
        df = csv2pandas(csvpath, mdpath)
        self.assertDataFramesEqual(df, self.correct_df)

    def test_load_latin1(self):
        # Read sig_latin1.csv correctly as iso-8859-1,
        # as specified in csvw metadata file
        mdpath = os.path.join(TESTDATADIR, 'sig-latin1-metadata.json')
        df = csv2pandas(mdpath=mdpath)
        refpath = os.path.join(TESTDATADIR, 'sig-latin1.parquet')
        rf = pd.read_parquet(refpath)
        self.assertDataFramesEqual(df, rf, type_matching='medium')

        # This is correct decoding from latin-1 (checked above)
        self.assertEqual(df.sig[0], '¤¦¨¼½¾')

        df = csv2pandas(mdpath=mdpath, encoding='iso-8859-15')

        # Check read *incorrectly* when latin9 specified
        self.assertNotEqual(df.sig[0], '¤¦¨¼½¾')

        # More specifically, check that it is read as latin9 (iso-8859-15)
        self.assertEqual(df.sig[0], '€ŠšŒœŸ')

    def test_load_latin9(self):
        # Read sig_latin9.csv correctly as iso-8859-15,
        # as specified in csvw metadata file
        mdpath = os.path.join(TESTDATADIR, 'sig-latin9-metadata.json')
        df = csv2pandas(mdpath=mdpath)
        refpath = os.path.join(TESTDATADIR, 'sig-latin9.parquet')
        rf = pd.read_parquet(refpath)
        self.assertDataFramesEqual(df, rf, type_matching='medium')

    def test_load_cp1252(self):
        # Read sig_cp1252.csv correctly as cp1252
        # as specified in csvw metadata file
        mdpath = os.path.join(TESTDATADIR, 'sig-cp1252-metadata.json')
        df = csv2pandas(mdpath=mdpath)
        refpath = os.path.join(TESTDATADIR, 'sig-cp1252.parquet')
        rf = pd.read_parquet(refpath)
        self.assertDataFramesEqual(df, rf, type_matching='medium')

    def test_load_utf16(self):
        # Read sig_utf16.csv correctly as utf-16.
        # This includes all the characters that differ among
        # latin1 (iso-8859-1), latin9 (iso-8859-15), and cp1252.
        mdpath = os.path.join(TESTDATADIR, 'sig-equiv-utf16-metadata.json')
        df = csv2pandas(mdpath=mdpath)
        refpath = os.path.join(TESTDATADIR, 'sig-equiv-utf16.parquet')
        rf = pd.read_parquet(refpath)
        self.assertDataFramesEqual(df, rf, type_matching='medium')

    def test_load_utf8(self):
        # Read sig_utf16.csv correctly as utf-8.
        # This includes all the characters that differ among
        # latin1 (iso-8859-1), latin9 (iso-8859-15), and cp1252.
        mdpath = os.path.join(TESTDATADIR, 'sig-equiv-utf8-metadata.json')
        df = csv2pandas(mdpath=mdpath)
        refpath = os.path.join(TESTDATADIR, 'sig-equiv-utf8.parquet')
        rf = pd.read_parquet(refpath)
        self.assertDataFramesEqual(df, rf, type_matching='medium')

    def test_default_load_all_csvw_types(self):
        # Test loading of all_csvw_types.csv with pandas read_csv defaults
        # This contains a column for each valid CSVW type
        # Those that csvmetadata fully supports should be loaded
        # correctly, with others loading as strings.
        #
        mdpath = os.path.join(TESTDATADIR, 'all-csvw-types-metadata.json')
        df = csv2pandas(mdpath=mdpath)
        refpath = os.path.join(TESTDATADIR, 'all-csvw-types.parquet')
        rf = pd.read_parquet(refpath, dtype_backend='numpy_nullable')

        self.assertDataFramesEqual(df, rf, type_matching='medium')


        # Belt and braces
        # This can't fail unless assertDataFramesEqual is broken
        # or something even worse has occurred
        for c in df:
            df[c].isnull == pd.Series([False, True, False])
            rf[c].isnull == pd.Series([False, True, False])

    def test_csvw_load_small2(self):
        # Test loading of small.csv with correct CSVW associated
        # metadata. All types now come in correctly
        # Here we have
        #   - used | as separator (specified with delimiter in dialect
        #   - double quoted all values
        #   - used NULL as the null marker
        #
        mdpath = os.path.join(TESTDATADIR, 'small2-metadata.json')
        df = csv2pandas(mdpath=mdpath)
        self.assertDataFramesEqual(df, self.correct_df)

    def test_load_nulls1(self):
        mdpath = os.path.join(TESTDATADIR, 'nulls1-metadata.json')
        refpath = os.path.join(TESTDATADIR, 'nulls1.parquet')
        df = csv2pandas(mdpath=mdpath)
        rf = pd.read_parquet(refpath)
        self.assertDataFramesEqual(df, rf)


#@tag
class TestCSVWTests(ReferenceTestCase):
    csvw_d = os.path.join(os.path.dirname(__file__), 'testdata/csvw')
    parquet_d = os.path.join(os.path.dirname(__file__),
                             'testdata/csvw-parquet')

    def fullpath(self, path):
        return os.path.normpath(os.path.join(self.csvw_d, path))

    def parquet_path(self, path):
        """
        Full path to parquet result for CSVW tests
        """
        return os.path.normpath(os.path.join(self.parquet_d, path))

    def csv_json_paths(self, stem):
        return (
            os.path.join(self.csvw_d, stem + '.csv'),
            os.path.join(self.csvw_d, stem + '.json')
        )

    def test001(self):
        self._test_csv_json('test001')

    def test002(self):
        pass

    def test003(self):
        pass

    def test004(self):
        pass

    def test005(self):

        # csvw expects the IDs to be read as strings
        # But pandas reads id as int and child_id as float,
        # because it has nulls

        # Clearly pandas behaviour is better, and there is not CSVW
        # involved. But we might like csv2pandas to coerce types

        # By using upgrade_possible_ints, we get int64 for id
        # (with no nulls) and Int64 for child_id.

        # And by forcing the string fields in ref_df to ints,
        # we match that.

        # So this test is _radically_ diffferent from the corresponding
        # CSVW test. But useful.

        self._test_csv_json('test005', upgrade_possible_ints=True,
                            to_ints=['id', 'child_id'])

    def test006(self):
        self._test_csv_json('test006')

    def test007(self):
        self._test_csv_json('test007')

    def test008(self):
        self._test_csv_json('test008', to_ints=['Book1', 'Book2'])

    def test009(self):
        self._test_csv_json('test009', to_ints=['GID'])

    def test010(self):
        self._test_csv_json('test010')

    def test011(self):
        test = this_function_name()  # function name
        csvpath = self.fullpath(f'{test}/tree-ops.csv')
        resultspath = self.fullpath(f'{test}/result.json')
        df = csv2pandas(csvpath, findmd=True)
        string_to_int(df, 'GID')
        fields = ['GID', 'on_street', 'species', 'trim_cycle',
                  'inventory_date']
        ref_df = csvw_json_to_df(resultspath, fields, to_ints=['GID'])

        # The string dates are a problem because the date and month
        # are not zero-padded.
        # Just correct here:
        ref_df['inventory_date'] = pd.Series([datetime.date(2010, 10, 18),
                                              datetime.date(2010, 6, 2)],
                                              dtype='datetime64[ns]')

        # medium because of object/string comparisons
        self.assertDataFramesEqual(df, ref_df, type_matching='medium')

    def test012(self):
        test = this_function_name()  # function name
        mdpath = self.fullpath(f'{test}/csv-metadata.json')
        resultspath = self.fullpath(f'{test}/result.json')


        df, md = csv2pandas(mdpath=mdpath, return_md=True)
        string_to_int(df, 'GID')
        csvpath = self.fullpath('test012/tree-ops.csv')
        fields = ['GID', 'on_street', 'species', 'trim_cycle',
                  'inventory_date']

        ref_df = csvw_json_to_df(resultspath, fields, to_ints=['GID'])


        # The string dates are a problem because the date and month
        # are not zero-padded.
        # Just correct here:
        ref_df['inventory_date'] = pd.Series([datetime.date(2010, 10, 18),
                                              datetime.date(2010, 6, 2)],
                                              dtype='datetime64[ns]')
        # medium because of object/string comparisons
        self.assertDataFramesEqual(df, ref_df, type_matching='medium')

    def test013(self):
        test = this_function_name()  # function name
        mdpath = self.fullpath(f'{test}-user-metadata.json')
        resultspath = self.fullpath(f'{test}.json')

        df, md = csv2pandas(mdpath=mdpath, return_md=True)
        string_to_int(df, 'GID')
        csvpath = self.fullpath('tree-ops.csv')
        fields = ['GID', 'on_street', 'species', 'trim_cycle',
                  'inventory_date']

        ref_df = csvw_json_to_df(resultspath, fields, to_ints=['GID'])

        # The string dates are a problem because the date and month
        # are not zero-padded.
        # Just correct here:
        ref_df['inventory_date'] =  pd.Series([datetime.date(2010, 10, 18),
                                               datetime.date(2010, 6, 2)],
                                               dtype='datetime64[ns]')
        # medium because of object/string comparisons
        self.assertDataFramesEqual(df, ref_df, type_matching='medium')

    def test014(self):
        test = this_function_name()  # function name
        mdpath = self.fullpath(f'{test}/linked-metadata.json')
        resultspath = self.fullpath(f'{test}/result.json')

        df, md = csv2pandas(mdpath=mdpath, return_md=True)
        string_to_int(df, 'GID')
        csvpath = self.fullpath(f'{test}/tree-ops.csv')
        fields = ['GID', 'on_street', 'species', 'trim_cycle',
                  'inventory_date']

        ref_df = csvw_json_to_df(resultspath, fields, to_ints=['GID'])


        # The string dates are a problem because the date and month
        # are not zero-padded.
        # Just correct here:
        ref_df['inventory_date'] = pd.Series([datetime.date(2010, 10, 18),
                                              datetime.date(2010, 6, 2)],
                                              dtype='datetime64[ns]')
        # medium because of object/string comparisons
        self.assertDataFramesEqual(df, ref_df, type_matching='medium')

    def test015(self):
        test = this_function_name()  # function name
        mdpath = self.fullpath(f'{test}/csv-metadata.json')
        resultspath = self.fullpath(f'{test}/result.json')

        df, md = csv2pandas(mdpath=mdpath, return_md=True)
        string_to_int(df, 'GID')
        csvpath = self.fullpath(f'{test}/tree-ops.csv')
        fields = ['GID', 'on_street', 'species', 'trim_cycle',
                  'inventory_date']

        ref_df = csvw_json_to_df(resultspath, fields, to_ints=['GID'])


        # The string dates are a problem because the date and month
        # are not zero-padded.
        # Just correct here:
        ref_df['inventory_date'] = pd.Series([datetime.date(2010, 10, 18),
                                              datetime.date(2010, 6, 2)],
                                              dtype='datetime64[ns]')
        # medium because of object/string comparisons
        self.assertDataFramesEqual(df, ref_df, type_matching='medium')

    def test016(self):
        test = this_function_name()  # function name
        mdpath = self.fullpath(f'{test}/csv-metadata.json')
        resultspath = self.fullpath(f'{test}/result.json')

        df, md = csv2pandas(mdpath=mdpath, return_md=True)
        string_to_int(df, 'GID')
        csvpath = self.fullpath(f'{test}/tree-ops.csv')
        fields = ['GID', 'on_street', 'species', 'trim_cycle',
                  'inventory_date']

        ref_df = csvw_json_to_df(resultspath, fields, to_ints=['GID'])


        # The string dates are a problem because the date and month
        # are not zero-padded.
        # Just correct here:
        ref_df['inventory_date'] = pd.Series([datetime.date(2010, 10, 18),
                                              datetime.date(2010, 6, 2)],
                                              dtype='datetime64[ns]')
        # medium because of object/string comparisons
        self.assertDataFramesEqual(df, ref_df, type_matching='medium')

    def test017(self):
        test = this_function_name()  # function name
        mdpath = self.fullpath(f'{test}/csv-metadata.json')
        resultspath = self.fullpath(f'{test}/result.json')

        df, md = csv2pandas(mdpath=mdpath, return_md=True)
        string_to_int(df, 'GID')
        csvpath = self.fullpath(f'{test}/tree-ops.csv')
        fields = ['GID', 'on_street', 'species', 'trim_cycle',
                  'inventory_date']

        ref_df = csvw_json_to_df(resultspath, fields, to_ints=['GID'])


        # The string dates are a problem because the date and month
        # are not zero-padded.
        # Just correct here:
        ref_df['inventory_date'] = pd.Series([datetime.date(2010, 10, 18),
                                              datetime.date(2010, 6, 2)],
                                              dtype='datetime64[ns]')
        # medium because of object/string comparisons
        self.assertDataFramesEqual(df, ref_df, type_matching='medium')

    def test018(self):
        test = this_function_name()  # function name
        mdpath = self.fullpath(f'{test}/tree-ops.csv-metadata.json')
        resultspath = self.fullpath(f'{test}/result.json')

        df, md = csv2pandas(mdpath=mdpath, return_md=True)
        string_to_int(df, 'GID')
        csvpath = self.fullpath(f'{test}/tree-ops.csv')
        fields = ['GID', 'on_street', 'species', 'trim_cycle',
                  'inventory_date']

        ref_df = csvw_json_to_df(resultspath, fields, to_ints=['GID'])


        # The string dates are a problem because the date and month
        # are not zero-padded.
        # Just correct here:
        ref_df['inventory_date'] = pd.Series([datetime.date(2010, 10, 18),
                                              datetime.date(2010, 6, 2)],
                                              dtype='datetime64[ns]')
        # medium because of object/string comparisons
        self.assertDataFramesEqual(df, ref_df, type_matching='medium')

    def test019(self):
        pass

    def test020(self):
        pass

    def test021(self):
        pass

    def test022(self):
        pass

    def test023(self):
        test = this_function_name()
        mdpath = self.fullpath(f'{test}-user-metadata.json')
        resultspath = self.fullpath(f'{test}.json')

        df = csv2pandas(mdpath=mdpath)
        self.assertEqual(list(df), [0, 1, 2, 3, 4])
        # This is what Pandas does:  ^^^
        # CSVW wants _col.1 to _col.5 apparently.

        fields = df.columns = [f'_col.{i + 1}' for i in range(len(df.columns))]
        ref_df = csvw_json_to_df(resultspath, fields)

        # medium because of object/string comparisons
        self.assertDataFramesEqual(df, ref_df, type_matching='medium')

    def test024(self):
        pass

    def test025(self):
        pass

    def test026(self):
        pass


    def test027(self):
        test = this_function_name()
        mdpath = self.fullpath(f'{test}-user-metadata.json')
        resultspath = self.fullpath(f'{test}.json')

        df = csv2pandas(mdpath=mdpath)
        fields = ['GID', 'on_street', 'species', 'trim_cycle',
                  'inventory_date']
        ref_df = csvw_bare_json_to_df(resultspath, fields)

        # medium because of object/string comparisons
        self.assertDataFramesEqual(df, ref_df, type_matching='medium')

    def test028(self):
        test = this_function_name()
        csvpath = self.fullpath(f'countries.csv')
        resultspath = self.fullpath(f'{test}.json')

        df = csv2pandas(csvpath)
        fields = fields_from(csvpath)
        ref_df = csvw_json_to_df(resultspath, fields)
        string_to_float(ref_df, 'latitude')
        string_to_float(ref_df, 'longitude')

        # medium because of object/string comparisons
        self.assertDataFramesEqual(df, ref_df)

    def test029(self):
        test = this_function_name()
        csvpath = self.fullpath(f'countries.csv')
        resultspath = self.fullpath(f'{test}.json')

        df = csv2pandas(csvpath)
        fields = fields_from(csvpath)
        ref_df = csvw_bare_json_to_df(resultspath, fields)
        string_to_float(ref_df, 'latitude')
        string_to_float(ref_df, 'longitude')

        # medium because of object/string comparisons
        self.assertDataFramesEqual(df, ref_df)

    def test030(self):
        test = this_function_name()
        csvpath = self.fullpath(f'countries.csv')
        mdpath = self.fullpath(f'countries.json')
        resultspath = self.fullpath(f'{test}.json')  # contains two tables

        df = csv2pandas(csvpath, mdpath, table_number=0)
        fields = fields_from(csvpath)
        ref_fields = [
            'http://www.geonames.org/ontology#countryCode',
            "schema:latitude",
            "schema:longitude",
            "schema:name",
        ]

        ref_df = csvw_json_to_df(resultspath, ref_fields, table_number=0)
        ref_df.columns = fields
        string_to_float(ref_df, 'latitude')
        string_to_float(ref_df, 'longitude')
        self.assertDataFramesEqual(df, ref_df, type_matching='medium')

        slice_csvpath = self.fullpath(f'country_slice.csv')
        df2 = csv2pandas(slice_csvpath, mdpath, table_number=1)
        slice_fields = fields_from(slice_csvpath)
        ref_df2 = csvw_json_to_df(resultspath, slice_fields, table_number=1)
        ref_df2['countryRef'] = (
            ref_df2['countryRef'].apply(lambda s: s.split('#')[-1])
        )
        self.assertDataFramesEqual(df2, ref_df2, type_matching='medium')

    def test031(self):
        # single json output with different kinds of records
        # not really appropriate for what tdda.serial is trying to do
        pass

    def test032(self):
        test = this_function_name()
        csvpath = self.fullpath(f'{test}/events-listing.csv')
        resultspath = self.parquet_path(f'{test}-result.parquet')
        mdpath = self.fullpath(f'{test}/csv-metadata.json')

        df, md = csv2pandas(csvpath, mdpath, return_md=True, verbosity=1)
        self.assertEqual(len(md.warnings), 5)  # 5 virtual fields

        # Compare against known correct result (not from csvw project)
        self.assertDataFrameCorrect(df, resultspath)

    def test033(self):
        pass  # same as 32 for our purposes

    def test034(self):
        test = this_function_name()
        f = self.fullpath
        pqp = self.parquet_path
        mdpath = f(f'{test}/csv-metadata.json')
        sdf, md = csv2pandas(
            f(f'{test}/senior-roles.csv'),
            mdpath,
            use_table_name=True,
            upgrade_possible_ints=True,
            return_md=True,
            verbosity=1,
        )
        self.assertDataFrameCorrect(sdf, pqp(f'{test}-senior-roles.parquet'))
        jdf = csv2pandas(
            f(f'{test}/junior-roles.csv'),
            mdpath,
            use_table_name=True,
            upgrade_possible_ints=True,
            verbosity=1,
        )
        self.assertDataFrameCorrect(jdf, pqp(f'{test}-junior-roles.parquet'))

        pdf = csv2pandas(
            f(f'{test}/gov.uk/data/professions.csv'),
            mdpath,
            use_table_name=True,
            upgrade_possible_ints=True,
            verbosity=1,
        )
        self.assertDataFrameCorrect(jdf, pqp(f'{test}-professions.parquet'))

        odf = csv2pandas(
            f(f'{test}/gov.uk/data/organizations.csv'),
            mdpath,
            use_table_name=True,
            upgrade_possible_ints=True,
            verbosity=1,
        )
        self.assertDataFrameCorrect(jdf, pqp(f'{test}-organizations.parquet'))

    def test035(self):
        pass  # same as 34 for our purposes

    def test036(self):
        test = this_function_name()
        csvpath = self.fullpath(f'{test}/tree-ops-ext.csv')
        resultspath = self.parquet_path(f'{test}-result.parquet')
        md = load_metadata(self.fullpath(f'{test}/tree-ops-ext.csv-metadata.json'))
        df = csv2pandas(csvpath, findmd=True)
        self.assertDataFrameCorrect(df, resultspath)



    def _test_csv_json(self, stem, upgrade_possible_ints=False,
                       to_ints=None):
        csvpath, resultspath = self.csv_json_paths(stem)
        df = csv2pandas(csvpath, upgrade_possible_ints=upgrade_possible_ints)
        fields = fields_from(csvpath)
        ref_df = csvw_json_to_df(resultspath, fields, to_ints=to_ints)
        #elf.assertDataFramesEqual(df, ref_df)


def csvw_json_to_df(path, fields, table_number=0, to_ints=None):
    with open(path) as f:
        d = json.load(f)
    rows = d['tables'][table_number]['row']
    df = pd.DataFrame({
            field: [r['describes'][0].get(field, None) for r in rows]
            for field in fields
    })
    for k in (to_ints or []):
        string_to_int(df, k)
    return df


def csvw_bare_json_to_df(path, fields, to_ints=None):
    with open(path) as f:
        d = json.load(f)
    rows = d
    df = pd.DataFrame({
            field: [r.get(field, None) for r in rows]
            for field in fields
    })
    for k in (to_ints or []):
        string_to_int(df, k)
    return df


def string_to_int(df, k):
    if sum(df[k].isnull()) > 0:
        df[k] = df[k].astype(pd.Int64Dtype())
    else:
        df[k] = df[k].astype('int')


def string_to_float(df, k):
    df[k] = df[k].astype('float')


def fields_from(csvpath):
    with open(csvpath) as f:
        return f.readline().strip().split(',')


def this_function_name():
    """
    Returns the name of the function (or method) from which this was called
    """
    return inspect.stack()[1][3]


if __name__ == '__main__':
    ReferenceTestCase.main()
