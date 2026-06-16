import datetime
import inspect
import json
import os

import numpy as np
import pandas as pd
from tdda.pd.utils import pd3, pdmaj

from tdda.referencetest import ReferenceTestCase, tag

from tdda.referencetest.checkpandas import diff_dataframes as pd_diff

from tdda.serial.metadata import (
    FieldType,
    FieldMetadata,
    SerialMetadata,
    DateFormat,
)
from tdda.serial.csvw import CSVWMetadata
from tdda.serial.pandasio import (
    csv_to_pandas,
    csvw_to_pandas_kwargs,
    pandas_to_csv,
    pandas_df_to_metadata,
    pandas_dtype_to_fieldtype,
    serial_to_pandas_read_csv_args,
    serial_to_pandas_write_csv_python,
)
from tdda.serial.reader import (
    load_metadata,
)

from tdda.serial.simple import pandas_read_csv, pandas_write_csv, metadata_path

from tdda.referencetest.checkpandas import diff_dataframes

from tdda.serial.examples.pdgen import generate_reference_base_pandas_dataframe


from tdda.serial.testserial import (
    TESTDATADIR,
    THREE_FLAVOURS,
    TDDASERIAL_PATTERNS,
    PANDAS2,
    tdpath,
    epath,
    tmppath,
)
from tdda.utils import testwarn

from tdda.serial.datautils import (
    tiny_pandas_df,
)


ROW_HEADER = '#'


def dfEqual(self, df, exp):
    self.assertEqual(len(df), len(exp))
    self.assertEqual(list(df), list(exp))
    for col in df:
        self.assertEqual(
            ('values', col, int((df[col] == exp[col]).sum())),
            ('values', col, len(df)),
        )
        dt1 = str(df[col].dtype)
        dt2 = str(exp[col].dtype)
        if not (dt1.startswith('datetime64') and dt2.startswith('datetime64')):
            self.assertEqual(('types', col, dt1), ('types', col, dt2))


class TestPandasKeywordArgsGeneration(ReferenceTestCase):
    def test_isodate(self):
        md_path = os.path.join(TESTDATADIR, 'isod-metadata.json')
        self.assertEqual(
            csvw_to_pandas_kwargs(md_path),
            {
                'dtype': {'row': 'Int64'},
                'parse_dates': ['date'],
                'encoding': 'utf-8',
            },
        )

    def test_simple(self):
        md_path = os.path.join(TESTDATADIR, 'simple-metadata.json')
        self.assertEqual(
            csvw_to_pandas_kwargs(md_path),
            {
                'dtype': {
                    'Even': 'boolean',
                    'Index': 'Int64',
                    'Name': 'string',
                    'Odd': 'boolean',
                    'Real': 'Float64',
                },
                'encoding': 'utf-8',
                'parse_dates': ['LastInFeb', 'LastIn2024'],
            },
        )

    def test_isodate_tsv(self):
        md_path = os.path.join(TESTDATADIR, 'isodt-tsv-metadata.json')
        self.assertEqual(
            csvw_to_pandas_kwargs(md_path),
            {
                'dtype': {'row': 'Int64'},
                'parse_dates': ['time'],
                'sep': '\t',
                'encoding': 'utf-8',
            },
        )

    def test_eurodate(self):
        md_path = os.path.join(TESTDATADIR, 'eurod-metadata.json')
        self.assertEqual(
            csvw_to_pandas_kwargs(md_path),
            {
                'dtype': {'row': 'Int64'},
                'date_format': {'date': '%d/%m/%Y'},
                'parse_dates': ['date'],
                'encoding': 'utf-8',
            },
        )


class TestPandasConversion(ReferenceTestCase):
    dfEqual = dfEqual

    def test_isodate2pd(self):
        md_path = os.path.join(TESTDATADIR, 'isod-metadata.json')
        csvpath = os.path.join(TESTDATADIR, 'isod.csv')

        df = pd.read_csv(csvpath, **csvw_to_pandas_kwargs(md_path))

        self.assertEqual(df.row.dtype, 'Int64')
        self.assertTrue(str(df.date.dtype).startswith('datetime64'))

        expected = pd.DataFrame(
            {
                'row': pd.Series([1, 15], dtype='Int64'),
                'date': [
                    datetime.datetime(2024, 1, 1),
                    datetime.datetime(2024, 1, 15),
                ],
            }
        )
        self.dfEqual(df, expected)

    def test_simple2metadata(self):
        md_path = os.path.join(TESTDATADIR, 'simple-metadata.json')
        md = CSVWMetadata(md_path)
        self.assertStringCorrect(
            str(md),
            tdpath('expected/simple-md.json'),
            ignore_substrings=[
                '_metadata_source_path',
                '_metadata_source_dir',
            ],
            ignore_patterns=TDDASERIAL_PATTERNS,
        )

    def test_simple2pd(self):
        md_path = os.path.join(TESTDATADIR, 'simple-metadata.json')
        csvpath = os.path.join(TESTDATADIR, 'simple.csv')

        kw = csvw_to_pandas_kwargs(md_path)
        self.assertEqual(
            kw,
            {
                'dtype': {
                    'Even': 'boolean',
                    'Index': 'Int64',
                    'Name': 'string',
                    'Odd': 'boolean',
                    'Real': 'Float64',
                },
                'encoding': 'utf-8',
                'parse_dates': ['LastInFeb', 'LastIn2024'],
            },
        )
        df = pd.read_csv(csvpath, **kw)

        expected = pd.DataFrame(
            {
                'Index': pd.Series([0, 1, 2], dtype='Int64'),
                'Odd': pd.Series([False, True, False], dtype='boolean'),
                'Even': pd.Series([True, False, True], dtype='boolean'),
                'Real': pd.Series([0.0, 1.125, 2.25], dtype='Float64'),
                'Name': pd.Series(['zero', 'one', 'two'], dtype='string'),
                'LastInFeb': pd.Series(
                    [
                        datetime.datetime(2024, 2, 20),
                        datetime.datetime(2024, 2, 21),
                        datetime.datetime(2024, 2, 22),
                    ],
                    dtype='datetime64[ns]',
                ),
                'LastIn2024': pd.Series(
                    [
                        datetime.datetime(2024, 2, 29, 23, 59, 50),
                        datetime.datetime(2024, 2, 29, 23, 59, 51),
                        datetime.datetime(2024, 2, 29, 23, 59, 52),
                    ],
                    dtype='datetime64[ns]',
                ),
            }
        )

        self.dfEqual(df, expected)

    def test_isodate_tsv2pd(self):
        md_path = os.path.join(TESTDATADIR, 'isodt-tsv-metadata.json')
        csvpath = os.path.join(TESTDATADIR, 'isodt.tsv')

        df = pd.read_csv(csvpath, **csvw_to_pandas_kwargs(md_path))

        expected = pd.DataFrame(
            {
                'row': pd.Series([1, 15], dtype='Int64'),
                'time': [
                    datetime.datetime(2024, 1, 1, 11, 11, 11),
                    datetime.datetime(2024, 1, 15, 22, 22, 22),
                ],
            }
        )
        self.dfEqual(df, expected)

    def test_eurodate2pd(self):
        md_path = os.path.join(TESTDATADIR, 'eurod-metadata.json')
        csvpath = os.path.join(TESTDATADIR, 'eurod.csv')
        # kw = csvw_to_pandas_kwargs(md_path)
        df = pd.read_csv(csvpath, **csvw_to_pandas_kwargs(md_path))

        expected = pd.DataFrame(
            {
                'row': pd.Series([1, 15], dtype='Int64'),
                'date': pd.Series(
                    [
                        datetime.datetime(2024, 1, 1),
                        datetime.datetime(2024, 1, 15),
                    ],
                    dtype='datetime64[ns]',
                ),
            }
        )
        self.dfEqual(df, expected)


