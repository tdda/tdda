import datetime
import os
import re

import numpy as np
import pandas as pd

from tdda.referencetest import ReferenceTestCase, tag

from tdda.serial.base import RE_ISO8601
from tdda.serial.csvw import CSVWMetadata, csvw_date_format_to_md_date_format
from tdda.serial.pandasio import gen_pandas_kwargs
from tdda.serial.reader import csv2pandas


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



if __name__ == '__main__':
    ReferenceTestCase.main()
