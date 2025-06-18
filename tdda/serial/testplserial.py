import datetime
import inspect
import json
import os

import polars as pl

from tdda.referencetest import ReferenceTestCase, tag

# from tdda.referencetest.checkpandas import diff_dataframes as pd_diff

from tdda.serial.base import FieldType
from tdda.serial.csvw import CSVWMetadata
from tdda.serial.polarsio import (
    csv_to_polars,
    tddaserial_to_polars_read_csv_args,
#    polars_df_to_csv,
#    polars_df_to_metadata,
#    polars_dtype_to_fieldtype,
)
from tdda.serial.reader import (
    load_metadata,
)

from rich import print as rprint

# from tdda.serial.simple import (
#     polars_read_csv,
#     polars_write_csv,
#     metadata_path
# )

# from tdda.referencetest.checkpolars import (
#     diff_dataframes
# )

from tdda.serial.examples.plgen import (
    generate_reference_base_polars_dataframe
)


from tdda.serial.testserial import (
    TESTDATADIR,

    THREE_FLAVOURS,
    TDDASERIAL_PATTERNS,
#    PANDAS2,

    tdpath,
    epath,
    tmppath,

    tiny_python_values,
)


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


def testwarn():
    buf = []
    f = lambda *args, **kw: buf.extend(args)
    return f, buf


class TestPolarsKeywordArgsGeneration(ReferenceTestCase):
    def test_base_tddaserial(self):
        md = load_metadata(epath('base-csv.serial'))
        warn, buf = testwarn()
        kw = tddaserial_to_polars_read_csv_args(md, warner=warn,
                                                serializable=True)
        self.assertStringCorrect(json.dumps(kw, indent=4),
                                 tdpath('base-csv-pl-from-serial.json'))
        self.assertEqual(buf, [
            'Polars does not understand escape characters.\n'
            'Ignoring escape value: \\'
        ])

    def test_base_polars_tddaserial(self):
        md = load_metadata(epath('base-csv-polars.serial'))
        warn, buf = testwarn()
        kw = tddaserial_to_polars_read_csv_args(md, warner=warn,
                                                serializable=True)
        self.assertStringCorrect(json.dumps(kw, indent=4),
                                 tdpath('base-csv-pl-from-serial2.json'))
        self.assertEqual(buf, [])

    def test_simple(self):
        md = load_metadata(tdpath('simple-metadata.json'))
        warn, buf = testwarn()
        kw = tddaserial_to_polars_read_csv_args(md, warner=warn,
                                                serializable=True)
        self.assertStringCorrect(json.dumps(kw, indent=4),
                                 tdpath('simple-csv-pl-from-csvw.json'))
        self.assertEqual(buf, [])

    def test_isodate_tsv(self):
        md = load_metadata(tdpath('isodt-tsv-metadata.json'))
        warn,  buf = testwarn()
        kw = tddaserial_to_polars_read_csv_args(md, warner=warn,
                                                serializable=True)
        self.assertStringCorrect(json.dumps(kw, indent=4),
                                 tdpath('isodate-tsv-pl-from-csvw.json'))
        self.assertEqual(buf, [])


# class TestConversion(ReferenceTestCase):
#     dfEqual = dfEqual

#     def test_isodate2pd(self):
#         mdpath = tdpath('isod-metadata.json')
#         csvpath = tdpath('isod.csv')

#         df = pd.read_csv(csvpath, **csvw_to_polars_kwargs(mdpath))

#         self.assertEqual(df.row.dtype, 'Int64')
#         self.assertEqual(df.date.dtype, 'datetime64[ns]')

#         expected = pd.DataFrame({
#             'row': pd.Series([1, 15], dtype='Int64'),
#             'date': [
#                 datetime.datetime(2024, 1, 1),
#                 datetime.datetime(2024, 1, 15)
#             ]
#         })
#         self.dfEqual(df, expected)

#     def test_simple2metadata(self):
#         mdpath = tdpath('simple-metadata.json')
#         md = CSVWMetadata(mdpath)
#         self.assertStringCorrect(str(md), tdpath('expected/simple-md.json'),
#                                  ignore_substrings=[
#                                     'metadata_source_path',
#                                     'metadata_source_dir'
#                                  ],
#                                  ignore_patterns=TDDASERIAL_PATTERNS)

#     def test_simple2pd(self):
#         mdpath = tdpath('simple-metadata.json')
#         csvpath = tdpath('simple.csv')

#         kw = csvw_to_polars_kwargs(mdpath)
#         self.assertEqual(kw, {
#             'date_format': {
#                 'LastIn2024': 'ISO8601',
#                 'LastInFeb': 'ISO8601'
#             },
#             'dtype': {
#                  'Even': 'boolean',
#                  'Index': 'Int64',
#                  'Name': 'string',
#                  'Odd': 'boolean',
#                  'Real': 'float'
#             },
#             'encoding': 'utf-8',
#             'parse_dates': [
#                 'LastInFeb',
#                 'LastIn2024'
#             ]
#         })
#         df = pd.read_csv(csvpath, **kw)

#         expected = pd.DataFrame({
#             'Index': pd.Series([0, 1, 2], dtype='Int64'),
#             'Odd': pd.Series([False, True, False], dtype='boolean'),
#             'Even': pd.Series([True, False, True], dtype='boolean'),
#             'Real': pd.Series([0.0, 1.125, 2.25], dtype='float64'),
#             'Name': pd.Series(['zero', 'one', 'two'], dtype='string'),
#             'LastInFeb': pd.Series([
#                 datetime.datetime(2024, 2, 20),
#                 datetime.datetime(2024, 2, 21),
#                 datetime.datetime(2024, 2, 22),
#             ], dtype='datetime64[ns]'),
#             'LastIn2024': pd.Series([
#                 datetime.datetime(2024, 2, 29, 23, 59, 50),
#                 datetime.datetime(2024, 2, 29, 23, 59, 51),
#                 datetime.datetime(2024, 2, 29, 23, 59, 52),
#             ], dtype='datetime64[ns]'),
#         })

#         self.dfEqual(df, expected)

#     def test_isodate_tsv2pd(self):
#         mdpath = tdpath('isodt-tsv-metadata.json')
#         csvpath = tdpath('isodt.tsv')

#         df = pd.read_csv(csvpath, **csvw_to_polars_kwargs(mdpath))

#         expected = pd.DataFrame({
#             'row': pd.Series([1, 15], dtype='Int64'),
#             'time': [
#                 datetime.datetime(2024, 1, 1, 11, 11, 11),
#                 datetime.datetime(2024, 1, 15, 22, 22, 22)
#             ]
#         })
#         self.dfEqual(df, expected)

#     def test_eurodate2pd(self):
#         mdpath = tdpath('eurod-metadata.json')
#         csvpath = tdpath('eurod.csv')
#         # kw = csvw_to_polars_kwargs(mdpath)
#         df = pd.read_csv(csvpath, **csvw_to_polars_kwargs(mdpath))

#         expected = pd.DataFrame({
#             'row': pd.Series([1, 15], dtype='Int64'),
#             'date': pd.Series([
#                 datetime.datetime(2024, 1, 1),
#                 datetime.datetime(2024, 1, 15)
#             ], dtype='datetime64[ns]')
#         })
#         self.dfEqual(df, expected)