class TestPandasLoad(ReferenceTestCase):
    @classmethod
    def setUpClass(cls):
        # This is the dataframe that is read by pd.read_csv
        # with no kwargs
        cls.default_read_csv_df = pd.DataFrame(
            {
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
                'dtu': [
                    '12/31/1999 11:59:59PM',
                    np.nan,
                    '04/03/2005 03:02:01AM',
                ],
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
            }
        )

        fromiso = datetime.datetime.fromisoformat
        dt_m1 = datetime.datetime(1999, 12, 31, 23, 59, 59)
        d_m1 = datetime.date(1999, 12, 31)
        d_212 = datetime.date(2002, 1, 2)
        d_543 = datetime.date(2005, 4, 3)
        d_333 = datetime.date(2003, 3, 3)
        dt_333333 = datetime.datetime(2003, 3, 3, 3, 3, 3)
        dt_222222 = datetime.datetime(2002, 2, 2, 2, 2, 2)
        dt_543_321 = datetime.datetime(2005, 4, 3, 3, 2, 1)
        dtz_m1_1 = fromiso('1999-12-31T23:59:59+01:00')
        dtz_333_321_1 = fromiso('2003-03-03T03:02:01+01:00')
        dtz_212_321_1 = fromiso('2002-01-02T03:02:01+01:00')
        dtz_m1_m5 = fromiso('1999-12-31T23:59:59-05:00')
        dtz_333_543_m8 = fromiso('2003-03-03T05:04:03-08:00')

        cls.correct_df = pd.DataFrame(
            {
                'i1': pd.Series([1, 2, 3], dtype='Int64'),
                'i2': pd.Series([1, np.nan, 3], dtype='Int64'),
                'i3': pd.Series([-1, -2, np.nan], dtype='Int64'),
                'f1': pd.Series([1.5, np.nan, 3.5], dtype='float'),
                'f2': pd.Series([-1.5, -2.5, np.nan], dtype='float'),
                'b1': pd.Series([True, np.nan, True], dtype='boolean'),
                'b2': pd.Series([False, False, np.nan], dtype='boolean'),
                's1': pd.Series(['hello', pd.NA, 'goodbye'], dtype='string'),
                's2': pd.Series(['àçéèïöô', 'aceeioo', pd.NA], dtype='string'),
                'dti': pd.Series(
                    [dt_m1, pd.NaT, dt_333333], dtype='datetime64[ns]'
                ),
                'dte': pd.Series(
                    [dt_m1, dt_222222, pd.NaT], dtype='datetime64[ns]'
                ),
                'dtu': pd.Series(
                    [dt_m1, pd.NaT, dt_543_321], dtype='datetime64[ns]'
                ),
                'di': pd.Series([d_m1, d_212, pd.NaT], dtype='datetime64[ns]'),
                'de': pd.Series([d_m1, pd.NaT, d_333], dtype='datetime64[ns]'),
                'du': pd.Series([d_m1, d_212, pd.NaT], dtype='datetime64[ns]'),
                # 'dtzi': pd.Series([dtz_m1_1, pd.NaT, dtz_333_321_1],
                #                    dtype='datetime64[ns]'),
                # 'dtze': pd.Series([dtz_m1_1, dtz_212_321_1, pd.NaT],
                #                    dtype='datetime64[ns]'),
                # 'dtzu': pd.Series([dtz_m1_m5, pd.NaT, dtz_333_543_m8],
                #                   dtype='datetime64[ns]'),
            }
        )

        cls.ref_base_df = generate_reference_base_pandas_dataframe()

    def test_default_load_small(self):
        # Test loading of small.csv with pandas read_csv defaults
        # No date parsing so all date/datetime fields end up as strings
        csvpath = os.path.join(TESTDATADIR, 'small.csv')
        df = pd.read_csv(csvpath)
        self.assertDataFramesEqual(
            df, self.default_read_csv_df, type_matching='medium'
        )

    def test_csvw_load_small(self):
        # Test loading of small.csv with correct CSVW associated
        # metadata. All types now come in correctly
        csvpath = os.path.join(TESTDATADIR, 'small.csv')
        md_path = os.path.join(TESTDATADIR, 'small-metadata.json')
        df = csv_to_pandas(csvpath, md_path)
        self.assertDataFramesEqual(df, self.correct_df)

    def test_load_latin1(self):
        # Read sig_latin1.csv correctly as iso-8859-1,
        # as specified in csvw metadata file
        md_path = os.path.join(TESTDATADIR, 'sig-latin1-metadata.json')
        df = csv_to_pandas(md_path=md_path)
        refpath = os.path.join(TESTDATADIR, 'sig-latin1.parquet')
        rf = pd.read_parquet(refpath)
        self.assertDataFramesEqual(df, rf, type_matching='medium')

        # This is correct decoding from latin-1 (checked above)
        self.assertEqual(df.sig[0], '¤¦¨¼½¾')

        df = csv_to_pandas(md_path=md_path, encoding='iso-8859-15')

        # Check read *incorrectly* when latin9 specified
        self.assertNotEqual(df.sig[0], '¤¦¨¼½¾')

        # More specifically, check that it is read as latin9 (iso-8859-15)
        self.assertEqual(df.sig[0], '€ŠšŒœŸ')

    def test_load_latin9(self):
        # Read sig_latin9.csv correctly as iso-8859-15,
        # as specified in csvw metadata file
        md_path = os.path.join(TESTDATADIR, 'sig-latin9-metadata.json')
        df = csv_to_pandas(md_path=md_path)
        refpath = os.path.join(TESTDATADIR, 'sig-latin9.parquet')
        rf = pd.read_parquet(refpath)
        self.assertDataFramesEqual(df, rf, type_matching='medium')

    def test_load_cp1252(self):
        # Read sig_cp1252.csv correctly as cp1252
        # as specified in csvw metadata file
        md_path = os.path.join(TESTDATADIR, 'sig-cp1252-metadata.json')
        df = csv_to_pandas(md_path=md_path)
        refpath = os.path.join(TESTDATADIR, 'sig-cp1252.parquet')
        rf = pd.read_parquet(refpath)
        self.assertDataFramesEqual(df, rf, type_matching='medium')

    def test_load_utf16(self):
        # Read sig_utf16.csv correctly as utf-16.
        # This includes all the characters that differ among
        # latin1 (iso-8859-1), latin9 (iso-8859-15), and cp1252.
        md_path = os.path.join(TESTDATADIR, 'sig-equiv-utf16-metadata.json')
        df = csv_to_pandas(md_path=md_path)
        refpath = os.path.join(TESTDATADIR, 'sig-equiv-utf16.parquet')
        rf = pd.read_parquet(refpath)
        self.assertDataFramesEqual(df, rf, type_matching='medium')

    def test_load_utf8(self):
        # Read sig_utf16.csv correctly as utf-8.
        # This includes all the characters that differ among
        # latin1 (iso-8859-1), latin9 (iso-8859-15), and cp1252.
        md_path = os.path.join(TESTDATADIR, 'sig-equiv-utf8-metadata.json')
        df = csv_to_pandas(md_path=md_path)
        refpath = os.path.join(TESTDATADIR, 'sig-equiv-utf8.parquet')
        rf = pd.read_parquet(refpath)
        self.assertDataFramesEqual(df, rf, type_matching='medium')

    def test_default_load_all_csvw_types(self):
        # Test loading of all_csvw_types.csv with pandas read_csv defaults
        # This contains a column for each valid CSVW type
        # Those that csvmetadata fully supports should be loaded
        # correctly, with others loading as strings.
        #
        md_path = os.path.join(TESTDATADIR, 'all-csvw-types-metadata.json')
        df = csv_to_pandas(md_path=md_path)
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
        md_path = os.path.join(TESTDATADIR, 'small2-metadata.json')
        df = csv_to_pandas(md_path=md_path)
        self.assertDataFramesEqual(df, self.correct_df)

    def test_load_nulls1(self):
        md_path = os.path.join(TESTDATADIR, 'nulls1-metadata.json')
        refpath = os.path.join(TESTDATADIR, 'nulls1.parquet')

        df = csv_to_pandas(md_path=md_path, backend='original')
        rf = pd.read_parquet(refpath, dtype_backend='numpy_nullable')
        self.assertDataFramesEqual(df, rf, type_matching='loose')

        df = csv_to_pandas(md_path=md_path, backend='numpy_nullable')
        self.assertDataFramesEqual(df, rf, type_matching='loose')

    def test_load_base_serial_explicit(self):
        # Bypass tdda serial and read metadata directly from file
        md_path = epath('base-csv-pandas.serial')
        with open(md_path) as f:
            d = json.load(f)
        params = d['pandas.read_csv']
        df = pd.read_csv(epath('base.csv'), **params)
        diffs = pd_diff(
            df,
            self.ref_base_df,
            type_matching='medium',
            precision=6,
            create_temporaries=False,
        )
        # In pandas 3, mixed-timezone datetimes can't be stored in a typed
        # column so datetimezone stays as strings, making it appear different
        # from the reference's datetime.datetime objects.
        expected_cols = [ROW_HEADER, 'string_torture']
        if pd3:
            expected_cols.append('datetimezone')
        details = diffs.details(df, self.ref_base_df)
        self.assertEqual(details.cols, expected_cols)
        if not pd3:
            self.assertEqual(details.rows, [[5, pd.NA, '']])

    def test_load_base_with_pandas_specific_serial_metadata(self):
        # Same as previous but using read_with_tdda_serial
        # using the pandas-specific metadata
        df = csv_to_pandas(epath('base.csv'), epath('base-csv-pandas.serial'))
        diffs = pd_diff(
            df,
            self.ref_base_df,
            type_matching='medium',
            precision=6,
            create_temporaries=False,
        )
        self.assertEqual(diffs.count, 1)
        details = diffs.details(df, self.ref_base_df)
        self.assertEqual(details.cols, [ROW_HEADER, 'string_torture'])
        self.assertEqual(details.rows, [[5, pd.NA, '']])

    def test_load_base_with_serial_metadata(self):
        # Same as previous but using read_with_tdda_serial
        # using the pandas-specific metadata
        df = csv_to_pandas(epath('base.csv'), epath('base-csv.serial'))
        diffs = pd_diff(
            df,
            self.ref_base_df,
            type_matching='medium',
            precision=6,
            create_temporaries=False,
        )
        self.assertEqual(diffs.count, 1)
        details = diffs.details(df, self.ref_base_df)
        self.assertEqual(details.cols, [ROW_HEADER, 'string_torture'])
        self.assertEqual(details.rows, [[5, pd.NA, '']])

    def test_load_base_psv_with_serial(self):
        # Same as previous but using pipe-separators
        df = csv_to_pandas(epath('base.psv'), epath('base-psv.serial'))
        diffs = pd_diff(
            df,
            self.ref_base_df,
            type_matching='medium',
            precision=6,
            create_temporaries=False,
        )
        self.assertEqual(diffs.count, 1)
        details = diffs.details(df, self.ref_base_df)
        self.assertEqual(details.cols, [ROW_HEADER, 'string_torture'])
        self.assertEqual(details.rows, [[5, pd.NA, '']])

    def test_load_base_tsv_with_pandas_serial(self):
        # Same as previous but using read_with_tdda_serial
        # using the tab separators and the pandas-specific tdda serial data
        df = csv_to_pandas(epath('base.tsv'), epath('base-tsv-pandas.serial'))
        diffs = pd_diff(
            df,
            self.ref_base_df,
            type_matching='medium',
            precision=6,
            create_temporaries=False,
        )
        self.assertEqual(diffs.count, 1)
        details = diffs.details(df, self.ref_base_df)
        self.assertEqual(details.cols, [ROW_HEADER, 'string_torture'])
        self.assertEqual(details.rows, [[5, pd.NA, '']])

    def test_load_base_csv_with_pandas_serial_dot_null(self):
        # Using ∙ (bullet operator) as null marker
        df = csv_to_pandas(
            epath('base-dot-null.csv'), epath('base-dot-csv.serial')
        )
        diffs = pd_diff(
            df,
            self.ref_base_df,
            type_matching='medium',
            precision=6,
            create_temporaries=False,
        )
        self.assertFalse(diffs)  # Actually reads it correctly!


class TestPandasCSVWTests(ReferenceTestCase):
    csvw_d = os.path.join(os.path.dirname(__file__), 'testdata/csvw')
    parquet_d = os.path.join(
        os.path.dirname(__file__), 'testdata/csvw-parquet'
    )

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
            os.path.join(self.csvw_d, stem + '.json'),
        )

    def test001(self):
        self._test_csv_json('test001')

    # def test002(self):
    #     pass

    # def test003(self):
    #     pass

    # def test004(self):
    #     pass

    def test005(self):
        # csvw expects the IDs to be read as strings
        # But pandas reads id as int and child_id as float,
        # because it has nulls

        # Clearly pandas behaviour is better, and there is not CSVW
        # involved. But we might like csv_to_pandas to coerce types

        # By using upgrade_possible_ints, we get int64 for id
        # (with no nulls) and Int64 for child_id.

        # And by forcing the string fields in ref_df to ints,
        # we match that.

        # So this test is _radically_ diffferent from the corresponding
        # CSVW test. But useful.

        self._test_csv_json(
            'test005', upgrade_possible_ints=True, to_ints=['id', 'child_id']
        )

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
        df = csv_to_pandas(csvpath, find_md=True, verbosity=1)
        string_to_int(df, 'GID')
        fields = [
            'GID',
            'on_street',
            'species',
            'trim_cycle',
            'inventory_date',
        ]
        ref_df = csvw_json_to_df(resultspath, fields, to_ints=['GID'])

        # The string dates are a problem because the date and month
        # are not zero-padded.
        # Just correct here:
        ref_df['inventory_date'] = pd.Series(
            [datetime.date(2010, 10, 18), datetime.date(2010, 6, 2)],
            dtype='datetime64[ns]',
        )

        # medium because of object/string comparisons
        self.assertDataFramesEqual(df, ref_df, type_matching='medium')

    def test012(self):
        test = this_function_name()  # function name
        md_path = self.fullpath(f'{test}/csv-metadata.json')
        resultspath = self.fullpath(f'{test}/result.json')

        df, md = csv_to_pandas(md_path=md_path, return_md=True, verbosity=1)
        string_to_int(df, 'GID')
        csvpath = self.fullpath('test012/tree-ops.csv')
        fields = [
            'GID',
            'on_street',
            'species',
            'trim_cycle',
            'inventory_date',
        ]

        ref_df = csvw_json_to_df(resultspath, fields, to_ints=['GID'])

        # The string dates are a problem because the date and month
        # are not zero-padded.
        # Just correct here:
        ref_df['inventory_date'] = pd.Series(
            [datetime.date(2010, 10, 18), datetime.date(2010, 6, 2)],
            dtype='datetime64[ns]',
        )
        # medium because of object/string comparisons
        self.assertDataFramesEqual(df, ref_df, type_matching='medium')

    def test013(self):
        test = this_function_name()  # function name
        md_path = self.fullpath(f'{test}-user-metadata.json')
        resultspath = self.fullpath(f'{test}.json')

        df, md = csv_to_pandas(md_path=md_path, return_md=True, verbosity=1)
        string_to_int(df, 'GID')
        # csvpath = self.fullpath('tree-ops.csv')
        fields = [
            'GID',
            'on_street',
            'species',
            'trim_cycle',
            'inventory_date',
        ]

        ref_df = csvw_json_to_df(resultspath, fields, to_ints=['GID'])

        # The string dates are a problem because the date and month
        # are not zero-padded.
        # Just correct here:
        ref_df['inventory_date'] = pd.Series(
            [datetime.date(2010, 10, 18), datetime.date(2010, 6, 2)],
            dtype='datetime64[ns]',
        )
        # medium because of object/string comparisons
        self.assertDataFramesEqual(df, ref_df, type_matching='medium')

    def test014(self):
        test = this_function_name()  # function name
        md_path = self.fullpath(f'{test}/linked-metadata.json')
        resultspath = self.fullpath(f'{test}/result.json')

        df, md = csv_to_pandas(md_path=md_path, return_md=True, verbosity=1)
        string_to_int(df, 'GID')
        # csvpath = self.fullpath(f'{test}/tree-ops.csv')
        fields = [
            'GID',
            'on_street',
            'species',
            'trim_cycle',
            'inventory_date',
        ]

        ref_df = csvw_json_to_df(resultspath, fields, to_ints=['GID'])

        # The string dates are a problem because the date and month
        # are not zero-padded.
        # Just correct here:
        ref_df['inventory_date'] = pd.Series(
            [datetime.date(2010, 10, 18), datetime.date(2010, 6, 2)],
            dtype='datetime64[ns]',
        )
        # medium because of object/string comparisons
        self.assertDataFramesEqual(df, ref_df, type_matching='medium')

    def test015(self):
        test = this_function_name()  # function name
        md_path = self.fullpath(f'{test}/csv-metadata.json')
        resultspath = self.fullpath(f'{test}/result.json')

        df, md = csv_to_pandas(md_path=md_path, return_md=True, verbosity=1)
        string_to_int(df, 'GID')
        # csvpath = self.fullpath(f'{test}/tree-ops.csv')
        fields = [
            'GID',
            'on_street',
            'species',
            'trim_cycle',
            'inventory_date',
        ]

        ref_df = csvw_json_to_df(resultspath, fields, to_ints=['GID'])

        # The string dates are a problem because the date and month
        # are not zero-padded.
        # Just correct here:
        ref_df['inventory_date'] = pd.Series(
            [datetime.date(2010, 10, 18), datetime.date(2010, 6, 2)],
            dtype='datetime64[ns]',
        )
        # medium because of object/string comparisons
        self.assertDataFramesEqual(df, ref_df, type_matching='medium')

    def test016(self):
        test = this_function_name()  # function name
        md_path = self.fullpath(f'{test}/csv-metadata.json')
        resultspath = self.fullpath(f'{test}/result.json')

        df, md = csv_to_pandas(md_path=md_path, return_md=True, verbosity=1)
        string_to_int(df, 'GID')
        # csvpath = self.fullpath(f'{test}/tree-ops.csv')
        fields = [
            'GID',
            'on_street',
            'species',
            'trim_cycle',
            'inventory_date',
        ]

        ref_df = csvw_json_to_df(resultspath, fields, to_ints=['GID'])

        # The string dates are a problem because the date and month
        # are not zero-padded.
        # Just correct here:
        ref_df['inventory_date'] = pd.Series(
            [datetime.date(2010, 10, 18), datetime.date(2010, 6, 2)],
            dtype='datetime64[ns]',
        )
        # medium because of object/string comparisons
        self.assertDataFramesEqual(df, ref_df, type_matching='medium')

    def test017(self):
        test = this_function_name()  # function name
        md_path = self.fullpath(f'{test}/csv-metadata.json')
        resultspath = self.fullpath(f'{test}/result.json')

        df, md = csv_to_pandas(md_path=md_path, return_md=True, verbosity=1)
        string_to_int(df, 'GID')
        # csvpath = self.fullpath(f'{test}/tree-ops.csv')
        fields = [
            'GID',
            'on_street',
            'species',
            'trim_cycle',
            'inventory_date',
        ]

        ref_df = csvw_json_to_df(resultspath, fields, to_ints=['GID'])

        # The string dates are a problem because the date and month
        # are not zero-padded.
        # Just correct here:
        ref_df['inventory_date'] = pd.Series(
            [datetime.date(2010, 10, 18), datetime.date(2010, 6, 2)],
            dtype='datetime64[ns]',
        )
        # medium because of object/string comparisons
        self.assertDataFramesEqual(df, ref_df, type_matching='medium')

    def test018(self):
        test = this_function_name()  # function name
        md_path = self.fullpath(f'{test}/tree-ops.csv-metadata.json')
        resultspath = self.fullpath(f'{test}/result.json')

        df, md = csv_to_pandas(md_path=md_path, return_md=True, verbosity=1)
        string_to_int(df, 'GID')
        # csvpath = self.fullpath(f'{test}/tree-ops.csv')
        fields = [
            'GID',
            'on_street',
            'species',
            'trim_cycle',
            'inventory_date',
        ]

        ref_df = csvw_json_to_df(resultspath, fields, to_ints=['GID'])

        # The string dates are a problem because the date and month
        # are not zero-padded.
        # Just correct here:
        ref_df['inventory_date'] = pd.Series(
            [datetime.date(2010, 10, 18), datetime.date(2010, 6, 2)],
            dtype='datetime64[ns]',
        )
        # medium because of object/string comparisons
        self.assertDataFramesEqual(df, ref_df, type_matching='medium')

    # def test019(self):
    #     pass

    # def test020(self):
    #     pass

    # def test021(self):
    #     pass

    # def test022(self):
    #     pass

    def test023(self):
        test = this_function_name()
        md_path = self.fullpath(f'{test}-user-metadata.json')
        resultspath = self.fullpath(f'{test}.json')

        df = csv_to_pandas(md_path=md_path)
        self.assertEqual(list(df), [0, 1, 2, 3, 4])
        # This is what Pandas does:  ^^^
        # CSVW wants _col.1 to _col.5 apparently.

        fields = df.columns = [f'_col.{i + 1}' for i in range(len(df.columns))]
        ref_df = csvw_json_to_df(resultspath, fields)

        # medium because of object/string comparisons
        self.assertDataFramesEqual(df, ref_df, type_matching='medium')

    # def test024(self):
    #     pass

    # def test025(self):
    #     pass

    # def test026(self):
    #     pass

    def test027(self):
        test = this_function_name()
        md_path = self.fullpath(f'{test}-user-metadata.json')
        resultspath = self.fullpath(f'{test}.json')

        df = csv_to_pandas(md_path=md_path, verbosity=1)
        fields = [
            'GID',
            'on_street',
            'species',
            'trim_cycle',
            'inventory_date',
        ]
        ref_df = csvw_bare_json_to_df(
            resultspath, fields, to_dates=['inventory_date']
        )
        self.assertDataFramesEqual(df, ref_df, type_matching='medium')

    def test028(self):
        test = this_function_name()
        csvpath = self.fullpath('countries.csv')
        resultspath = self.fullpath(f'{test}.json')

        df = csv_to_pandas(csvpath)
        fields = fields_from(csvpath)
        ref_df = csvw_json_to_df(resultspath, fields)
        string_to_float(ref_df, 'latitude')
        string_to_float(ref_df, 'longitude')

        # medium because of object/string comparisons
        self.assertDataFramesEqual(df, ref_df, type_matching='medium')

    def test029(self):
        test = this_function_name()
        csvpath = self.fullpath('countries.csv')
        resultspath = self.fullpath(f'{test}.json')

        df = csv_to_pandas(csvpath)
        fields = fields_from(csvpath)
        ref_df = csvw_bare_json_to_df(resultspath, fields)
        string_to_float(ref_df, 'latitude')
        string_to_float(ref_df, 'longitude')

        # medium because of object/string comparisons
        self.assertDataFramesEqual(df, ref_df, type_matching='medium')

    def test030(self):
        test = this_function_name()
        csvpath = self.fullpath('countries.csv')
        md_path = self.fullpath('countries.json')
        resultspath = self.fullpath(f'{test}.json')  # contains two tables

        df = csv_to_pandas(csvpath, md_path, table_number=0)
        fields = fields_from(csvpath)
        ref_fields = [
            'http://www.geonames.org/ontology#countryCode',
            'schema:latitude',
            'schema:longitude',
            'schema:name',
        ]

        ref_df = csvw_json_to_df(resultspath, ref_fields, table_number=0)
        ref_df.columns = fields
        string_to_float(ref_df, 'latitude')
        string_to_float(ref_df, 'longitude')
        self.assertDataFramesEqual(df, ref_df, type_matching='medium')

        slice_csvpath = self.fullpath('country_slice.csv')
        df2 = csv_to_pandas(slice_csvpath, md_path, table_number=1)
        slice_fields = fields_from(slice_csvpath)
        ref_df2 = csvw_json_to_df(resultspath, slice_fields, table_number=1)
        ref_df2['countryRef'] = ref_df2['countryRef'].apply(
            lambda s: s.split('#')[-1]
        )
        self.assertDataFramesEqual(df2, ref_df2, type_matching='medium')

    # def test031(self):
    #     # single json output with different kinds of records
    #     # not really appropriate for what tdda.serial is trying to do
    #     pass

    def test032(self):
        test = this_function_name()
        csvpath = self.fullpath(f'{test}/events-listing.csv')
        resultspath = self.parquet_path(f'{test}-result.parquet')
        md_path = self.fullpath(f'{test}/csv-metadata.json')

        df, md = csv_to_pandas(csvpath, md_path, return_md=True, verbosity=1)
        self.assertEqual(len(md._warnings), 5)  # 5 virtual fields
        # Compare against known correct result (not from csvw project)
        self.assertDataFrameCorrect(df, resultspath, type_matching='loose')

    # def test033(self):
    #     pass  # same as 32 for our purposes

    def test034(self):
        test = this_function_name()
        f = self.fullpath
        pqp = self.parquet_path
        md_path = f(f'{test}/csv-metadata.json')
        sdf, md = csv_to_pandas(
            f(f'{test}/senior-roles.csv'),
            md_path,
            use_table_name=True,
            upgrade_possible_ints=True,
            return_md=True,
            verbosity=1,
        )
        self.assertDataFrameCorrect(
            sdf, pqp(f'{test}-senior-roles.parquet'), type_matching='loose'
        )

        jdf = csv_to_pandas(
            f(f'{test}/junior-roles.csv'),
            md_path,
            use_table_name=True,
            upgrade_possible_ints=True,
            verbosity=1,
        )
        self.assertDataFrameCorrect(
            jdf, pqp(f'{test}-junior-roles.parquet'), type_matching='loose'
        )

        pdf = csv_to_pandas(
            f(f'{test}/gov.uk/data/professions.csv'),
            md_path,
            use_table_name=True,
            upgrade_possible_ints=True,
            verbosity=1,
        )
        self.assertDataFrameCorrect(
            pdf, pqp(f'{test}-professions.parquet'), type_matching='loose'
        )

        odf = csv_to_pandas(
            f(f'{test}/gov.uk/data/organizations.csv'),
            md_path,
            use_table_name=True,
            upgrade_possible_ints=True,
            verbosity=1,
        )
        self.assertDataFrameCorrect(
            odf, pqp(f'{test}-organizations.parquet'), type_matching='loose'
        )

    # def test035(self):
    #     pass  # same as 34 for our purposes

    def test036(self):
        test = this_function_name()
        csvpath = self.fullpath(f'{test}/tree-ops-ext.csv')
        resultspath = self.parquet_path(f'{test}-result.parquet')
        # md is this:
        # md = load_metadata(
        #     self.fullpath(f'{test}/tree-ops-ext.csv-metadata.json')
        # )
        df = csv_to_pandas(csvpath, find_md=True, verbosity=1)
        self.assertDataFrameCorrect(df, resultspath, type_matching='loose')

    def _test_csv_json(self, stem, upgrade_possible_ints=False, to_ints=None):
        csvpath, resultspath = self.csv_json_paths(stem)
        df = csv_to_pandas(
            csvpath, upgrade_possible_ints=upgrade_possible_ints
        )
        fields = fields_from(csvpath)
        ref_df = csvw_json_to_df(resultspath, fields, to_ints=to_ints)
        # self.assertDataFramesEqual(df, ref_df)