class TestPolarsLoad(ReferenceTestCase):
    @classmethod
    def setUpClass(cls):

        # This is the dataframe that is read by pl.read_csv
        # with no kwargs
        cls.default_read_csv_df = pl.DataFrame({
            'i1': [1, 2, 3],
            'i2': [1.0, None, 3.0],
            'i3': [-1.0, -2.0, None],
            'f1': [1.5, None, 3.5],
            'f2': [-1.5, -2.5, None],
            'b1': [True, None, True],
            'b2': [False, False, None],
            's1': ['hello', None, 'goodbye'],
            's2': ['àçéèïöô', 'aceeioo', None],
            'dti': ['1999-12-31T23:59:59', None, '2003-03-03T03:03:03'],
            'dte': ['31/12/1999 23:59:59', '02/02/2002 02:02:02', None],
            'dtu': ['12/31/1999 11:59:59p', None, '04/03/2005 03:02:01a'],
            'di': ['1999-12-31', '2002-01-02', None],
            'de': ['31/12/1999', None, '03/03/2003'],
            'du': ['12/31/1999', '01/02/2002', None],
            # 'dtzi': ['1999-12-31T23:59:59+01:00', None,
            #          '2003-03-03T03:02:01+01:00'],
            # 'dtze': [
            #     '31/12/1999 23:59:59+0100',
            #     '02/01/2002 03:02:01+0100',
            #     None
            # ],
            # 'dtzu': [
            #     '12/31/1999 11:59:59p-0500',
            #     None,
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

        cls.correct_df = pl.DataFrame((
            pl.Series('i1', [1, 2, 3], dtype=pl.Int64),
            pl.Series('i2', [1, None, 3], dtype=pl.Int64),
            pl.Series('i3', [-1, -2, None], dtype=pl.Int64),
            pl.Series('f1', [1.5, None, 3.5], dtype=pl.Float64),
            pl.Series('f2', [-1.5, -2.5, None], dtype=pl.Float64),
            pl.Series('b1', [True, None, True], dtype=pl.Boolean),
            pl.Series('b2', [False, False, None], dtype=pl.Boolean),
            pl.Series('s1', ['hello', None, 'goodbye'], dtype=pl.String),
            pl.Series('s2', ['àçéèïöô', 'aceeioo', None], dtype=pl.String),
            pl.Series('dti', [dt_m1, None, dt_333333], dtype=pl.Datetime),
            pl.Series('dte', [dt_m1, dt_222222, None], dtype=pl.Datetime),
            pl.Series('dtu', [dt_m1, None, dt_543_321], dtype=pl.Datetime),
            pl.Series('di', [d_m1, d_212, None], dtype=pl.Datetime),
            pl.Series('de', [d_m1, None, d_333], dtype=pl.Datetime),
            pl.Series('du', [d_m1, d_212, None], dtype=pl.Datetime),
            # 'dtzi': pd.Series([dtz_m1_1, pd.NaT, dtz_333_321_1],
            #                    dtype='datetime64[ns]'),
            # 'dtze': pd.Series([dtz_m1_1, dtz_212_321_1, pd.NaT],
            #                    dtype='datetime64[ns]'),
            # 'dtzu': pd.Series([dtz_m1_m5, pd.NaT, dtz_333_543_m8],
            #                   dtype='datetime64[ns]'),
        ))

        cls.dfisodates = pl.DataFrame((
            pl.Series('i1', [1, 2, 3], dtype=pl.Int64),
            pl.Series('i2', [1, None, 3], dtype=pl.Int64),
            pl.Series('i3', [-1, -2, None], dtype=pl.Int64),
            pl.Series('f1', [1.5, None, 3.5], dtype=pl.Float64),
            pl.Series('f2', [-1.5, -2.5, None], dtype=pl.Float64),
            pl.Series('b1', [True, None, True], dtype=pl.Boolean),
            pl.Series('b2', [False, False, None], dtype=pl.Boolean),
            pl.Series('s1', ['hello', None, 'goodbye'], dtype=pl.String),
            pl.Series('s2', ['àçéèïöô', 'aceeioo', None], dtype=pl.String),
            pl.Series('dti', [dt_m1, None, dt_333333], dtype=pl.Datetime),
            pl.Series('dte', ['31/12/1999 23:59:59', '02/02/2002 02:02:02',
                              None], dtype=pl.String),
            pl.Series('dtu', ['12/31/1999 11:59:59p', None,
                              '04/03/2005 03:02:01a'], dtype=pl.String),


            pl.Series('di', [d_m1, d_212, None], dtype=pl.Datetime),
            pl.Series('de', ['31/12/1999', None, '03/03/2003'],
                      dtype=pl.String),
            pl.Series('du', ['12/31/1999', '01/02/2002', None],
                      dtype=pl.String),

        ))

        cls.ref_base_df = generate_reference_base_polars_dataframe()

    def test_default_load_small(self):
        # Test loading of small.csv with polars read_csv defaults
        # No date parsing so all date/datetime fields end up as strings

        csvpath = tdpath('small.csv')
        df = pl.read_csv(csvpath)
        self.assertTrue(df.equals(self.default_read_csv_df))
        # self.assertDataFramesEqual(df, self.default_read_csv_df,
        #                            type_matching='medium')

    def test_csvw_load_small(self):
        # Test loading of small.csv with correct CSVW associated
        # metadata. All types now come in correctly
        csvpath = tdpath('small.csv')
        mdpath = tdpath('small-metadata.json')
        md = load_metadata(mdpath)
        warn, buf = testwarn()
        df = csv_to_polars(csvpath, mdpath, warner=warn)

        # Cannot read non ISO-8601 dates
        # tdda.serial gets it to read these as strings
        self.assertTrue(df.equals(self.dfisodates))
        # self.assertDataFramesEqual(df, self.correct_df)

    def test_load_latin1(self):
        # Read sig_latin1.csv correctly as iso-8859-1,
        # as specified in csvw metadata file
        mdpath = tdpath('sig-latin1-metadata.json')
        df = csv_to_polars(mdpath=mdpath)
        refpath = tdpath('sig-latin1.parquet')
        rf = pl.read_parquet(refpath)

        self.assertTrue(df.equals(rf))
        # self.assertDataFramesEqual(df, rf, type_matching='medium')

        # This is correct decoding from latin-1 (checked above)
        self.assertEqual(df['sig'][0], '¤¦¨¼½¾')

        warn, buf = testwarn()
        df = csv_to_polars(mdpath=mdpath, encoding='iso-8859-15', warner=warn)
        self.assertEqual(buf, [])
        # Check read *incorrectly* when latin9 specified
        self.assertNotEqual(df['sig'][0], '¤¦¨¼½¾')

        # More specifically, check that it is read as latin9 (iso-8859-15)
        self.assertEqual(df['sig'][0], '€ŠšŒœŸ')

    def test_load_cp1252(self):
        # Read sig_cp1252.csv correctly as cp1252
        # as specified in csvw metadata file
        mdpath = tdpath('sig-cp1252-metadata.json')
        warn, buf = testwarn()
        df = csv_to_polars(mdpath=mdpath, warner=warn)
        self.assertEqual(buf, [])
        refpath = tdpath('sig-cp1252.parquet')
        rf = pl.read_parquet(refpath)
        self.assertTrue(df.equals(rf))
        # self.assertDataFramesEqual(df, rf, type_matching='medium')

    def test_load_utf16(self):
        # Read sig_utf16.csv correctly as utf-16.
        # This includes all the characters that differ among
        # latin1 (iso-8859-1), latin9 (iso-8859-15), and cp1252.
        mdpath = tdpath('sig-equiv-utf16-metadata.json')
        warn, buf = testwarn()
        df = csv_to_polars(mdpath=mdpath, warner=warn)
        self.assertEqual(buf, [])
        refpath = tdpath('sig-equiv-utf16.parquet')
        rf = pl.read_parquet(refpath)
        self.assertTrue(df.equals(rf))
        # self.assertDataFramesEqual(df, rf, type_matching='medium')

    def test_load_utf8(self):
        # Read sig_utf16.csv correctly as utf-8.
        # This includes all the characters that differ among
        # latin1 (iso-8859-1), latin9 (iso-8859-15), and cp1252.
        mdpath = tdpath('sig-equiv-utf8-metadata.json')
        warn, buf = testwarn()
        df = csv_to_polars(mdpath=mdpath, warner=warn)
        self.assertEqual(buf, [])
        refpath = tdpath('sig-equiv-utf8.parquet')
        rf = pl.read_parquet(refpath)
        self.assertTrue(df.equals(rf))
        # self.assertDataFramesEqual(df, rf, type_matching='medium')

    def test_default_load_all_csvw_types(self):
        # Test loading of all_csvw_types.csv with polars read_csv defaults
        # This contains a column for each valid CSVW type
        # Those that csvmetadata fully supports should be loaded
        # correctly, with others loading as strings.
        #
        mdpath = tdpath('all-csvw-types-metadata.json')
        warn, buf = testwarn()
        df = csv_to_polars(mdpath=mdpath, warner=warn)
        self.assertEqual(buf, [])
        refpath = tdpath('all-csvw-types.parquet')
        rf = pl.read_parquet(refpath)
        self.assertTrue(df.equals(rf))
        # self.assertDataFramesEqual(df, rf, type_matching='medium')

    def test_csvw_load_small2(self):
        # Test loading of small.csv with correct CSVW associated
        # metadata. All types now come in correctly
        # Here we have
        #   - used | as separator (specified with delimiter in dialect
        #   - double quoted all values
        #   - used NULL as the null marker
        #
        mdpath = tdpath('small2-metadata.json')
        warn, buf = testwarn()
        df = csv_to_polars(mdpath=mdpath, warner=warn)
        self.assertEqual(len(buf), 4)  # 4 bad date fields
        self.assertTrue(df.equals(self.dfisodates))

        # self.assertDataFramesEqual(df, self.correct_df)

#     def test_load_nulls1(self):
#         mdpath = tdpath('nulls1-metadata.json')
#         refpath = tdpath('nulls1.parquet')
#         df = csv_to_polars(mdpath=mdpath)
#         rf = pl.read_parquet(refpath)
#         self.assertDataFramesEqual(df, rf)

#     def test_load_base_serial_explicit(self):
#         # Bypass tdda serial and read metadata directly from file
#         mdpath = epath('base-csv-polars.serial')
#         with open(mdpath) as f:
#             d = json.load(f)
#         params = d['polars.read_csv']
#         df = pl.read_csv(epath('base.csv'), **params)
#         diffs = pd_diff(df, self.ref_base_df,
#                         type_matching='medium', precision=6,
#                         create_temporaries=False)
#         self.assertEqual(diffs.count, 1)
#         details = diffs.details(df, self.ref_base_df)
#         self.assertEqual(details.cols, ['index', 'string_torture'])
#         self.assertEqual(details.rows, [[5, None, '']])

#     def test_load_base_with_polars_specific_serial_metadata(self):
#         # Same as previous but using read_with_tdda_serial
#         # using the polars-specific metadata
#         df = csv_to_polars(epath('base.csv'), epath('base-csv-polars.serial'))
#         diffs = pd_diff(df, self.ref_base_df,
#                         type_matching='medium', precision=6,
#                         create_temporaries=False)
#         self.assertEqual(diffs.count, 1)
#         details = diffs.details(df, self.ref_base_df)
#         self.assertEqual(details.cols, ['index', 'string_torture'])
#         self.assertEqual(details.rows, [[5, None, '']])

#     def test_load_base_with_tddaserial_metadata(self):
#         # Same as previous but using read_with_tdda_serial
#         # using the polars-specific metadata
#         df = csv_to_polars(epath('base.csv'), epath('base-csv.serial'))
#         diffs = pd_diff(df, self.ref_base_df,
#                         type_matching='medium', precision=6,

#                         create_temporaries=False)
#         self.assertEqual(diffs.count, 1)
#         details = diffs.details(df, self.ref_base_df)
#         self.assertEqual(details.cols, ['index', 'string_torture'])
#         self.assertEqual(details.rows, [[5, None, '']])

#     def test_load_base_psv_with_tddaserial(self):
#         # Same as previous but using pipe-separators
#         df = csv_to_polars(epath('base.psv'), epath('base-psv.serial'))
#         diffs = pd_diff(df, self.ref_base_df,
#                         type_matching='medium', precision=6,
#                         create_temporaries=False)
#         self.assertEqual(diffs.count, 1)
#         details = diffs.details(df, self.ref_base_df)
#         self.assertEqual(details.cols, ['index', 'string_torture'])
#         self.assertEqual(details.rows, [[5, None, '']])

#     def test_load_base_tsv_with_polars_serial(self):
#         # Same as previous but using read_with_tdda_serial
#         # using the tab separators and the polars-specific tdda serial data
#         df = csv_to_polars(epath('base.tsv'), epath('base-tsv-polars.serial'))
#         diffs = pd_diff(df, self.ref_base_df,
#                         type_matching='medium', precision=6,
#                         create_temporaries=False)
#         self.assertEqual(diffs.count, 1)
#         details = diffs.details(df, self.ref_base_df)
#         self.assertEqual(details.cols, ['index', 'string_torture'])
#         self.assertEqual(details.rows, [[5, None, '']])

#     def test_load_base_csv_with_polars_serial_dot_null(self):
#         # Using ∙ (bullet operator) as null marker
#         df = csv_to_polars(epath('base-dot-null.csv'),
#                            epath('base-dot-csv.serial'))
#         diffs = pd_diff(df, self.ref_base_df,
#                         type_matching='medium', precision=6,

#                         create_temporaries=False)
#         self.assertFalse(diffs)  # Actually reads it correctly!



# class TestCSVWTests(ReferenceTestCase):
#     csvw_d = os.path.join(os.path.dirname(__file__), 'testdata/csvw')
#     parquet_d = os.path.join(os.path.dirname(__file__),
#                              'testdata/csvw-parquet')

#     def fullpath(self, path):
#         return os.path.normpath(os.path.join(self.csvw_d, path))

#     def parquet_path(self, path):
#         """
#         Full path to parquet result for CSVW tests
#         """
#         return os.path.normpath(os.path.join(self.parquet_d, path))

#     def csv_json_paths(self, stem):
#         return (
#             os.path.join(self.csvw_d, stem + '.csv'),
#             os.path.join(self.csvw_d, stem + '.json')
#         )

#     def test001(self):
#         self._test_csv_json('test001')

#     def test002(self):
#         pass

#     def test003(self):
#         pass

#     def test004(self):
#         pass

#     def test005(self):

#         # csvw expects the IDs to be read as strings
#         # But polars reads id as int and child_id as float,
#         # because it has nulls

#         # Clearly polars behaviour is better, and there is not CSVW
#         # involved. But we might like csv_to_polars to coerce types

#         # By using upgrade_possible_ints, we get int64 for id
#         # (with no nulls) and Int64 for child_id.

#         # And by forcing the string fields in ref_df to ints,
#         # we match that.

#         # So this test is _radically_ diffferent from the corresponding
#         # CSVW test. But useful.

#         self._test_csv_json('test005', upgrade_possible_ints=True,
#                             to_ints=['id', 'child_id'])

#     def test006(self):
#         self._test_csv_json('test006')

#     def test007(self):
#         self._test_csv_json('test007')

#     def test008(self):
#         self._test_csv_json('test008', to_ints=['Book1', 'Book2'])

#     def test009(self):
#         self._test_csv_json('test009', to_ints=['GID'])

#     def test010(self):
#         self._test_csv_json('test010')

#     def test011(self):
#         test = this_function_name()  # function name
#         csvpath = self.fullpath(f'{test}/tree-ops.csv')
#         resultspath = self.fullpath(f'{test}/result.json')
#         df = csv_to_polars(csvpath, findmd=True)
#         string_to_int(df, 'GID')
#         fields = ['GID', 'on_street', 'species', 'trim_cycle',
#                   'inventory_date']
#         ref_df = csvw_json_to_df(resultspath, fields, to_ints=['GID'])

#         # The string dates are a problem because the date and month
#         # are not zero-padded.
#         # Just correct here:
#         ref_df['inventory_date'] = pd.Series([datetime.date(2010, 10, 18),
#                                               datetime.date(2010, 6, 2)],
#                                               dtype='datetime64[ns]')

#         # medium because of object/string comparisons
#         self.assertDataFramesEqual(df, ref_df, type_matching='medium')

#     def test012(self):
#         test = this_function_name()  # function name
#         mdpath = self.fullpath(f'{test}/csv-metadata.json')
#         resultspath = self.fullpath(f'{test}/result.json')


#         df, md = csv_to_polars(mdpath=mdpath, return_md=True)
#         string_to_int(df, 'GID')
#         csvpath = self.fullpath('test012/tree-ops.csv')
#         fields = ['GID', 'on_street', 'species', 'trim_cycle',
#                   'inventory_date']

#         ref_df = csvw_json_to_df(resultspath, fields, to_ints=['GID'])


#         # The string dates are a problem because the date and month
#         # are not zero-padded.
#         # Just correct here:
#         ref_df['inventory_date'] = pd.Series([datetime.date(2010, 10, 18),
#                                               datetime.date(2010, 6, 2)],
#                                               dtype='datetime64[ns]')
#         # medium because of object/string comparisons
#         self.assertDataFramesEqual(df, ref_df, type_matching='medium')

#     def test013(self):
#         test = this_function_name()  # function name
#         mdpath = self.fullpath(f'{test}-user-metadata.json')
#         resultspath = self.fullpath(f'{test}.json')

#         df, md = csv_to_polars(mdpath=mdpath, return_md=True)
#         string_to_int(df, 'GID')
#         # csvpath = self.fullpath('tree-ops.csv')
#         fields = ['GID', 'on_street', 'species', 'trim_cycle',
#                   'inventory_date']

#         ref_df = csvw_json_to_df(resultspath, fields, to_ints=['GID'])

#         # The string dates are a problem because the date and month
#         # are not zero-padded.
#         # Just correct here:
#         ref_df['inventory_date'] =  pd.Series([datetime.date(2010, 10, 18),
#                                                datetime.date(2010, 6, 2)],
#                                                dtype='datetime64[ns]')
#         # medium because of object/string comparisons
#         self.assertDataFramesEqual(df, ref_df, type_matching='medium')

#     def test014(self):
#         test = this_function_name()  # function name
#         mdpath = self.fullpath(f'{test}/linked-metadata.json')
#         resultspath = self.fullpath(f'{test}/result.json')

#         df, md = csv_to_polars(mdpath=mdpath, return_md=True)
#         string_to_int(df, 'GID')
#         # csvpath = self.fullpath(f'{test}/tree-ops.csv')
#         fields = ['GID', 'on_street', 'species', 'trim_cycle',
#                   'inventory_date']

#         ref_df = csvw_json_to_df(resultspath, fields, to_ints=['GID'])


#         # The string dates are a problem because the date and month
#         # are not zero-padded.
#         # Just correct here:
#         ref_df['inventory_date'] = pd.Series([datetime.date(2010, 10, 18),
#                                               datetime.date(2010, 6, 2)],
#                                               dtype='datetime64[ns]')
#         # medium because of object/string comparisons
#         self.assertDataFramesEqual(df, ref_df, type_matching='medium')

#     def test015(self):
#         test = this_function_name()  # function name
#         mdpath = self.fullpath(f'{test}/csv-metadata.json')
#         resultspath = self.fullpath(f'{test}/result.json')

#         df, md = csv_to_polars(mdpath=mdpath, return_md=True)
#         string_to_int(df, 'GID')
#         # csvpath = self.fullpath(f'{test}/tree-ops.csv')
#         fields = ['GID', 'on_street', 'species', 'trim_cycle',
#                   'inventory_date']

#         ref_df = csvw_json_to_df(resultspath, fields, to_ints=['GID'])


#         # The string dates are a problem because the date and month
#         # are not zero-padded.
#         # Just correct here:
#         ref_df['inventory_date'] = pd.Series([datetime.date(2010, 10, 18),
#                                               datetime.date(2010, 6, 2)],
#                                               dtype='datetime64[ns]')
#         # medium because of object/string comparisons
#         self.assertDataFramesEqual(df, ref_df, type_matching='medium')

#     def test016(self):
#         test = this_function_name()  # function name
#         mdpath = self.fullpath(f'{test}/csv-metadata.json')
#         resultspath = self.fullpath(f'{test}/result.json')

#         df, md = csv_to_polars(mdpath=mdpath, return_md=True)
#         string_to_int(df, 'GID')
#         # csvpath = self.fullpath(f'{test}/tree-ops.csv')
#         fields = ['GID', 'on_street', 'species', 'trim_cycle',
#                   'inventory_date']

#         ref_df = csvw_json_to_df(resultspath, fields, to_ints=['GID'])


#         # The string dates are a problem because the date and month
#         # are not zero-padded.
#         # Just correct here:
#         ref_df['inventory_date'] = pd.Series([datetime.date(2010, 10, 18),
#                                               datetime.date(2010, 6, 2)],
#                                               dtype='datetime64[ns]')
#         # medium because of object/string comparisons
#         self.assertDataFramesEqual(df, ref_df, type_matching='medium')

#     def test017(self):
#         test = this_function_name()  # function name
#         mdpath = self.fullpath(f'{test}/csv-metadata.json')
#         resultspath = self.fullpath(f'{test}/result.json')

#         df, md = csv_to_polars(mdpath=mdpath, return_md=True)
#         string_to_int(df, 'GID')
#         # csvpath = self.fullpath(f'{test}/tree-ops.csv')
#         fields = ['GID', 'on_street', 'species', 'trim_cycle',
#                   'inventory_date']

#         ref_df = csvw_json_to_df(resultspath, fields, to_ints=['GID'])


#         # The string dates are a problem because the date and month
#         # are not zero-padded.
#         # Just correct here:
#         ref_df['inventory_date'] = pd.Series([datetime.date(2010, 10, 18),
#                                               datetime.date(2010, 6, 2)],
#                                               dtype='datetime64[ns]')
#         # medium because of object/string comparisons
#         self.assertDataFramesEqual(df, ref_df, type_matching='medium')

#     def test018(self):
#         test = this_function_name()  # function name
#         mdpath = self.fullpath(f'{test}/tree-ops.csv-metadata.json')
#         resultspath = self.fullpath(f'{test}/result.json')

#         df, md = csv_to_polars(mdpath=mdpath, return_md=True)
#         string_to_int(df, 'GID')
#         # csvpath = self.fullpath(f'{test}/tree-ops.csv')
#         fields = ['GID', 'on_street', 'species', 'trim_cycle',
#                   'inventory_date']

#         ref_df = csvw_json_to_df(resultspath, fields, to_ints=['GID'])


#         # The string dates are a problem because the date and month
#         # are not zero-padded.
#         # Just correct here:
#         ref_df['inventory_date'] = pd.Series([datetime.date(2010, 10, 18),
#                                               datetime.date(2010, 6, 2)],
#                                               dtype='datetime64[ns]')
#         # medium because of object/string comparisons
#         self.assertDataFramesEqual(df, ref_df, type_matching='medium')

#     def test019(self):
#         pass

#     def test020(self):
#         pass

#     def test021(self):
#         pass

#     def test022(self):
#         pass

#     def test023(self):
#         test = this_function_name()
#         mdpath = self.fullpath(f'{test}-user-metadata.json')
#         resultspath = self.fullpath(f'{test}.json')

#         df = csv_to_polars(mdpath=mdpath)
#         self.assertEqual(list(df), [0, 1, 2, 3, 4])
#         # This is what Polars does:  ^^^
#         # CSVW wants _col.1 to _col.5 apparently.

#         fields = df.columns = [f'_col.{i + 1}' for i in range(len(df.columns))]
#         ref_df = csvw_json_to_df(resultspath, fields)

#         # medium because of object/string comparisons
#         self.assertDataFramesEqual(df, ref_df, type_matching='medium')

#     def test024(self):
#         pass

#     def test025(self):
#         pass

#     def test026(self):
#         pass


#     def test027(self):
#         test = this_function_name()
#         mdpath = self.fullpath(f'{test}-user-metadata.json')
#         resultspath = self.fullpath(f'{test}.json')

#         df = csv_to_polars(mdpath=mdpath)
#         fields = ['GID', 'on_street', 'species', 'trim_cycle',
#                   'inventory_date']
#         ref_df = csvw_bare_json_to_df(resultspath, fields)

#         # medium because of object/string comparisons
#         self.assertDataFramesEqual(df, ref_df, type_matching='medium')

#     def test028(self):
#         test = this_function_name()
#         csvpath = self.fullpath('countries.csv')
#         resultspath = self.fullpath(f'{test}.json')

#         df = csv_to_polars(csvpath)
#         fields = fields_from(csvpath)
#         ref_df = csvw_json_to_df(resultspath, fields)
#         string_to_float(ref_df, 'latitude')
#         string_to_float(ref_df, 'longitude')

#         # medium because of object/string comparisons
#         self.assertDataFramesEqual(df, ref_df)

#     def test029(self):
#         test = this_function_name()
#         csvpath = self.fullpath('countries.csv')
#         resultspath = self.fullpath(f'{test}.json')

#         df = csv_to_polars(csvpath)
#         fields = fields_from(csvpath)
#         ref_df = csvw_bare_json_to_df(resultspath, fields)
#         string_to_float(ref_df, 'latitude')
#         string_to_float(ref_df, 'longitude')

#         # medium because of object/string comparisons
#         self.assertDataFramesEqual(df, ref_df)

#     def test030(self):
#         test = this_function_name()
#         csvpath = self.fullpath('countries.csv')
#         mdpath = self.fullpath('countries.json')
#         resultspath = self.fullpath(f'{test}.json')  # contains two tables

#         df = csv_to_polars(csvpath, mdpath, table_number=0)
#         fields = fields_from(csvpath)
#         ref_fields = [
#             'http://www.geonames.org/ontology#countryCode',
#             "schema:latitude",
#             "schema:longitude",
#             "schema:name",
#         ]

#         ref_df = csvw_json_to_df(resultspath, ref_fields, table_number=0)
#         ref_df.columns = fields
#         string_to_float(ref_df, 'latitude')
#         string_to_float(ref_df, 'longitude')
#         self.assertDataFramesEqual(df, ref_df, type_matching='medium')

#         slice_csvpath = self.fullpath('country_slice.csv')
#         df2 = csv_to_polars(slice_csvpath, mdpath, table_number=1)
#         slice_fields = fields_from(slice_csvpath)
#         ref_df2 = csvw_json_to_df(resultspath, slice_fields, table_number=1)
#         ref_df2['countryRef'] = (
#             ref_df2['countryRef'].apply(lambda s: s.split('#')[-1])
#         )
#         self.assertDataFramesEqual(df2, ref_df2, type_matching='medium')

#     def test031(self):
#         # single json output with different kinds of records
#         # not really appropriate for what tdda.serial is trying to do
#         pass

#     def test032(self):
#         test = this_function_name()
#         csvpath = self.fullpath(f'{test}/events-listing.csv')
#         resultspath = self.parquet_path(f'{test}-result.parquet')
#         mdpath = self.fullpath(f'{test}/csv-metadata.json')

#         df, md = csv_to_polars(csvpath, mdpath, return_md=True, verbosity=1)
#         self.assertEqual(len(md.warnings), 5)  # 5 virtual fields

#         # Compare against known correct result (not from csvw project)
#         self.assertDataFrameCorrect(df, resultspath)

#     def test033(self):
#         pass  # same as 32 for our purposes

#     def test034(self):
#         test = this_function_name()
#         f = self.fullpath
#         pqp = self.parquet_path
#         mdpath = f(f'{test}/csv-metadata.json')
#         sdf, md = csv_to_polars(
#             f(f'{test}/senior-roles.csv'),
#             mdpath,
#             use_table_name=True,
#             upgrade_possible_ints=True,
#             return_md=True,
#             verbosity=1,
#         )
#         self.assertDataFrameCorrect(sdf, pqp(f'{test}-senior-roles.parquet'))
#         jdf = csv_to_polars(
#             f(f'{test}/junior-roles.csv'),
#             mdpath,
#             use_table_name=True,
#             upgrade_possible_ints=True,
#             verbosity=1,
#         )
#         self.assertDataFrameCorrect(jdf, pqp(f'{test}-junior-roles.parquet'))

#         pdf = csv_to_polars(
#             f(f'{test}/gov.uk/data/professions.csv'),
#             mdpath,
#             use_table_name=True,
#             upgrade_possible_ints=True,
#             verbosity=1,
#         )
#         self.assertDataFrameCorrect(jdf, pqp(f'{test}-professions.parquet'))

#         odf = csv_to_polars(
#             f(f'{test}/gov.uk/data/organizations.csv'),
#             mdpath,
#             use_table_name=True,
#             upgrade_possible_ints=True,
#             verbosity=1,
#         )
#         self.assertDataFrameCorrect(jdf, pqp(f'{test}-organizations.parquet'))

#     def test035(self):
#         pass  # same as 34 for our purposes

#     def test036(self):
#         test = this_function_name()
#         csvpath = self.fullpath(f'{test}/tree-ops-ext.csv')
#         resultspath = self.parquet_path(f'{test}-result.parquet')
#         md = load_metadata(
#             self.fullpath(f'{test}/tree-ops-ext.csv-metadata.json')
#         )
#         df = csv_to_polars(csvpath, findmd=True)
#         self.assertDataFrameCorrect(df, resultspath)



#     def _test_csv_json(self, stem, upgrade_possible_ints=False,
#                        to_ints=None):
#         csvpath, resultspath = self.csv_json_paths(stem)
#         df = csv_to_polars(csvpath, upgrade_possible_ints=upgrade_possible_ints)
#         fields = fields_from(csvpath)
#         ref_df = csvw_json_to_df(resultspath, fields, to_ints=to_ints)
#         #self.assertDataFramesEqual(df, ref_df)



# class TestPolarsFlatFileRoundTrips(ReferenceTestCase):
#     def testDefault(self):
#         df = testDataset4()
#         path = tmppath('ds4-polars-defaults.csv')
#         polars_write_csv(df, path)

#         md_path = metadata_path(path)
#         with open(md_path, 'r') as f:
#             md = f.read()
#         self.assertFileCorrect(md_path,
#                                tdpath('ds4-polars-defaults.serial'),
#                                ignore_patterns=TDDASERIAL_PATTERNS,)

#         df2 = polars_read_csv(path)
#         self.assertDataFramesEquivalent(df, df2, type_matching='medium')

#         df3 = polars_read_csv(path, md_path=md_path)
#         self.assertDataFramesEquivalent(df, df3, type_matching='medium')

#         alt_md_path = tdpath('ds4-polars-alt.serial')
#         df4 = polars_read_csv(path, md_path=alt_md_path)
#         dtypes = {k: str(df4[k].dtype) for k in df4}
#         self.assertEqual(
#             dtypes,
#             {
#                 'row': 'float64',
#                 'b': 'object',
#                 'i': 'float64',
#                 'I': 'string',
#                 'r': 'object',
#                 's': 'object',
#                 'nulllike': 'object',
#                 'd': 'datetime64[ns]',
#                 'dt': 'datetime64[ns]'
#             }
#         )

#     def testMetadataGeneration_tinycd(self):
#         # Write metadata for tiny complete (c: no nulls), default types (d)
#         df = tiny_polars_df(nulls=False, nullable_types=False)
#         csv_path = tmppath('tiny1cd3.csv')
#         md_path = tmppath('tiny1cd3.serial')
#         polars_df_to_csv(df, csv_path, md_path, flavours=THREE_FLAVOURS)

#         # Right CSV written
#         self.assertFileCorrect(csv_path, tdpath('tiny1cd3.csv'))

#         # Right metadata written
#         self.assertFileCorrect(md_path, tdpath('tiny1cd3.serial'),
#                                ignore_patterns=TDDASERIAL_PATTERNS)



#         polars_df_to_csv(df, csv_path, md_path, flavours=['tdda.serial'])
#         self.assertFileCorrect(csv_path, tdpath('tiny1cd.csv'))
#         self.assertFileCorrect(md_path, tdpath('tiny1cd.serial'),
#                                ignore_patterns=TDDASERIAL_PATTERNS)


#         polars_df_to_csv(df, csv_path, md_path, flavours=PANDAS2)
#         self.assertFileCorrect(csv_path, tdpath('tiny1cd-polars.csv'))
#         self.assertFileCorrect(md_path, tdpath('tiny1cd-polars.serial'),
#                                ignore_patterns=TDDASERIAL_PATTERNS)


#         # Read back correctly using various metadata in .serial file

#         dfa = csv_to_polars(tdpath('tiny1cd3.csv'),
#                          mdpath=tdpath('tiny1cd3.serial'),
#                          upgrade_types=False,
#                          preferred='polars.read_csv')

#         self.assertDataFramesEquivalent(dfa, df, fuzzy_nulls=True)

#         dfa = csv_to_polars(tdpath('tiny1cd3.csv'),
#                          mdpath=tdpath('tiny1cd3.serial'),
#                          upgrade_types=False,
#                          preferred='tdda.serial')
#         self.assertDataFramesEquivalent(dfa, df, fuzzy_nulls=True)

#         dfa = csv_to_polars(tdpath('tiny1cd-polars.csv'),
#                          mdpath=tdpath('tiny1cd-polars.serial'),
#                          upgrade_types=False)
#         self.assertDataFramesEquivalent(dfa, df, fuzzy_nulls=True)

#     def testMetadataGeneration_tinynd(self):
#         # Write metadata for tiny with nulls (n), default types (d)
#         df = tiny_polars_df(nulls=True, nullable_types=False)
#         csv_path = tmppath('tiny1nd3.csv')
#         md_path = tmppath('tiny1nd3.serial')
#         polars_df_to_csv(df, csv_path, md_path, flavours=THREE_FLAVOURS)
#         self.assertFileCorrect(csv_path, tdpath('tiny1nd3.csv'))
#         self.assertFileCorrect(md_path, tdpath('tiny1nd3.serial'),
#                                ignore_patterns=TDDASERIAL_PATTERNS)

#         polars_df_to_csv(df, csv_path, md_path, flavours=['tdda.serial'])
#         self.assertFileCorrect(csv_path, tdpath('tiny1nd.csv'))
#         self.assertFileCorrect(md_path, tdpath('tiny1nd.serial'),
#                                ignore_patterns=TDDASERIAL_PATTERNS)

#         polars_df_to_csv(df, csv_path, md_path, flavours=PANDAS2)
#         self.assertFileCorrect(csv_path, tdpath('tiny1nd-polars.csv'))
#         self.assertFileCorrect(md_path, tdpath('tiny1nd-polars.serial'),
#                                ignore_patterns=TDDASERIAL_PATTERNS)

#         # Read back correctly using various metadata in .serial file

#         dfa = csv_to_polars(tdpath('tiny1nd3.csv'),
#                          mdpath=tdpath('tiny1nd3.serial'),
#                          upgrade_types=False,
#                          preferred='polars.read_csv')
#         self.assertDataFramesEquivalent(dfa, df, fuzzy_nulls=True)

#         dfa = csv_to_polars(tdpath('tiny1nd3.csv'),
#                          mdpath=tdpath('tiny1nd3.serial'),
#                          upgrade_types=False,
#                          preferred='tdda.serial')
#         self.assertDataFramesEquivalent(dfa, df, fuzzy_nulls=True)

#         dfa = csv_to_polars(tdpath('tiny1nd3.csv'),
#                          mdpath=tdpath('tiny1nd-polars.serial'),
#                          upgrade_types=False)
#         self.assertDataFramesEquivalent(dfa, df, fuzzy_nulls=True)


#     def testMetadataGeneration_tinycn(self):
#         # Write metadata for tiny complete (c: no nulls), nullable types (n)
#         df = tiny_polars_df(nulls=False, nullable_types=True)
#         csv_path = tmppath('tiny1cn3.csv')
#         md_path = tmppath('tiny1cn3.serial')
#         polars_df_to_csv(df, csv_path, md_path, flavours=THREE_FLAVOURS)
#         self.assertFileCorrect(csv_path, tdpath('tiny1cn3.csv'))
#         self.assertFileCorrect(md_path, tdpath('tiny1cn3.serial'),
#                                ignore_patterns=TDDASERIAL_PATTERNS)

#         polars_df_to_csv(df, csv_path, md_path, flavours=['tdda.serial'])
#         self.assertFileCorrect(csv_path, tdpath('tiny1cn.csv'))
#         self.assertFileCorrect(md_path, tdpath('tiny1cn.serial'),
#                                ignore_patterns=TDDASERIAL_PATTERNS)

#         polars_df_to_csv(df, csv_path, md_path, flavours=PANDAS2)
#         self.assertFileCorrect(csv_path, tdpath('tiny1cn-polars.csv'))
#         self.assertFileCorrect(md_path, tdpath('tiny1cn-polars.serial'),
#                                ignore_patterns=TDDASERIAL_PATTERNS)

#         # Read back correctly using various metadata in .serial file

#         dfa = csv_to_polars(tdpath('tiny1cn3.csv'),
#                          mdpath=tdpath('tiny1cn3.serial'),
#                          upgrade_types=False,
#                          preferred='polars.read_csv')
#         self.assertDataFramesEquivalent(dfa, df, fuzzy_nulls=True)

#         dfa = csv_to_polars(tdpath('tiny1cn3.csv'),
#                          mdpath=tdpath('tiny1cn3.serial'),
#                          upgrade_types=False,
#                          preferred='tdda.serial')
#         self.assertDataFramesEquivalent(dfa, df, fuzzy_nulls=True)

#         dfa = csv_to_polars(tdpath('tiny1cn3.csv'),
#                          mdpath=tdpath('tiny1cn-polars.serial'),
#                          upgrade_types=False)
#         self.assertDataFramesEquivalent(dfa, df, fuzzy_nulls=True)

#     def testMetadataGeneration_tinynn(self):
#         # Write metadata for tiny with nulls (n), nullable types (n)
#         df = tiny_polars_df(nulls=True, nullable_types=True)
#         csv_path = tmppath('tiny1nn3.csv')
#         md_path = tmppath('tiny1nn3.serial')
#         polars_df_to_csv(df, csv_path, md_path, flavours=THREE_FLAVOURS)
#         self.assertFileCorrect(csv_path, tdpath('tiny1nn3.csv'))
#         self.assertFileCorrect(md_path, tdpath('tiny1nn3.serial'),
#                                ignore_patterns=TDDASERIAL_PATTERNS)

#         polars_df_to_csv(df, csv_path, md_path, flavours=['tdda.serial'])
#         self.assertFileCorrect(csv_path, tdpath('tiny1nn.csv'))
#         self.assertFileCorrect(md_path, tdpath('tiny1nn.serial'),
#                                ignore_patterns=TDDASERIAL_PATTERNS)

#         polars_df_to_csv(df, csv_path, md_path, flavours=PANDAS2)
#         self.assertFileCorrect(csv_path, tdpath('tiny1nn-polars.csv'))
#         self.assertFileCorrect(md_path, tdpath('tiny1nn-polars.serial'),
#                                ignore_patterns=TDDASERIAL_PATTERNS)

#         # Read back correctly using various metadata in .serial file

#         dfa = csv_to_polars(tdpath('tiny1nn3.csv'),
#                             mdpath=tdpath('tiny1nn3.serial'),
#                             upgrade_types=False,
#                             preferred='polars.read_csv')
#         self.assertDataFramesEquivalent(dfa, df, fuzzy_nulls=True)

#         dfa = csv_to_polars(tdpath('tiny1nn3.csv'),
#                             mdpath=tdpath('tiny1nn3.serial'),
#                             upgrade_types=False,
#                             preferred='tdda.serial')
#         self.assertDataFramesEquivalent(dfa, df, fuzzy_nulls=True)

#         dfa = csv_to_polars(tdpath('tiny1nn3.csv'),
#                             mdpath=tdpath('tiny1nn-polars.serial'),
#                             upgrade_types=False)
#         self.assertDataFramesEquivalent(dfa, df, fuzzy_nulls=True)


# class TestPolarsParquetRoundTrips(ReferenceTestCase):
#     # Really checking diff_dataframes more than parquet
#     # But also confirming that round-tripping is working
#     # for Polars via parquet
#     def testTinyParquetCD(self):
#         df = tiny_polars_df(nulls=False, nullable_types=False)
#         path = tmppath('tiny1cd.parquet')
#         df.to_parquet(path)
#         df2 = pl.read_parquet(path)
#         self.assertEqual(diff_dataframes(df2, df).failures, 0)

#     def testTinyParquetCN(self):
#         df = tiny_polars_df(nulls=False, nullable_types=True)
#         path = tmppath('tiny1cn.parquet')
#         df.to_parquet(path)
#         df2 = pl.read_parquet(path)
#         self.assertEqual(diff_dataframes(df2, df).failures, 0)

#     def testTinyParquetND(self):
#         df = tiny_polars_df(nulls=True, nullable_types=False)
#         path = tmppath('tiny1cd.parquet')
#         df.to_parquet(path)
#         df2 = pl.read_parquet(path)
#         self.assertEqual(diff_dataframes(df2, df).failures, 0)

#     def testTinyParquetNN(self):
#         df = tiny_polars_df(nulls=True, nullable_types=True)
#         path = tmppath('tiny1cn.parquet')
#         df.to_parquet(path)
#         df2 = pl.read_parquet(path)
#         diffs = diff_dataframes(df2, df, create_temporaries=False)
#         self.assertEqual(diff_dataframes(df2, df).failures, 0)

#     def testTinyParquetSmallWideD(self):
#         df, _ = small_wide_pd_df(prefer_nullable=False)
#         path = tmppath('small_wide-d.parquet')
#         df.to_parquet(path)
#         df2 = pl.read_parquet(path)
#         diffs = diff_dataframes(df2, df, create_temporaries=False)
#         self.assertEqual(diffs.failures, 1)  # types
#         msg = str(diffs.diffs)
#         self.assertTrue(msg.startswith(
#             'Data frames have different column structure.'
#         ))
#         diffs2 = diff_dataframes(df2, df, type_matching='medium')
#         print(diffs2.diffs)
#         self.assertEqual(diffs2.failures, 0)

#     def testTinyParquetSmallWideN(self):
#         df, _ = small_wide_pd_df(prefer_nullable=True)
#         path = tmppath('small_wide-n.parquet')
#         df.to_parquet(path)
#         df2 = pl.read_parquet(path)
#         diffs = diff_dataframes(df2, df, create_temporaries=False)
#         self.assertEqual(diffs.failures, 1)  # types
#         msg = str(diffs.diffs)
#         self.assertTrue(msg.startswith(
#             'Data frames have different column structure.'
#         ))

#         diffs2 = diff_dataframes(df2, df, type_matching='medium')
#         self.assertEqual(diffs2.failures, 0)


# class TestPolarsToMetadata(ReferenceTestCase):
#     def testSimpleDtypeFieldtypeMapping(self):
#         # WITH col passed in, prefer nullable types (defaults)

#         df, expected_types = small_wide_pd_df()
#         actual = {
#             col: polars_dtype_to_fieldtype(df[col].dtype, df[col])
#             for col in df
#         }
#         remove_common_key_vals(actual, expected_types)
#         self.assertEqual(actual, expected_types)
#         self.assertEqual(actual, {})

#     def testSimpleDtypeFieldtypeMappingNoValues(self):
#         # WITHOUT col passed in

#         df, expected_types = small_wide_pd_df(with_col=False)
#         actual = {
#             col: polars_dtype_to_fieldtype(df[col].dtype)
#             for col in df
#         }

#         remove_common_key_vals(actual, expected_types)
#         self.assertEqual(actual, expected_types)
#         self.assertEqual(actual, {})

#     def testSimpleDtypeFieldtypeMappingNotPreferNullable(self):
#         # WITHOUT preferring nullable types:

#         df, expected_types = small_wide_pd_df(prefer_nullable=False)
#         actual = {
#             col: polars_dtype_to_fieldtype(df[col].dtype, df[col],
#                                            prefer_nullable=False)
#             for col in df
#         }

#         # Similarly, with no values, the whole-number floats
#         # remain as floats

#         remove_common_key_vals(actual, expected_types)
#         self.assertEqual(actual, expected_types)
#         self.assertEqual(actual, {})

#     def testMetadataGeneration(self):
#         df, _ = small_wide_pd_df(with_col=False)
#         m = polars_df_to_metadata(df, flavours=['tdda.serial'])
#         self.assertStringCorrect(
#             str(m),
#             tdpath('small-wide.serial'),
#             ignore_patterns=TDDASERIAL_PATTERNS,
#         )


# def testDataset4():
#     return pd.DataFrame({
#         'row': [1, 2, 3, 4, 5],
#         'b': [True, False, None, False, True],
#         'i': [-1, 0, 1, None, None],
#         'I': pd.Series([-1, 0, 1, None, None], dtype='Int64'),
#         'r': [-1.25e-37, -1, None, +1, 1.25e37],
#         's': [None, 'one', 'Nöel', '''(ΑΒΓΔ φχψω "❤️‍🩹" '✔' \n \\)''', ' '],
#         'nulllike': [None, 'NULL', 'NA', 'N/A', 'na'],
#         'd': [
#             datetime.date(1969, 12, 31),
#             datetime.date(1970, 1, 1),
#             datetime.date(2040, 2, 28),
#             datetime.date(2040, 2, 29),
#             None,
#         ],
#         'dt':  [
#             datetime.datetime(1969, 12, 31, 23, 59, 59),
#             datetime.datetime(1970, 1, 1, 0, 0, 0),
#             datetime.datetime(1999, 12, 31, 23, 59, 59),
#             datetime.datetime(2038, 12, 31, 23, 59, 59),
#             None,
#         ]
#     })



# def csvw_json_to_df(path, fields, table_number=0, to_ints=None):
#     with open(path) as f:
#         d = json.load(f)
#     rows = d['tables'][table_number]['row']
#     df = pd.DataFrame({
#             field: [r['describes'][0].get(field, None) for r in rows]
#             for field in fields
#     })
#     for k in (to_ints or []):
#         string_to_int(df, k)
#     return df


# def csvw_bare_json_to_df(path, fields, to_ints=None):
#     with open(path) as f:
#         d = json.load(f)
#     rows = d
#     df = pd.DataFrame({
#             field: [r.get(field, None) for r in rows]
#             for field in fields
#     })
#     for k in (to_ints or []):
#         string_to_int(df, k)
#     return df


# def string_to_int(df, k):
#     if sum(df[k].isnull()) > 0:
#         df[k] = df[k].astype(pd.Int64Dtype())
#     else:
#         df[k] = df[k].astype('int')


# def string_to_float(df, k):
#     df[k] = df[k].astype('float')


# def fields_from(csvpath):
#     with open(csvpath) as f:
#         return f.readline().strip().split(',')


# def this_function_name():
#     """
#     Returns the name of the function (or method) from which this was called
#     """
#     return inspect.stack()[1][3]


# def small_wide_pd_df(with_col=True, prefer_nullable=True):
#     """
#     Generates a dataframe and ites expected types.
#     """
#     df = pd.DataFrame({
#        'null': pd.Series([None] * 3, dtype='O'),
#        'inull': pd.Series([None] * 3, dtype='Int64'),
#        'bnull': pd.Series([None] * 3, dtype='boolean'),
#        'fnull': pd.Series([None] * 3, dtype='float'),
#        'bn': pd.Series([True, False, None], dtype='O'),
#        'b': [True, False, True],
#        'B': pd.Series([True, False, None], dtype='boolean'),
#        'in': [1, -1, None],
#        'i': [1, -1, 0],
#        'I': pd.Series([1, -1, None], dtype='Int64'),
#        'U': pd.Series([1, 0, None], dtype='UInt64'),
#        'un': pd.Series([1, 2, None], dtype='float'),
#        'fn': [1.5, 2.0, None],
#        'f': [1.5, 2.0, 3.0],
#        'Fn': [1.0, 2.0, None],
#        'F': [1.0, 2.0, 3.0],
#        's': list('abc'),
#        'sn': ['a', 'b', None],
#        'd': [datetime.date(2025, 1, day) for day in range(1, 4)],
#        'dn': [datetime.date(2025, 1, day) for day in range(1, 3)] + [None],
#        'dt': [datetime.datetime(2025, 12, 31, 23, 59, s)
#               for s in range(57, 60)],
#        'dtn': [datetime.datetime(2025, 12, 31, 23, 59, s)
#                for s in range(58, 60)] + [None],
#        'dz': [datetime.datetime(2025, 12, 31, 23, 59, 59,
#                                 tzinfo=datetime.timezone(
#                                     datetime.timedelta(seconds=3600 * delta)))
#               for delta in (-1, 0, 1)],
#        # 'dzn': [datetime.datetime(2025, 12, 31, 23, 59, 59,
#        #                           tzinfo=datetime.timezone(
#        #                              datetime.timedelta(seconds=3600 * delta)))
#        #         for delta in (-1, 1)] + [None],
#        'dzn': [datetime.datetime.now(
#                   datetime.timezone(
#                       datetime.timedelta(seconds=3600)))] * 2 + [None]
#     })

#     types = {
#         'null': FieldType.STRING,
#         'inull': FieldType.INT,
#         'bnull': FieldType.BOOL,
#         'fnull': FieldType.FLOAT,
#         'bn': FieldType.BOOL,
#         'b': FieldType.BOOL,
#         'B': FieldType.BOOL,
#         'in': FieldType.INT,
#         'i': FieldType.INT,
#         'I': FieldType.INT,
#         'U': FieldType.INT,
#         'un': FieldType.INT,
#         'Fn': FieldType.INT,
#         'F': FieldType.INT,
#         'fn': FieldType.FLOAT,
#         'f': FieldType.FLOAT,
#         's': FieldType.STRING,
#         'sn': FieldType.STRING,
#         'd': FieldType.DATE,
#         'dn': FieldType.DATE,
#         'dt': FieldType.DATETIME,
#         'dtn': FieldType.DATETIME,
#         'dz': FieldType.DATETIME,
#         'dzn': FieldType.DATETIME_WITH_TIMEZONE,
#     }

#     if not with_col:
#         # With no values, all the object fields become strings
#         for k in ('bn', 'dn', 'd', 'dz'):
#             types[k] = FieldType.STRING

#     # Similarly, with no values, or of not prefer_nullable
#     # the whole-number floats
#     # remain as float
#     if not prefer_nullable or not with_col:
#         for k in ('F', 'Fn', 'un', 'in'):
#             types[k] = FieldType.FLOAT

#     return (df, types)


# def tiny_polars_df(nulls=False, nullable_types=False):
#     if nullable_types:
#         return pd.DataFrame({
#             k: pd.Series(v, dtype=ntype(k))
#             for k, v in tiny_python_values(nulls=nulls).items()
#         })
#     else:
#         return pd.DataFrame(tiny_python_values(nulls=nulls))


# def ntype(name):
#     d = {
#         'b': 'boolean',
#         'i': 'Int64',
#         'f': 'float',
#         'r': 'float',
#         's': 'string',
#         'd': 'datetime64[ns]',
#         't': 'datetime64[ns]',
#     }
#     return d[name[:1].lower()]




# def remove_common_key_vals(left, right):
#     for k in list(left.keys()):
#         if left[k] == right[k]:
#             del left[k]
#             del right[k]


def print_df(df):
    with pl.Config() as cfg:
        cfg.set_tbl_cols(-1)
        cfg.set_tbl_rows(-1)
        print(df)




if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