class TestPandasFlatFileRoundTrips(ReferenceTestCase):
    def testDefault(self):
        df = testDataset4()
        path = tmppath('ds4-pandas-defaults.csv')
        pandas_write_csv(df, path)

        md_path = metadata_path(path)
        with open(md_path, 'r') as f:
            md = f.read()
        self.assertFileCorrect(
            md_path,
            tdpath('ds4-pandas-defaults.serial'),
            ignore_patterns=TDDASERIAL_PATTERNS,
        )

        df2 = pandas_read_csv(path)
        self.assertDataFramesEquivalent(df, df2, type_matching='medium')

        df3 = pandas_read_csv(path, md_path=md_path)
        self.assertDataFramesEquivalent(df, df3, type_matching='medium')

        str_t = 'str' if pd3 else 'object'
        dt_t = f'datetime64[{"us" if pd3 else "ns"}]'
        alt_md_path = tdpath('ds4-pandas-alt.serial')
        df4 = pandas_read_csv(path, md_path=alt_md_path)
        dtypes = {k: str(df4[k].dtype) for k in df4}
        self.assertEqual(
            dtypes,
            {
                'row': 'float64',
                'b': 'object',
                'i': 'float64',
                'I': 'string',
                'r': 'object',
                's': str_t,
                'nulllike': str_t,
                'd': dt_t,
                'dt': dt_t,
            },
        )

    def testMetadataGeneration_tinycd(self):
        # Write metadata for tiny complete (c: no nulls), default types (d)
        df = tiny_pandas_df(nulls=False, nullable_types=False)
        csv_path = tmppath('tiny1cd3.csv')
        md_path = tmppath('tiny1cd3.serial')
        pandas_to_csv(df, csv_path, md_outpath=md_path, flavour=THREE_FLAVOURS)

        # Right CSV written
        self.assertFileCorrect(csv_path, tdpath('tiny1cd3.csv'))

        # Right metadata written
        self.assertFileCorrect(
            md_path,
            tdpath('tiny1cd3.serial'),
            ignore_patterns=TDDASERIAL_PATTERNS,
        )

        pandas_to_csv(df, csv_path, md_outpath=md_path, flavour='tdda.serial')
        self.assertFileCorrect(csv_path, tdpath('tiny1cd.csv'))
        self.assertFileCorrect(
            md_path,
            tdpath('tiny1cd.serial'),
            ignore_patterns=TDDASERIAL_PATTERNS,
        )

        pandas_to_csv(df, csv_path, md_outpath=md_path, flavour=PANDAS2)
        self.assertFileCorrect(csv_path, tdpath('tiny1cd-pandas.csv'))
        self.assertFileCorrect(
            md_path,
            tdpath('tiny1cd-pandas.serial'),
            ignore_patterns=TDDASERIAL_PATTERNS,
        )

        # Read back correctly using various metadata in .serial file

        dfa = csv_to_pandas(
            tdpath('tiny1cd3.csv'),
            md_path=tdpath('tiny1cd3.serial'),
            upgrade_types=False,
            preferred='pandas.read_csv',
        )

        self.assertDataFramesEquivalent(dfa, df, fuzzy_nulls=True)

        dfa = csv_to_pandas(
            tdpath('tiny1cd3.csv'),
            md_path=tdpath('tiny1cd3.serial'),
            upgrade_types=False,
            preferred='tdda.serial',
        )
        self.assertDataFramesEquivalent(dfa, df, fuzzy_nulls=True)

        dfa = csv_to_pandas(
            tdpath('tiny1cd-pandas.csv'),
            md_path=tdpath('tiny1cd-pandas.serial'),
            upgrade_types=False,
        )
        self.assertDataFramesEquivalent(dfa, df, fuzzy_nulls=True)

    def testMetadataGeneration_tinynd(self):
        # Write metadata for tiny with nulls (n), default types (d)
        df = tiny_pandas_df(nulls=True, nullable_types=False)
        csv_path = tmppath('tiny1nd3.csv')
        md_path = tmppath('tiny1nd3.serial')

        pandas_to_csv(df, csv_path, md_outpath=md_path, flavour=THREE_FLAVOURS)
        self.assertFileCorrect(csv_path, tdpath('tiny1nd3.csv'))
        self.assertFileCorrect(
            md_path,
            tdpath('tiny1nd3.serial'),
            ignore_patterns=TDDASERIAL_PATTERNS,
        )

        pandas_to_csv(df, csv_path, md_outpath=md_path, flavour='tdda.serial')
        self.assertFileCorrect(csv_path, tdpath('tiny1nd-pandas.csv'))
        self.assertFileCorrect(
            md_path,
            tdpath('tiny1nd-i-as-float.serial'),
            ignore_patterns=TDDASERIAL_PATTERNS,
        )

        pandas_to_csv(df, csv_path, md_outpath=md_path, flavour=PANDAS2)
        self.assertFileCorrect(csv_path, tdpath('tiny1nd-pandas.csv'))
        self.assertFileCorrect(
            md_path,
            tdpath('tiny1nd-pandas.serial'),
            ignore_patterns=TDDASERIAL_PATTERNS,
        )

        # Read back correctly using various metadata in .serial file

        dfa = csv_to_pandas(
            tdpath('tiny1nd3.csv'),
            md_path=tdpath('tiny1nd3.serial'),
            upgrade_types=False,
            preferred='pandas.read_csv',
        )
        self.assertDataFramesEquivalent(dfa, df, fuzzy_nulls=True)

        dfa = csv_to_pandas(
            tdpath('tiny1nd3.csv'),
            md_path=tdpath('tiny1nd3.serial'),
            upgrade_types=False,
            preferred='tdda.serial',
        )
        self.assertDataFramesEquivalent(dfa, df, fuzzy_nulls=True)

        dfa = csv_to_pandas(
            tdpath('tiny1nd3.csv'),
            md_path=tdpath('tiny1nd-pandas.serial'),
            upgrade_types=False,
        )
        self.assertDataFramesEquivalent(dfa, df, fuzzy_nulls=True)

    def testMetadataGeneration_tinycn(self):
        # Write metadata for tiny complete (c: no nulls), nullable types (n)
        df = tiny_pandas_df(nulls=False, nullable_types=True)
        csv_path = tmppath('tiny1cn3.csv')
        md_path = tmppath('tiny1cn3.serial')
        pandas_to_csv(
            df,
            csv_path,
            md_outpath=md_path,
            flavour=THREE_FLAVOURS,
            index=True,
        )
        self.assertFileCorrect(csv_path, tdpath('tiny1cn3.csv'))
        self.assertFileCorrect(
            md_path,
            tdpath('tiny1cn3.serial'),
            ignore_patterns=TDDASERIAL_PATTERNS,
        )

        pandas_to_csv(
            df,
            csv_path,
            md_outpath=md_path,
            flavour=['tdda.serial'],
            index=True,
        )
        self.assertFileCorrect(csv_path, tdpath('tiny1cn.csv'))
        self.assertFileCorrect(
            md_path,
            tdpath('tiny1cn.serial'),
            ignore_patterns=TDDASERIAL_PATTERNS,
        )

        pandas_to_csv(
            df, csv_path, md_outpath=md_path, flavour=PANDAS2, index=True
        )
        self.assertFileCorrect(csv_path, tdpath('tiny1cn-pandas.csv'))
        self.assertFileCorrect(
            md_path,
            tdpath('tiny1cn-pandas.serial'),
            ignore_patterns=TDDASERIAL_PATTERNS,
        )

        # Read back correctly using various metadata in .serial file

        dfa = csv_to_pandas(
            tdpath('tiny1cn3.csv'),
            md_path=tdpath('tiny1cn3.serial'),
            upgrade_types=False,
            preferred='pandas.read_csv',
        )
        self.assertDataFramesEquivalent(dfa, df, fuzzy_nulls=True)

        dfa = csv_to_pandas(
            tdpath('tiny1cn3.csv'),
            md_path=tdpath('tiny1cn3.serial'),
            upgrade_types=False,
            preferred='tdda.serial',
        )
        self.assertDataFramesEquivalent(dfa, df, fuzzy_nulls=True)

        dfa = csv_to_pandas(
            tdpath('tiny1cn3.csv'),
            md_path=tdpath('tiny1cn-pandas.serial'),
            upgrade_types=False,
        )
        self.assertDataFramesEquivalent(dfa, df, fuzzy_nulls=True)

    def testMetadataGeneration_tinynn(self):
        # Write metadata for tiny with nulls (n), nullable types (n)
        df = tiny_pandas_df(nulls=True, nullable_types=True)
        csv_path = tmppath('tiny1nn3.csv')
        md_path = tmppath('tiny1nn3.serial')
        pandas_to_csv(df, csv_path, md_outpath=md_path, flavour=THREE_FLAVOURS)
        self.assertFileCorrect(csv_path, tdpath('tiny1nn3.csv'))
        self.assertFileCorrect(
            md_path,
            tdpath('tiny1nn3.serial'),
            ignore_patterns=TDDASERIAL_PATTERNS,
        )

        pandas_to_csv(df, csv_path, md_outpath=md_path, flavour='tdda.serial')
        self.assertFileCorrect(csv_path, tdpath('tiny1nn.csv'))
        self.assertFileCorrect(
            md_path,
            tdpath('tiny1nn.serial'),
            ignore_patterns=TDDASERIAL_PATTERNS,
        )

        pandas_to_csv(df, csv_path, md_outpath=md_path, flavour=PANDAS2)
        self.assertFileCorrect(csv_path, tdpath('tiny1nn-pandas.csv'))
        self.assertFileCorrect(
            md_path,
            tdpath('tiny1nn-pandas.serial'),
            ignore_patterns=TDDASERIAL_PATTERNS,
        )

        # Read back correctly using various metadata in .serial file

        dfa = csv_to_pandas(
            tdpath('tiny1nn3.csv'),
            md_path=tdpath('tiny1nn3.serial'),
            upgrade_types=False,
            preferred='pandas.read_csv',
        )
        self.assertDataFramesEquivalent(dfa, df, fuzzy_nulls=True)

        dfa = csv_to_pandas(
            tdpath('tiny1nn3.csv'),
            md_path=tdpath('tiny1nn3.serial'),
            upgrade_types=False,
            preferred='tdda.serial',
        )
        self.assertDataFramesEquivalent(dfa, df, fuzzy_nulls=True)

        dfa = csv_to_pandas(
            tdpath('tiny1nn3.csv'),
            md_path=tdpath('tiny1nn-pandas.serial'),
            upgrade_types=False,
        )
        self.assertDataFramesEquivalent(dfa, df, fuzzy_nulls=True)


class TestPandasParquetRoundTrips(ReferenceTestCase):
    # Really checking diff_dataframes more than parquet
    # But also confirming that round-tripping is working
    # for Pandas via parquet
    def testTinyParquetCD(self):
        df = tiny_pandas_df(nulls=False, nullable_types=False)
        path = tmppath('tiny1cd.parquet')
        df.to_parquet(path)
        df2 = pd.read_parquet(path)
        self.assertEqual(diff_dataframes(df2, df).failures, 0)

    def testTinyParquetCN(self):
        df = tiny_pandas_df(nulls=False, nullable_types=True)
        path = tmppath('tiny1cn.parquet')
        df.to_parquet(path)
        df2 = pd.read_parquet(path)
        self.assertEqual(diff_dataframes(df2, df).failures, 0)

    def testTinyParquetND(self):
        df = tiny_pandas_df(nulls=True, nullable_types=False)
        path = tmppath('tiny1cd.parquet')
        df.to_parquet(path)
        df2 = pd.read_parquet(path)
        self.assertEqual(diff_dataframes(df2, df).failures, 0)

    def testTinyParquetNN(self):
        df = tiny_pandas_df(nulls=True, nullable_types=True)
        path = tmppath('tiny1cn.parquet')
        df.to_parquet(path)
        df2 = pd.read_parquet(path)
        diffs = diff_dataframes(df2, df, create_temporaries=False)
        self.assertEqual(diff_dataframes(df2, df).failures, 0)

    def testTinyParquetSmallWideD(self):
        df, _ = small_wide_pd_df()
        path = tmppath('small_wide-d.parquet')
        df.to_parquet(path)
        df2 = pd.read_parquet(path)
        diffs = diff_dataframes(df2, df, create_temporaries=False)
        self.assertEqual(diffs.failures, 1)  # types
        msg = str(diffs.diffs)
        self.assertTrue(
            msg.startswith('Data frames have different column structure.')
        )
        diffs2 = diff_dataframes(df2, df, type_matching='medium')
        self.assertEqual(diffs2.failures, 0)

    def testTinyParquetSmallWideN(self):
        df, _ = small_wide_pd_df()
        path = tmppath('small_wide-n.parquet')
        df.to_parquet(path)
        df2 = pd.read_parquet(path)
        diffs = diff_dataframes(df2, df, create_temporaries=False)
        self.assertEqual(diffs.failures, 1)  # types
        msg = str(diffs.diffs)
        self.assertTrue(
            msg.startswith('Data frames have different column structure.')
        )

        diffs2 = diff_dataframes(df2, df, type_matching='medium')
        self.assertEqual(diffs2.failures, 0)


class TestPandasToMetadata(ReferenceTestCase):
    def testSimpleDtypeFieldtypeMapping(self):
        # WITH col passed in, prefer nullable types (defaults)

        df, expected_types = small_wide_pd_df()
        actual = {
            col: pandas_dtype_to_fieldtype(df[col].dtype, df[col])
            for col in df
        }
        remove_common_key_vals(actual, expected_types)
        self.assertEqual(actual, expected_types)
        self.assertEqual(actual, {})

    def testSimpleDtypeFieldtypeMappingNoValues(self):
        # WITHOUT col passed in

        df, expected_types = small_wide_pd_df(with_col=False)
        actual = {col: pandas_dtype_to_fieldtype(df[col].dtype) for col in df}

        remove_common_key_vals(actual, expected_types)
        self.assertEqual(actual, expected_types)
        self.assertEqual(actual, {})

    def testSimpleDtypeFieldtypeMappingNotPreferNullable(self):
        # WITHOUT preferring nullable types:

        df, expected_types = small_wide_pd_df()
        actual = {
            col: pandas_dtype_to_fieldtype(df[col].dtype, df[col])
            for col in df
        }

        # Similarly, with no values, the whole-number floats
        # remain as floats

        remove_common_key_vals(actual, expected_types)
        self.assertEqual(actual, expected_types)
        self.assertEqual(actual, {})

    def testMetadataGeneration(self):
        df, _ = small_wide_pd_df(with_col=False)
        m = pandas_df_to_metadata(df, flavours='tdda.serial')
        self.assertStringCorrect(
            str(m),
            tdpath('small-wide.serial'),
            ignore_patterns=TDDASERIAL_PATTERNS,
        )


def testDataset4():
    return pd.DataFrame(
        {
            'row': [1, 2, 3, 4, 5],
            'b': [True, False, None, False, True],
            'i': [-1, 0, 1, None, None],
            'I': pd.Series([-1, 0, 1, None, None], dtype='Int64'),
            'r': [-1.25e-37, -1, None, +1, 1.25e37],
            's': [None, 'one', 'Nöel', """(ΑΒΓΔ φχψω "❤️‍🩹" '✔' \n \\)""", ' '],
            'nulllike': [None, 'NULL', 'NA', 'N/A', 'na'],
            'd': [
                datetime.date(1969, 12, 31),
                datetime.date(1970, 1, 1),
                datetime.date(2040, 2, 28),
                datetime.date(2040, 2, 29),
                None,
            ],
            'dt': [
                datetime.datetime(1969, 12, 31, 23, 59, 59),
                datetime.datetime(1970, 1, 1, 0, 0, 0),
                datetime.datetime(1999, 12, 31, 23, 59, 59),
                datetime.datetime(2038, 12, 31, 23, 59, 59),
                None,
            ],
        }
    )


testDataset4.__test__ = False


def csvw_json_to_df(path, fields, table_number=0, to_ints=None):
    with open(path) as f:
        d = json.load(f)
    rows = d['tables'][table_number]['row']
    df = pd.DataFrame(
        {
            field: [r['describes'][0].get(field, None) for r in rows]
            for field in fields
        }
    )
    for k in to_ints or []:
        string_to_int(df, k)
    return df


def csvw_bare_json_to_df(path, fields, to_ints=None, to_dates=None):
    with open(path) as f:
        d = json.load(f)
    rows = d
    df = pd.DataFrame(
        {field: [r.get(field, None) for r in rows] for field in fields}
    )
    for k in to_ints or []:
        string_to_int(df, k)
    for k in to_dates or []:
        df[k] = pd.to_datetime(df[k])
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


def small_wide_pd_df(with_col=True):
    """
    Generates a dataframe and its expected types.
    """
    df = pd.DataFrame(
        {
            'null': pd.Series([None] * 3, dtype='O'),
            'inull': pd.Series([None] * 3, dtype='Int64'),
            'bnull': pd.Series([None] * 3, dtype='boolean'),
            'fnull': pd.Series([None] * 3, dtype='float'),
            'bn': pd.Series([True, False, None], dtype='O'),
            'b': [True, False, True],
            'B': pd.Series([True, False, None], dtype='boolean'),
            'in': [1, -1, None],
            'i': [1, -1, 0],
            'I': pd.Series([1, -1, None], dtype='Int64'),
            'U': pd.Series([1, 0, None], dtype='UInt64'),
            'un': pd.Series([1, 2, None], dtype='float'),
            'fn': [1.5, 2.0, None],
            'f': [1.5, 2.0, 3.0],
            'Fn': [1.0, 2.0, None],
            'F': [1.0, 2.0, 3.0],
            's': list('abc'),
            'sn': ['a', 'b', None],
            'd': [datetime.date(2025, 1, day) for day in range(1, 4)],
            'dn': [datetime.date(2025, 1, day) for day in range(1, 3)]
            + [None],
            'dt': [
                datetime.datetime(2025, 12, 31, 23, 59, s)
                for s in range(57, 60)
            ],
            'dtn': [
                datetime.datetime(2025, 12, 31, 23, 59, s)
                for s in range(58, 60)
            ]
            + [None],
            'dz': [
                datetime.datetime(
                    2025,
                    12,
                    31,
                    23,
                    59,
                    59,
                    tzinfo=datetime.timezone(
                        datetime.timedelta(seconds=3600 * delta)
                    ),
                )
                for delta in (-1, 0, 1)
            ],
            # 'dzn': [datetime.datetime(2025, 12, 31, 23, 59, 59,
            #                           tzinfo=datetime.timezone(
            #                              datetime.timedelta(seconds=3600 * delta)))
            #         for delta in (-1, 1)] + [None],
            'dzn': [
                datetime.datetime.now(
                    datetime.timezone(datetime.timedelta(seconds=3600))
                )
            ]
            * 2
            + [None],
        }
    )

    types = {
        'null': FieldType.STRING,
        'inull': FieldType.INT,
        'bnull': FieldType.BOOL,
        'fnull': FieldType.FLOAT,
        'bn': FieldType.BOOL,
        'b': FieldType.BOOL,
        'B': FieldType.BOOL,
        'in': FieldType.INT,
        'i': FieldType.INT,
        'I': FieldType.INT,
        'U': FieldType.INT,
        'un': FieldType.INT,
        'Fn': FieldType.INT,
        'F': FieldType.INT,
        'fn': FieldType.FLOAT,
        'f': FieldType.FLOAT,
        's': FieldType.STRING,
        'sn': FieldType.STRING,
        'd': FieldType.DATE,
        'dn': FieldType.DATE,
        'dt': FieldType.DATETIME,
        'dtn': FieldType.DATETIME,
        'dz': FieldType.DATETIME,
        'dzn': FieldType.DATETIME_WITH_TIMEZONE,
    }

    if not with_col:
        # With no values, all the object fields become strings
        for k in ('bn', 'dn', 'd', 'dz'):
            types[k] = FieldType.STRING

    # Similarly, with no values, or of not prefer_nullable
    # the whole-number floats
    # remain as float
    #    if not with_col:
    if True:
        for k in ('F', 'Fn', 'un', 'in'):
            types[k] = FieldType.FLOAT

    return (df, types)


def remove_common_key_vals(left, right):
    for k in list(left.keys()):
        if left[k] == right[k]:
            del left[k]
            del right[k]


class TestSerialPandasKwargsNamedDateFormats(ReferenceTestCase):
    """
    Tests that serial_to_pandas_read_csv_args produces correct pandas
    date_format kwargs when SerialMetadata uses named date formats.
    """

    def _md(self, fieldtype, fmt):
        """Build a minimal SerialMetadata with one date field."""
        field = FieldMetadata('d', fieldtype=fieldtype, format=fmt)
        return SerialMetadata(fields=[field])

    def test_serial_iso8601_date_kwargs_read(self):
        # ISO8601 named formats → 'ISO8601' on read
        kw = serial_to_pandas_read_csv_args(
            self._md('date', DateFormat.ISO8601_DATE)
        )
        self.assertEqual(kw['date_format'], {'d': 'ISO8601'})

    def test_serial_iso8601_datetime_kwargs_read(self):
        kw = serial_to_pandas_read_csv_args(
            self._md('datetime', DateFormat.ISO8601_DATETIME)
        )
        self.assertEqual(kw['date_format'], {'d': 'ISO8601'})

    def test_serial_dataset_date_format_iso8601(self):
        # dataset-level iso8601 → 'ISO8601' on read
        field = FieldMetadata('d', fieldtype='date')
        md = SerialMetadata(
            fields=[field], date_format=DateFormat.ISO8601_UNSPECIFIED
        )
        kw = serial_to_pandas_read_csv_args(md)
        self.assertEqual(kw['date_format'], {'d': 'ISO8601'})

    def test_serial_allformats2unspec_kwargs(self):
        # Fields with no per-field format fall back to dataset-level
        # date_format (eu-date) and datetime_format (eu-datetime).
        # All other fields have explicit per-field formats.
        md = load_metadata(tdpath('allformats2unspec.serial'))
        kw = serial_to_pandas_read_csv_args(md)
        self.assertEqual(
            kw['date_format'],
            {
                'eu_date': '%d/%m/%Y',
                'eu_date_2y': '%d/%m/%y',
                'iso_date': 'ISO8601',
                'us_date': '%m/%d/%Y',
                'us_date_2y': '%m/%d/%y',
                'eu_datetime': '%d/%m/%Y %H:%M:%S',
                'eu_datetime_2y': '%d/%m/%y %H:%M:%S',
                'iso_datetime': 'ISO8601',
                'us_datetime': '%m/%d/%Y %H:%M:%S',
                'us_datetime_2y': '%m/%d/%y %H:%M:%S',
                'udate': '%d/%m/%Y',
                'udatetime': '%d/%m/%Y %H:%M:%S',
            },
        )


class TestSerialPandasNamedDateFormatsLoad(ReferenceTestCase):
    """
    Integration tests: load CSVs via .serial metadata with named
    euro/US date formats. Both parse to the same datetime values,
    verified against a shared reference parquet.
    """

    def test_iso_date_serial(self):
        df = csv_to_pandas(tdpath('isod.csv'), tdpath('isod.serial'))
        self.assertDataFrameCorrect(df, tdpath('dated.parquet'))

    def test_eu_date_serial(self):
        df = csv_to_pandas(tdpath('eurod.csv'), tdpath('eurod.serial'))
        self.assertDataFrameCorrect(df, tdpath('dated.parquet'))

    def test_us_date_serial(self):
        df = csv_to_pandas(tdpath('usd.csv'), tdpath('usd.serial'))
        self.assertDataFrameCorrect(df, tdpath('dated.parquet'))

    def test_eu_date2y_serial(self):
        df = csv_to_pandas(tdpath('eurod2y.csv'), tdpath('eurod2y.serial'))
        self.assertDataFrameCorrect(df, tdpath('dated.parquet'))

    def test_us_date2y_serial(self):
        df = csv_to_pandas(tdpath('usd2y.csv'), tdpath('usd2y.serial'))
        self.assertDataFrameCorrect(df, tdpath('dated.parquet'))

    def test_iso_datetime_serial(self):
        df = csv_to_pandas(
            tdpath('isodatetime.csv'), tdpath('isodatetime.serial')
        )
        self.assertDataFrameCorrect(df, tdpath('datetimed.parquet'))

    def test_eu_datetime_serial(self):
        df = csv_to_pandas(tdpath('eurodt.csv'), tdpath('eurodt.serial'))
        self.assertDataFrameCorrect(df, tdpath('datetimed.parquet'))

    def test_us_datetimeserial(self):
        df = csv_to_pandas(tdpath('usdt.csv'), tdpath('usdt.serial'))
        self.assertDataFrameCorrect(df, tdpath('datetimed.parquet'))

    def test_eu_datetime2y_serial(self):
        df = csv_to_pandas(tdpath('eurodt2y.csv'), tdpath('eurodt2y.serial'))
        self.assertDataFrameCorrect(df, tdpath('datetimed.parquet'))

    def test_us_datetime2y_serial(self):
        df = csv_to_pandas(tdpath('usdt2y.csv'), tdpath('usdt2y.serial'))
        self.assertDataFrameCorrect(df, tdpath('datetimed.parquet'))

    def test_us_allformats2unspec_serial(self):
        df = csv_to_pandas(
            tdpath('allformats2unspec.csv'), tdpath('allformats2unspec.serial')
        )
        self.assertDataFrameCorrect(
            df, tdpath('alldateformats2unspec.parquet'), type_matching='loose'
        )


class TestSerialPandasNamedDateFormatsWrite(ReferenceTestCase):
    """
    Integration tests: write DataFrames via pandas_to_csv with euro date
    formats, both via kw_overrides and via an input .serial file.
    Verify that the written CSV and companion .serial file are correct.
    """

    def test_write_eu_datetime_via_kwargs(self):
        df = pd.read_parquet(tdpath('datetimed.parquet'))
        csv_path = tmppath('eurodt-write-kw.csv')
        md_path = tmppath('eurodt-write-kw.serial')
        pandas_to_csv(
            df, csv_path, md_outpath=md_path, date_format='%d/%m/%Y %H:%M:%S'
        )
        self.assertFileCorrect(csv_path, tdpath('eurodt-write-kw.csv'))
        self.assertFileCorrect(
            md_path,
            tdpath('eurodt-write-kw.serial'),
            ignore_patterns=TDDASERIAL_PATTERNS,
        )

    def test_write_eu_datetime_via_serial(self):
        df = pd.read_parquet(tdpath('datetimed.parquet'))
        csv_path = tmppath('eurodt-write-serial.csv')
        md_path = tmppath('eurodt-write-serial.serial')
        pandas_to_csv(
            df, csv_path, md_inpath=tdpath('eurodt.serial'), md_outpath=md_path
        )
        self.assertFileCorrect(csv_path, tdpath('eurodt-write-serial.csv'))
        self.assertFileCorrect(
            md_path,
            tdpath('eurodt-write-serial.serial'),
            ignore_patterns=TDDASERIAL_PATTERNS,
        )


class TestSerialPandasSmallWrite(ReferenceTestCase):
    """
    Integration tests: write a multi-type DataFrame (read from small.csv)
    via pandas_to_csv with tab delimiter, single-quote char, and NULL
    null marker — both via kw_overrides and via an input .serial file.
    Verify that the written CSV and companion .serial file are correct.
    """

    def test_write_small_via_kwargs(self):
        df = csv_to_pandas(tdpath('small.csv'), md_path=tdpath('small.serial'))
        csv_path = tmppath('small-write-kw.csv')
        md_path = tmppath('small-write-kw.serial')
        pandas_to_csv(
            df,
            csv_path,
            md_outpath=md_path,
            sep='\t',
            quotechar="'",
            na_rep='NULL',
        )
        self.assertFileCorrect(csv_path, tdpath('small-write-kw.csv'))
        self.assertFileCorrect(
            md_path,
            tdpath('small-write-kw.serial'),
            ignore_patterns=TDDASERIAL_PATTERNS,
        )

    def test_write_small_via_serial(self):
        df = csv_to_pandas(tdpath('small.csv'), md_path=tdpath('small.serial'))
        csv_path = tmppath('small-write-serial.csv')
        md_path = tmppath('small-write-serial.serial')
        pandas_to_csv(
            df,
            csv_path,
            md_inpath=tdpath('small-write-tsv.serial'),
            md_outpath=md_path,
        )
        self.assertFileCorrect(csv_path, tdpath('small-write-serial.csv'))
        self.assertFileCorrect(
            md_path,
            tdpath('small-write-serial.serial'),
            ignore_patterns=TDDASERIAL_PATTERNS,
        )

    def test_all_date_formats_working(self):
        df = csv_to_pandas(tdpath('allformats.csv:'))
        pcdf = csv_to_pandas(
            tdpath('allformats.csv'), tdpath('allformats-pc.serial')
        )
        ldf = csv_to_pandas(
            tdpath('allformats.csv'), tdpath('allformats-literal.serial')
        )
        self.assertDataFramesEquivalent(pcdf, df, type_matching='strict')
        self.assertDataFramesEquivalent(ldf, df, type_matching='strict')


class TestSerialPandasAlternateBooleans(ReferenceTestCase):
    """
    Tests for alternate boolean values at field level and dataset level.
    """

    def test_alternate_booleans_pandas(self):
        df = csv_to_pandas(
            tdpath('bools.csv'), tdpath('bools.serial'), backend='n'
        )
        self.assertDataFrameCorrect(df, tdpath('bools.parquet'))


class TestPandasWritePython(ReferenceTestCase):
    """
    Tests for serial_to_pandas_write_csv_python.

    Each test:
    1. Loads metadata from a .serial file
    2. Generates Python write code and checks it against a reference .py
    3. Executes the generated Python and writes a CSV to a temp path
    4. Checks the written CSV against a reference file
    """

    def _run(self, serial_path, csv_path, ref_py, ref_csv,
             expected_warnings=None):
        md = load_metadata(serial_path)
        warn, buf = testwarn()
        py = serial_to_pandas_write_csv_python(md, warner=warn)
        if expected_warnings is not None:
            self.assertEqual(buf, expected_warnings)
        self.assertStringCorrect(py, ref_py)
        df = csv_to_pandas(csv_path, serial_path)
        ns = {}
        exec(py, ns)
        out = tmppath(os.path.basename(ref_csv))
        ns['write_data'](df, out)
        self.assertFileCorrect(out, ref_csv)

    def test_write_py_weird(self):
        self._run(
            tdpath('tiny1nd-weird.serial'),
            tdpath('tiny1nd-weird.ssv'),
            tdpath('tiny1nd-weird-write-pd.py'),
            tdpath('tiny1nd-weird-write-pd.ssv'),
            expected_warnings=[
                'Boolean formats cannot be expressed in'
                ' pandas.DataFrame.to_csv;'
                ' booleans will be written as True/False.'
            ],
        )

    def test_write_py_a1k_mixed(self):
        self._run(
            tdpath('a10-mixed.csv.serial'),
            tdpath('a10-mixed.csv'),
            tdpath('a10-mixed-write-pd.py'),
            tdpath('a10-mixed-write-pd.csv'),
            expected_warnings=[
                'Boolean formats cannot be expressed in'
                ' pandas.DataFrame.to_csv;'
                ' booleans will be written as True/False.',
                'Multiple data formats; using ISO 8601.',
            ],
        )


class TestPandasToCSV(ReferenceTestCase):

    def test_write_csv_no_metadata(self):
        out = tmppath('tiny1cd-pd.csv')
        pandas_to_csv(tiny_pandas_df(), out, index=False)
        self.assertFileCorrect(out, tdpath('tiny1cd-pd.csv'))

    def test_write_csv_with_md_out(self):
        out = tmppath('tiny1cd-pd.csv')
        md_out = tmppath('tiny1cd-pd.serial')
        pandas_to_csv(tiny_pandas_df(), out, md_outpath=md_out, index=False)
        self.assertFileCorrect(out, tdpath('tiny1cd-pd.csv'))
        self.assertFileCorrect(
            md_out,
            tdpath('tiny1cd-pd.serial'),
            ignore_patterns=TDDASERIAL_PATTERNS,
        )

    def test_write_csv_with_md_in(self):
        out = tmppath('tiny1cd-pd-from-serial.csv')
        pandas_to_csv(
            tiny_pandas_df(), out, md_inpath=tdpath('tiny1cd.serial'),
            index=False,
        )
        self.assertFileCorrect(out, tdpath('tiny1cd-pd-from-serial.csv'))

    def test_round_trip_null_value(self):
        # With default na_rep='', null and '' are both written as ""
        # so '' comes back as null on read. Known pandas limitation.
        out = tmppath('tiny1cd-pd-rt.csv')
        md_out = tmppath('tiny1cd-pd-rt.serial')
        pandas_to_csv(tiny_pandas_df(), out, md_outpath=md_out, index=False)
        df2 = csv_to_pandas(out, md_out)
        expected = tiny_pandas_df().copy()
        expected['s'] = expected['s'].where(expected['s'] != '', other=None)
        self.assertDataFramesEqual(expected, df2, type_matching='medium')

    def test_round_trip_safe_null(self):
        out = tmppath('tiny1cd-pd-rt-null.csv')
        md_out = tmppath('tiny1cd-pd-rt-null.serial')
        pandas_to_csv(
            tiny_pandas_df(), out, md_outpath=md_out,
            index=False, na_rep='NULL',
        )
        df2 = csv_to_pandas(out, md_out)
        self.assertDataFramesEqual(tiny_pandas_df(), df2, type_matching='medium')


if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
