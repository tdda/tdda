import os
import re

import pandas
import polars

from collections import namedtuple

from tdda.referencetest import ReferenceTestCase, tag

from tdda.serial import csv_to_pandas, csv_to_polars
from tdda.serial.converter import SerialConverter
from tdda.serial.csvw import CSVWMetadata, serial_to_csvw
from tdda.serial.frictionless import (
    FrictionlessMetadata,
)
from tdda.serial.metadata import FieldType
from tdda.serial.dateutils import (
    AmbiguousDateFormat,
    DateRE,
    Separators,
    get_date_separators,
    infer_date_format_from_strings,
)
from tdda.serial.infer import (
    NO_DELIMITER,
    FirstLineStats,
    analyse_values,
    careful_split,
    infer_format_from_flat_file,
    read_file_lines,
)
from tdda.serial.reader import load_metadata
from tdda.utils import TDDAError, nvl


from tdda.serial.testserial import (
    tdpath,
    tmppath,
    REFTESTDATA,
)


from tdda.utils import testwarn

TDDA_SERIAL_VERSION_RE = r'tdda\.serial\-[0-9]+.[0-9]+\.[0-9]+[rc0-9]*'

Spec = namedtuple('Spec', 'generate formats broad_out inpath outpath')


class TestInference(ReferenceTestCase):
    tiny1nd_serial = tdpath('tiny1nd.serial')
    weird_serial = tdpath('tiny1nd-weird.serial')
    IGL = ['tdda.serial-', 'writer']

    def infer(self, path, **kw):
        Warn, buf = testwarn()
        md = infer_format_from_flat_file(path, warner=Warn, **kw)
        return md, buf

    def check_infer(self, name, prov=False, ignore_patterns=None, **kw):
        base, ext = os.path.splitext(name)
        stem = base if ext == '.csv' else base + '-' + ext[1:]
        suffix = '-prov-inferred.serial' if prov else '-inferred.serial'
        outname = stem + suffix
        Warn, buf = testwarn()
        md = infer_format_from_flat_file(
            tdpath(name), warner=Warn, raise_error=True, **kw
        )
        outpath = tmppath(outname)
        with open(outpath, 'w') as f:
            f.write(md.to_json())
        self.assertFileCorrect(
            outpath,
            tdpath(outname),
            ignore_lines=self.IGL,
            ignore_patterns=ignore_patterns,
        )
        return buf, md

    def testInferMetadataTiny1cdq(self):
        md, buf = self.infer(
            tdpath('tiny1ndq.csv'), verbosity=0, add_defaults=True
        )
        self.assertStringCorrect(
            md.to_json(),
            tdpath('tiny1ndq-with-defaults-inferred.serial'),
            ignore_lines=self.IGL,
        )

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

    def testInferMetadataWeird(self):
        md, buf = self.infer(
            tdpath('tiny1nd-weird.ssv'), verbosity=0, add_defaults=True
        )
        self.assertStringCorrect(
            md.to_json(),
            tdpath('tiny1nd-weird-with-defaults-inferred.serial'),
            ignore_lines=self.IGL,
        )

    def testInferMetadataSimple(self):
        md, buf = self.infer(
            tdpath('simple.csv'), verbosity=0, add_defaults=True
        )
        self.assertStringCorrect(
            md.to_json(),
            tdpath('simple-with-defaults-inferred.serial'),
            ignore_lines=self.IGL,
        )
        self.assertEqual(
            buf,
            [
                "encoding: 'UTF-8' (default, no evidence)",
                "quote_char: '\"' (default, no evidence)",
            ],
        )

    def testInferMetadataMinimal(self):
        md, buf = self.infer(
            tdpath('minimal.csv'), verbosity=0, add_defaults=True
        )
        self.assertStringCorrect(
            md.to_json(),
            tdpath('minimal-with-defaults-inferred.serial'),
            ignore_lines=self.IGL,
        )

    def testInferAllformats(self):
        buf, md = self.check_infer('allformats.csv', prov=False, verbosity=0)
        self.assertEqual(buf, [])

    def testInferOnestringSingleField(self):
        buf, md = self.check_infer(
            'onestring.txt', prov=True, verbosity=0, single_field=True
        )
        self.assertEqual(md.delimiter, NO_DELIMITER)

    def testInferAmbiguousAllAmbiguous(self):
        # All date fields ambiguous: should default to EU and warn
        md, buf = self.infer(tdpath('ambig-all.csv'), verbosity=0)
        self.assertEqual(md.date_format, 'DD/MM/YYYY')
        self.assertEqual(len(buf), 1)
        self.assertIn('defaulting to EU', buf[0])
        self.assertIn('"dt"', buf[0])

    def testInferAmbiguousGuidedByEU(self):
        # One unambiguous EU field guides resolution of ambiguous field
        md, buf = self.infer(tdpath('ambig-guided-eu.csv'), verbosity=0)
        self.assertEqual(md.date_format, 'DD/MM/YYYY')
        self.assertEqual(len(buf), 1)
        self.assertIn('assuming EU', buf[0])
        self.assertIn('"ambig"', buf[0])

    def testInferAmbiguousGuidedByUS(self):
        # One unambiguous US field guides resolution of ambiguous field
        md, buf = self.infer(tdpath('ambig-guided-us.csv'), verbosity=0)
        self.assertEqual(md.date_format, 'MM/DD/YYYY')
        self.assertEqual(len(buf), 1)
        self.assertIn('assuming US', buf[0])
        self.assertIn('"ambig"', buf[0])


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
        )

        self.assertEqual(
            analyse_values(
                'd', ['2000.01.01', '31-12-2000', '12/31/2000', '999-99-999']
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
                    '999-99-999',
                    '2000.jan.01',
                    '31-feb-2000',
                    'dec-31/2000',
                    'zzz-99-999',
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
            FieldType.STRING,  # 2/3 valid < 99% threshold → string
        )  # Note: Changing to 999-99-999 99:99:99ksjdhfkZ would break
        # because the .* on the end permits ksjdhfkZ.
        # That should be tightened up later.

        self.assertEqual(
            analyse_values(
                'd',
                [
                    '20000.01.01T12:34:56',
                    '31-12-2000 12:34:56+0100',
                    '999-999-999 99:99:99ksjdhfkZ',
                ],
            ).most_likely_type,
            FieldType.STRING,  # 2/3 valid < 99% threshold → string
        )  # Note: as previous comment.

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
        expected = 'a.txt'
        self.assertEqual(m.choose_csv_from_csvw_name('a.json'), expected)
        self.assertEqual(m.choose_csv_from_csvw_name('/d/a.json'), expected)
        self.assertEqual(m.choose_csv_from_csvw_name('~/d/a.json'), expected)

        self.assertEqual(
            m.choose_csv_from_csvw_name('b-metadata.json'), 'b.txt'
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
        expected = 'a.txt'
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
            m.choose_csv_from_frictionless_name('b.resource.json'), 'b.txt'
        )

    def testConversionSpecificationCLI(self):
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


class TestDateFormatInference(ReferenceTestCase):
    def testDateRE(self):
        R = DateRE
        dates = {
            '2024-01-20': R.ISO_DATEISH,
            '2024/01/20': R.ISO_DATEISH,
            '2024-01-20T12:34:56': R.ISO_DATETIMEISH,
            '2024-01-20 12:34:56.12345': R.ISO_DATETIMEISH,
            '2024/01/20T12:34:56': R.ISO_DATETIMEISH,
            '2024/01/20 12:34:56.12345': R.ISO_DATETIMEISH,
            '20-01-2024': R.DATEISH4Y,
            '20/01/2024': R.DATEISH4Y,
            '01-20-2024': R.DATEISH4Y,
            '01/20/2024': R.DATEISH4Y,
            '20-01-2024T12:34:56': R.DATEISH4Y,
            '20-01-2024T12:34:56.123456': R.DATEISH4Y,
            '20-01-24': R.DATEISH2Y,
            '20/01/24': R.DATEISH2Y,
            '01-20-24': R.DATEISH2Y,
            '01/20/24': R.DATEISH2Y,
            '20-01-24T12:34:56': R.DATEISH2Y,
            '20-01-24T12:34:56.123456': R.DATEISH2Y,
        }

        for k, r in dates.items():
            m = re.match(r, k)
            if not m:
                print(f'Failing: {k} {r.pattern}')
            self.assertIsNotNone(m)

            m = re.match(R.DATEISH, k)
            if not m:
                print(f'Failing: {k} (not DATEISH)')
            self.assertIsNotNone(m)

        sep_dates = {
            '20-01-2024': (
                R.SEPS4Y,
                Separators('-', None, None, False, False, ''),
            ),
            '20-01-2024T12:34:56': (
                R.SEPS4Y,
                Separators('-', 'T', ':', True, False, 'T%H:%M:%S'),
            ),
            '20-01-2024T12:34:56.123': (
                R.SEPS4Y,
                Separators('-', 'T', ':', True, True, 'T%H:%M:%S.%f'),
            ),
            '20/01/2024 12.34.56.123': (
                R.SEPS4Y,
                Separators('/', ' ', '.', True, True, ' %H.%M.%S.%f'),
            ),
        }
        for k, (r, expected) in sep_dates.items():
            actual = get_date_separators(r, k)
            if actual != expected:
                print('-->   actual', actual)
                print('--> expected', expected)
                print()
            self.assertEqual(actual, expected)

    def testDateFormatFromStrings(self):
        f = infer_date_format_from_strings
        # ISO dates — separator preserved
        self.assertEqual(f(['2024-01-01', '2024-01-20']), '%Y-%m-%d')
        self.assertEqual(f(['2024/01/01', '2024/01/20']), '%Y/%m/%d')
        # ISO datetimes — separator and T/space preserved
        self.assertEqual(
            f(['2024-01-01T12:34:56', '2024-01-20T21:22:23']),
            '%Y-%m-%dT%H:%M:%S',
        )
        self.assertEqual(
            f(['2024-01-01 12:34:56', '2024-01-20 21:22:23']),
            '%Y-%m-%d %H:%M:%S',
        )
        # Euro 4Y — separator preserved
        self.assertEqual(f(['01-01-2024', '20-01-2024']), '%d-%m-%Y')
        self.assertEqual(f(['01/01/2024', '20/01/2024']), '%d/%m/%Y')
        # Euro datetime 4Y
        self.assertEqual(
            f(['01-01-2024 12:34:56', '20-01-2024 21:22:23']),
            '%d-%m-%Y %H:%M:%S',
        )
        # US 4Y — separator preserved
        self.assertEqual(f(['01-01-2024', '01-20-2024']), '%m-%d-%Y')
        self.assertEqual(f(['01/01/2024', '01/20/2024']), '%m/%d/%Y')
        # US datetime 4Y
        self.assertEqual(
            f(['01-01-2024 12:34:56', '01-20-2024 21:22:23']),
            '%m-%d-%Y %H:%M:%S',
        )
        # Euro 2Y
        self.assertEqual(f(['01-01-24', '20-01-24']), '%d-%m-%y')
        # US 2Y
        self.assertEqual(f(['01-01-24', '01-20-24']), '%m-%d-%y')
        # Ambiguous 4Y (all parts <= 12): returns AmbiguousDateFormat
        self.assertEqual(
            f(['01-01-2024', '02-03-2024']),
            AmbiguousDateFormat.EU_OR_US_DATE,
        )
        # Ambiguous 4Y with time
        self.assertEqual(
            f(['01-01-2024 01:02:03', '02-03-2024 04:05:06']),
            AmbiguousDateFormat.EU_OR_US_DATETIME,
        )
        # Ambiguous 2Y (all parts <= 12)
        self.assertEqual(
            f(['01-01-24', '02-03-24']),
            AmbiguousDateFormat.EU_OR_US_DATE_2Y,
        )
        # Ambiguous 2Y with time
        self.assertEqual(
            f(['01-01-24 01:02:03', '02-03-24 04:05:06']),
            AmbiguousDateFormat.EU_OR_US_DATETIME_2Y,
        )
        # ISO datetime with fractional seconds
        self.assertEqual(
            f(['2024-01-01T12:34:56.123', '2024-01-20T21:22:23.456789']),
            '%Y-%m-%dT%H:%M:%S.%f',
        )
        # Mixed ISO datetime: some with frac, some without → include .%f
        self.assertEqual(
            f(['2024-01-01T12:34:56', '2024-01-20T21:22:23.456']),
            '%Y-%m-%dT%H:%M:%S.%f',
        )
        # EU date with dot separator (unambiguous: day > 12)
        self.assertEqual(f(['20.01.2024']), '%d.%m.%Y')
        # US date with dot separator (unambiguous: second part > 12)
        self.assertEqual(f(['01.20.2024']), '%m.%d.%Y')
        # Ambiguous dot-separator date
        self.assertEqual(
            f(['01.01.2024', '02.03.2024']),
            AmbiguousDateFormat.EU_OR_US_DATE,
        )
        # Not dates at all
        self.assertIsNone(f(['foo', 'bar']))
        # Empty
        self.assertIsNone(f([]))


class TestInferAllFlatFiles(TestInference):
    # One test per flat file in testdata. All provisional (prov=True).
    # Add targeted assertions to specific tests as inference is validated.

    def validate_inferred_serial_wrt_handmade_serial(
        self, stem, lib='polars', inf_path=None, prov=False
    ):
        """Compare prov-inferred serial+DF against plain .serial.

        md is the inferred metadata returned by check_infer(prov=True).
        """
        plain_path = tdpath(stem + '.serial')
        p = '-prov' if prov else ''
        infpath = nvl(inf_path, tdpath(stem + f'{p}-inferred.serial'))
        csv_path = tdpath(stem + '.csv')
        Warn1, _buf1 = testwarn()
        Warn2, _buf2 = testwarn()
        convert = csv_to_pandas if lib == 'pandas' else csv_to_polars
        df_prov = convert(csv_path, infpath, warner=Warn1)
        df_plain = convert(csv_path, plain_path, warner=Warn2)
        self.assertDataFramesEqual(df_prov, df_plain, type_matching='loose')

    def testInferAllCsvwTypes(self):
        buf, md = self.check_infer(
            'all-csvw-types.csv', prov=False, verbosity=0
        )
        self.assertEqual(buf, [])
        df = csv_to_pandas(
            tdpath('all-csvw-types.csv'),
            tdpath('all-csvw-types-inferred.serial'),
        )
        ref_df = pandas.read_parquet(tdpath('all-csvw-types-v2dates.parquet'))
        # gDay/gMonth/gYear are int in inferred serial (correctly) but
        # object in the parquet (written without type info); exclude them
        exclude = ['gDay', 'gMonth', 'gYear']
        df = df.drop(columns=exclude)
        ref_df = ref_df.drop(columns=exclude)
        self.assertDataFramesEqual(df, ref_df, type_matching='loose')
        csvw = serial_to_csvw(md, 'all-csvw-types.csv')
        outpath = tmppath('all-csvw-types.csvwvalidated.json')
        csvw.write_csvw(outpath, csvfile='all-csvw-types.csv')
        self.assertFileCorrect(
            outpath,
            tdpath('all-csvw-types.csvwvalidated.json'),
            ignore_lines=self.IGL,
        )

    def testInferAllformats(self):
        buf, md = self.check_infer('allformats.csv', prov=False, verbosity=0)
        self.assertEqual(buf, [])
        Warn, buf2 = testwarn()
        df = csv_to_polars(
            tdpath('allformats.csv'),
            tdpath('allformats-inferred.serial'),
            warner=Warn,
        )
        ref_df = polars.read_parquet(tdpath('allformats.parquet'))
        self.assertDataFramesEqual(df, ref_df, type_matching='loose')
        # date format warnings for post-read strptime parsing are expected
        self.assertTrue(all('parse post-read' in w for w in buf2))

    def testInferAllformats2unspec(self):
        buf, md = self.check_infer(
            'allformats2unspec.csv', prov=True, verbosity=0
        )

    def testInferAmbigAll(self):
        buf, md = self.check_infer('ambig-all.csv', prov=True, verbosity=0)

    def testInferAmbigGuidedEu(self):
        buf, md = self.check_infer(
            'ambig-guided-eu.csv', prov=True, verbosity=0
        )

    def testInferAmbigGuidedUs(self):
        buf, md = self.check_infer(
            'ambig-guided-us.csv', prov=True, verbosity=0
        )

    def testInferCodingUtf16(self):
        buf, md = self.check_infer('coding-utf16.csv', prov=True, verbosity=0)

    def testInferCodingUtf8(self):
        buf, md = self.check_infer('coding-utf8.csv', prov=True, verbosity=0)

    def testInferDdd(self):
        buf, md = self.check_infer('ddd.csv', verbosity=0)
        # Quoting style detection reclassifies evenstr, oddstr, elevens
        self.assertTrue(all('reclassified' in w for w in buf))
        self.assertEqual(
            [
                w
                for w in buf
                if 'evenstr' in w or 'oddstr' in w or 'elevens' in w
            ],
            buf,
        )
        Warn, buf2 = testwarn()
        df = csv_to_polars(
            tdpath('ddd.csv'),
            tdpath('ddd-inferred.serial'),
            warner=Warn,
        )
        parquet = os.path.join(REFTESTDATA, 'ddd.parquet')
        ref_df = polars.read_parquet(parquet)
        ref_df = ref_df.drop('greek')
        self.assertDataFramesEqual(df, ref_df, type_matching='loose')
        self.assertEqual(buf2, [])

    def testInferDdd2(self):
        buf, md = self.check_infer('ddd2.csv', verbosity=0)

    def testInferDdd3(self):
        buf, md = self.check_infer('ddd3.csv', prov=True, verbosity=0)

    def testInferAlphaDates(self):
        buf, md = self.check_infer('alphadates.tsv', prov=False, verbosity=0)
        self.assertEqual(buf, [])

    def testInferAlphaLongDates(self):
        buf, md = self.check_infer(
            'alphalongdates.tsv', prov=False, verbosity=0
        )
        self.assertEqual(buf, [])

    def testInferElements3Old(self):
        buf, md = self.check_infer(
            'elements3-old.csv', prov=False, verbosity=0
        )
        self.assertEqual(buf, [])
        Warn, buf2 = testwarn()
        df = csv_to_polars(
            tdpath('elements3-old.csv'),
            tdpath('elements3-old-inferred.serial'),
            warner=Warn,
        )
        ref_df = polars.read_parquet(tdpath('elements3-old.parquet'))
        self.assertDataFramesEqual(df, ref_df)
        self.assertEqual(buf2, [])

    def testInferEurod(self):
        buf, md = self.check_infer('eurod.csv', verbosity=0)
        self.validate_inferred_serial_wrt_handmade_serial('eurod')

    def testInferEurod2y(self):
        buf, md = self.check_infer('eurod2y.csv', verbosity=0)
        self.validate_inferred_serial_wrt_handmade_serial('eurod2y')

    def testInferEurodtWriteKw(self):
        buf, md = self.check_infer('eurodt-write-kw.csv', verbosity=0)
        self.validate_inferred_serial_wrt_handmade_serial('eurodt-write-kw')

    def testInferEurodtWriteSerial(self):
        buf, md = self.check_infer('eurodt-write-serial.csv', verbosity=0)
        self.validate_inferred_serial_wrt_handmade_serial(
            'eurodt-write-serial'
        )

    def testInferEurodt(self):
        buf, md = self.check_infer('eurodt.csv', verbosity=0)
        self.validate_inferred_serial_wrt_handmade_serial('eurodt')

    def testInferEurodt2y(self):
        buf, md = self.check_infer('eurodt2y.csv', verbosity=0)
        self.validate_inferred_serial_wrt_handmade_serial('eurodt2y')

    def testInferExcel1(self):
        buf, md = self.check_infer('excel1.csv', prov=False, verbosity=0)
        self.assertEqual(buf, [])

    def testInferExcel2(self):
        buf, md = self.check_infer('excel2.csv', prov=False, verbosity=0)
        self.assertEqual(buf, [])

    def testInferExcel3(self):
        buf, md = self.check_infer('excel3.csv', prov=False, verbosity=0)
        self.assertEqual(buf, [])

    def testInferIsod(self):
        buf, md = self.check_infer('isod.csv', verbosity=0)
        self.validate_inferred_serial_wrt_handmade_serial('isod')

    def testInferIsodatetime(self):
        buf, md = self.check_infer('isodatetime.csv', verbosity=0)
        self.validate_inferred_serial_wrt_handmade_serial('isodatetime')

    def testInferIsodt(self):
        buf, md = self.check_infer('isodt.csv', verbosity=0)
        # verified by hand

    def testInferMinimal(self):
        buf, md = self.check_infer('minimal.csv', prov=True, verbosity=0)

    def testInferNullInference1(self):
        # Unquoted strings: no quoting evidence, '' not inferred as null
        buf, md = self.check_infer(
            'nullinference1.csv', prov=False, verbosity=0
        )
        self.assertEqual(buf, [])
        self.assertIsNone(md.null_indicator)
        self.assertEqual(md.quoting, 'QUOTE_NONE')

    def testInferNullInference2(self):
        # Quoted strings, only "" empty: '' dropped (empty string, not null)
        buf, md = self.check_infer(
            'nullinference2.csv', prov=False, verbosity=0
        )
        self.assertEqual(buf, [])
        self.assertIsNone(md.null_indicator)
        self.assertEqual(md.quoting, 'QUOTE_STRINGS_ONLY')

    def testInferNullInference3(self):
        # Quoted strings, quoted "" and unquoted empty: '' is genuine null
        buf, md = self.check_infer(
            'nullinference3.psv', prov=False, verbosity=0
        )
        self.assertEqual(buf, [])
        self.assertEqual(md.null_indicator, '')
        self.assertEqual(md.quoting, 'QUOTE_STRINGS_ONLY')

    def testInferNullInference4(self):
        # Quoted "" in string col, unquoted empty in non-string col: '' is null
        buf, md = self.check_infer(
            'nullinference4.csv', prov=False, verbosity=0
        )
        self.assertEqual(buf, [])
        self.assertEqual(md.null_indicator, '')
        self.assertEqual(md.quoting, 'QUOTE_STRINGS_ONLY')

    def testInferNulls1(self):
        buf, md = self.check_infer('nulls1.csv', prov=False, verbosity=0)
        self.assertEqual(buf, [])
        Warn, buf2 = testwarn()
        df = csv_to_pandas(
            tdpath('nulls1.csv'),
            tdpath('nulls1-inferred.serial'),
            warner=Warn,
        )
        # nulls1n.parquet was written from nulls1.csv via a good .serial
        # file, so known null strings are already converted to null
        # and type checking should be perfect.
        ref_df = pandas.read_parquet(tdpath('nulls1n.parquet'))
        self.assertDataFramesEqual(df, ref_df, type_matching='strict')
        self.assertEqual(buf2, [])

    def testInferSigCp1252(self):
        buf, md = self.check_infer('sig-cp1252.csv', prov=False, verbosity=0)
        # encoding fallback warning is expected for non-UTF-8 files
        self.assertEqual(len(buf), 1)
        self.assertIn('cp1252', buf[0])
        Warn, buf2 = testwarn()
        df = csv_to_polars(
            tdpath('sig-cp1252.csv'),
            tdpath('sig-cp1252-inferred.serial'),
            warner=Warn,
        )
        ref_df = polars.read_parquet(tdpath('sig-cp1252.parquet'))
        self.assertDataFramesEqual(df, ref_df, type_matching='loose')
        self.assertEqual(buf2, [])

    def testInferSigEquivUtf16(self):
        buf, md = self.check_infer(
            'sig-equiv-utf16.csv', prov=False, verbosity=0
        )
        self.assertEqual(buf, [])
        Warn, buf2 = testwarn()
        df = csv_to_pandas(
            tdpath('sig-equiv-utf16.csv'),
            tdpath('sig-equiv-utf16-inferred.serial'),
            warner=Warn,
        )
        ref_df = pandas.read_parquet(tdpath('sig-equiv-utf16.parquet'))
        self.assertDataFramesEqual(df, ref_df, type_matching='loose')
        self.assertEqual(buf2, [])

    def testInferSigEquivUtf8(self):
        buf, md = self.check_infer(
            'sig-equiv-utf8.csv', prov=False, verbosity=0
        )
        self.assertEqual(buf, [])
        Warn, buf2 = testwarn()
        df = csv_to_polars(
            tdpath('sig-equiv-utf8.csv'),
            tdpath('sig-equiv-utf8-inferred.serial'),
            warner=Warn,
        )
        ref_df = polars.read_parquet(tdpath('sig-equiv-utf8.parquet'))
        self.assertDataFramesEqual(df, ref_df, type_matching='loose')
        self.assertEqual(buf2, [])

    def testInferSigLatin1(self):
        buf, md = self.check_infer('sig-latin1.csv', prov=False, verbosity=0)
        # chardet >= 6 may detect as UTF-8 first, then fall back to latin-1
        self.assertIn(len(buf), (0, 1))
        Warn, buf2 = testwarn()
        df = csv_to_pandas(
            tdpath('sig-latin1.csv'),
            tdpath('sig-latin1-inferred.serial'),
            warner=Warn,
        )
        ref_df = pandas.read_parquet(tdpath('sig-latin1.parquet'))
        self.assertDataFramesEqual(df, ref_df, type_matching='loose')
        self.assertEqual(buf2, [])

    def testInferSigLatin9(self):
        buf, md = self.check_infer('sig-latin9.csv', prov=False, verbosity=0)
        # chardet >= 6 may detect as UTF-8 first, then fall back to latin-1
        self.assertIn(len(buf), (0, 1))
        Warn, buf2 = testwarn()
        df = csv_to_polars(
            tdpath('sig-latin9.csv'),
            tdpath('sig-latin9-inferred.serial'),
            warner=Warn,
        )
        ref_df = polars.read_parquet(tdpath('sig-latin9.parquet'))
        # latin-9 (iso-8859-15) is indistinguishable from latin-1 at inference
        # time; the sig column will be the latin-9 bytes misread as latin-1
        self.assertEqual(
            df['sig'][0],
            ref_df['sig'][0].encode('iso-8859-15').decode('iso-8859-1'),
        )
        self.assertDataFramesEqual(
            df.drop('sig'), ref_df.drop('sig'), type_matching='loose'
        )
        self.assertEqual(buf2, [])

    def testInferSimple(self):
        buf, md = self.check_infer('simple.csv', prov=True, verbosity=0)

    def testInferSmallCp1252(self):
        # chardet < 6 detects this file as windows-1255; chardet >= 6 as
        # latin-1, which the cp1252 byte check in read_file_lines promotes
        # to cp1252.
        buf, md = self.check_infer(
            'small-cp1252.csv',
            prov=True,
            verbosity=0,
            ignore_patterns=[r'"encoding": "(latin-1|windows-1255)"'],
        )

    def testInferSmallLatin1(self):
        # chardet < 6 detects this file as windows-1255; chardet >= 6 as
        # latin-1.
        buf, md = self.check_infer(
            'small-latin1.csv',
            prov=True,
            verbosity=0,
            ignore_patterns=[r'"encoding": "(latin-1|windows-1255)"'],
        )

    def testInferSmallLatin9(self):
        # chardet < 6 detects this file as windows-1255; chardet >= 6 as
        # latin-1.
        buf, md = self.check_infer(
            'small-latin9.csv',
            prov=True,
            verbosity=0,
            ignore_patterns=[r'"encoding": "(latin-1|windows-1255)"'],
        )

    def testInferSmallWriteKw(self):
        buf, md = self.check_infer('small-write-kw.csv', verbosity=0)
        self.validate_inferred_serial_wrt_handmade_serial('small-write-kw')

    def testInferSmallWriteSerial(self):
        buf, md = self.check_infer('small-write-serial.csv', verbosity=0)
        self.validate_inferred_serial_wrt_handmade_serial('small-write-serial')

    def testInferSmall(self):
        buf, md = self.check_infer('small.csv', verbosity=0)
        # Fails to infer 12 us datetime.
        # Fine for now. Triggers Pandas warning, which is nasty
        # Don't compare dataframe for now
        # self.validate_inferred_serial_wrt_handmade_serial('small')

    def testInferSmall2(self):
        buf, md = self.check_infer('small2.csv', verbosity=0)

    def testInferStrings1(self):
        buf, md = self.check_infer('strings1.csv', prov=True, verbosity=0)

    def testInferTiny1cdPandas(self):
        buf, md = self.check_infer('tiny1cd-pandas.csv', verbosity=0)
        self.validate_inferred_serial_wrt_handmade_serial(
            'tiny1cd-pandas', lib='pandas'
        )

    def testInferTiny1cd(self):
        buf, md = self.check_infer('tiny1cd.csv', verbosity=0)
        self.validate_inferred_serial_wrt_handmade_serial('tiny1cd')

    def testInferTiny1cd3(self):
        buf, md = self.check_infer('tiny1cd3.csv', verbosity=0)
        self.validate_inferred_serial_wrt_handmade_serial('tiny1cd3')

    def testInferTiny1cnPandas(self):
        buf, md = self.check_infer(
            'tiny1cn-pandas.csv', prov=True, verbosity=0
        )

    def testInferTiny1cn(self):
        buf, md = self.check_infer('tiny1cn.csv', prov=False, verbosity=0)
        self.assertEqual(buf, [])

    def testInferTiny1cn3(self):
        buf, md = self.check_infer('tiny1cn3.csv', verbosity=0)
        self.validate_inferred_serial_wrt_handmade_serial('tiny1cn3')

    def testInferTiny1ndDot(self):
        buf, md = self.check_infer('tiny1nd-dot.csv', prov=True, verbosity=0)
        # Infer can't handle the dot
        # So we override:
        Warn, buf = testwarn()
        md2 = infer_format_from_flat_file(
            tdpath('tiny1nd-dot.csv'),
            warner=Warn,
            raise_error=True,
            null=['.'],
        )
        outpath = tmppath('tiny1cn-force-dot-null.serial')
        with open(outpath, 'w') as f:
            f.write(md2.to_json())
        self.validate_inferred_serial_wrt_handmade_serial(
            'tiny1nd-dot', lib='pandas', inf_path=outpath
        )

    def testInferTiny1ndNull(self):
        buf, md = self.check_infer('tiny1nd-NULL.csv', prov=True, verbosity=0)

    def testInferTiny1ndPandas(self):
        buf, md = self.check_infer('tiny1nd-pandas.csv', verbosity=0)
        self.validate_inferred_serial_wrt_handmade_serial(
            'tiny1nd-pandas', lib='pandas'
        )

    def testInferTiny1nd(self):
        buf, md = self.check_infer('tiny1nd.csv', verbosity=0)
        self.validate_inferred_serial_wrt_handmade_serial('tiny1nd')

    def testInferTiny1nd3(self):
        buf, md = self.check_infer('tiny1nd3.csv', verbosity=0)
        self.validate_inferred_serial_wrt_handmade_serial('tiny1nd3')

    def testInferTiny1ndq(self):
        buf, md = self.check_infer('tiny1ndq.csv', prov=True, verbosity=0)

    def testInferTiny1nnPandas(self):
        buf, md = self.check_infer('tiny1nn-pandas.csv', verbosity=0)
        self.validate_inferred_serial_wrt_handmade_serial(
            'tiny1nn-pandas', lib='pandas'
        )

    def testInferTiny1nn(self):
        buf, md = self.check_infer('tiny1nn.csv', verbosity=0)
        self.validate_inferred_serial_wrt_handmade_serial('tiny1nn')

    def testInferTiny1nn3(self):
        buf, md = self.check_infer('tiny1nn3.csv', verbosity=0)
        self.validate_inferred_serial_wrt_handmade_serial('tiny1nn3')

    def testInferTz(self):
        buf, md = self.check_infer('tz.csv', prov=True, verbosity=0)

    def testInferUsd(self):
        buf, md = self.check_infer('usd.csv', verbosity=0)
        self.validate_inferred_serial_wrt_handmade_serial('usd')

    def testInferUsd2y(self):
        buf, md = self.check_infer('usd2y.csv', verbosity=0)
        self.validate_inferred_serial_wrt_handmade_serial('usd2y')

    def testInferUsdt(self):
        buf, md = self.check_infer('usdt.csv', verbosity=0)
        self.validate_inferred_serial_wrt_handmade_serial('usdt')

    def testInferUsdt2y(self):
        buf, md = self.check_infer('usdt2y.csv', verbosity=0)
        self.validate_inferred_serial_wrt_handmade_serial('usdt2y')

    # .txt files

    def testInferOnebool(self):
        with self.assertRaisesRegex(TDDAError, 'Separator does not appear'):
            self.check_infer('onebool.txt', prov=True, verbosity=0)

    def testInferOnereal(self):
        with self.assertRaisesRegex(TDDAError, 'Separator does not appear'):
            self.check_infer('onereal.txt', prov=True, verbosity=0)

    def testInferOnestring(self):
        with self.assertRaisesRegex(TDDAError, 'Too many values for header'):
            self.check_infer('onestring.txt', prov=True, verbosity=0)

    def testInferSemicolon(self):
        buf, md = self.check_infer('semicolon.txt', prov=True, verbosity=0)

    def testInferSemicolon2(self):
        buf, md = self.check_infer('semicolon2.txt', prov=True, verbosity=0)

    def testInferSemicolon3(self):
        buf, md = self.check_infer('semicolon3.txt', prov=True, verbosity=0)

    def testInferSemicolon4(self):
        buf, md = self.check_infer('semicolon4.txt', prov=True, verbosity=0)

    def testInferSemicolon5(self):
        buf, md = self.check_infer('semicolon5.txt', prov=True, verbosity=0)

    def testInferSemicolon6(self):
        buf, md = self.check_infer('semicolon6.txt', prov=True, verbosity=0)

    # .tsv file

    def testInferIsodtTsv(self):
        buf, md = self.check_infer('isodt.tsv', verbosity=0)
        # Verifued by hand
        # Also successfully converts to csvw and csvwvalidate validates it.
        # TODO: Could add tests around that. isodt-metadata.json
        # is for this TSV file (not the CSV file).

    # .ssv file

    def testInferTiny1ndWeirdSsv(self):
        buf, md = self.check_infer('tiny1nd-weird.ssv', prov=True, verbosity=0)

    def testInferenceLiteralDates(self):
        outpath = tmppath('ddd-literal-inferred.serial')
        c = SerialConverter(
            cli_args=[
                tdpath('ddd.csv'),
                outpath,
                '--generate',
                '--use-literal-dates',
            ]
        )
        Warn, buf = testwarn()
        c.convert(warner=Warn)
        self.assertFileCorrect(
            outpath,
            tdpath('ddd-literal-inferred.serial'),
            ignore_lines=self.IGL,
        )


class TestFirstLineStats(ReferenceTestCase):
    """Tests for FirstLineStats using header*/noheader*/dataline1-* files."""

    def check_fls(self, filename, **kw):
        path = tdpath(filename)
        line, _, _ = read_file_lines(path, lines_to_use=0)
        fls = FirstLineStats(line, **kw)
        base, ext = os.path.splitext(filename)
        if ext in ('.csv', '.txt'):
            stem = base
        else:
            stem = base + '-' + ext[1:]
        refname = f'fls-{stem}.txt'
        self.assertStringCorrect(str(fls), tdpath(refname))

    def testFLS_header1(self):
        self.check_fls('header1.txt')

    def testFLS_header2quoted(self):
        self.check_fls('header2quoted.txt')

    def testFLS_header3squoted(self):
        self.check_fls('header3squoted.txt')

    def testFLS_header4pandas_style(self):
        self.check_fls('header4pandas-style.txt')

    def testFLS_header5ch(self):
        self.check_fls('header5ch.txt')

    def testFLS_header6dqstutter(self):
        self.check_fls('header6dqstutter.txt')

    def testFLS_header7dqstutter(self):
        self.check_fls('header7dqstutter.txt')

    def testFLS_header8sqstutter(self):
        self.check_fls('header8sqstutter.txt')

    def testFLS_header9sqstutter(self):
        self.check_fls('header9sqstutter.txt')

    def testFLS_header10dqesc(self):
        self.check_fls('header10dqesc.txt')

    def testFLS_header11sqesc(self):
        self.check_fls('header11sqesc.txt')

    def testFLS_header12dqesc(self):
        self.check_fls('header12dqesc.txt')

    def testFLS_header13sqesc(self):
        self.check_fls('header13sqesc.txt')

    def testFLS_header14spaces(self):
        self.check_fls('header14spaces.txt')

    def testFLS_header15nonletters(self):
        self.check_fls('header15nonletters.txt')

    def testFLS_header16nonletters(self):
        self.check_fls('header16nonletters.txt')

    def testFLS_header17apos(self):
        self.check_fls('header17apos.txt')

    def testFLS_header18allcaps(self):
        self.check_fls('header18allcaps.txt')

    def testFLS_header19nums(self):
        self.check_fls('header19nums.txt')

    def testFLS_header20accents(self):
        self.check_fls('header20accents.txt')

    def testFLS_header20dups(self):
        self.check_fls('header20dups.txt')

    def testFLS_header21gritbins(self):
        self.check_fls('header21gritbins.txt')

    def testFLS_header21single_name(self):
        self.check_fls('header21single-name.txt')

    def testFLS_header22single_ambig(self):
        self.check_fls('header22single-ambig.txt')

    def testFLS_header23tabs(self):
        self.check_fls('header23tabs.txt')

    def testFLS_header24pipes(self):
        self.check_fls('header24pipes.txt')

    def testFLS_header25semis(self):
        self.check_fls('header25semis.txt')

    def testFLS_noheader1(self):
        self.check_fls('noheader1.txt')

    def testFLS_noheader2(self):
        self.check_fls('noheader2.txt')

    def testFLS_noheader3(self):
        self.check_fls('noheader3.txt')

    def testFLS_noheader4single(self):
        self.check_fls('noheader4single.txt')

    def testFLS_noheader5dates(self):
        self.check_fls('noheader5dates.txt')

    def testFLS_noheader6nums(self):
        self.check_fls('noheader6nums.txt')

    def testFLS_dataline1_all_csvw_types(self):
        self.check_fls('dataline1-all-csvw-types.csv')

    def testFLS_dataline1_allformats(self):
        self.check_fls('dataline1-allformats.csv')

    def testFLS_dataline1_allformats2unspec(self):
        self.check_fls('dataline1-allformats2unspec.csv')

    def testFLS_dataline1_ambig_all(self):
        self.check_fls('dataline1-ambig-all.csv')

    def testFLS_dataline1_ambig_guided_eu(self):
        self.check_fls('dataline1-ambig-guided-eu.csv')

    def testFLS_dataline1_ambig_guided_us(self):
        self.check_fls('dataline1-ambig-guided-us.csv')

    def testFLS_dataline1_coding_utf16(self):
        self.check_fls('dataline1-coding-utf16.csv')

    def testFLS_dataline1_coding_utf8(self):
        self.check_fls('dataline1-coding-utf8.csv')

    def testFLS_dataline1_ddd(self):
        self.check_fls('dataline1-ddd.csv')

    def testFLS_dataline1_ddd2(self):
        self.check_fls('dataline1-ddd2.csv')

    def testFLS_dataline1_ddd3(self):
        self.check_fls('dataline1-ddd3.csv')

    def testFLS_dataline1_elements3_old(self):
        self.check_fls('dataline1-elements3-old.csv')

    def testFLS_dataline1_eurod(self):
        self.check_fls('dataline1-eurod.csv')

    def testFLS_dataline1_eurod2y(self):
        self.check_fls('dataline1-eurod2y.csv')

    def testFLS_dataline1_eurodt_write_kw(self):
        self.check_fls('dataline1-eurodt-write-kw.csv')

    def testFLS_dataline1_eurodt_write_serial(self):
        self.check_fls('dataline1-eurodt-write-serial.csv')

    def testFLS_dataline1_eurodt(self):
        self.check_fls('dataline1-eurodt.csv')

    def testFLS_dataline1_eurodt2y(self):
        self.check_fls('dataline1-eurodt2y.csv')

    def testFLS_dataline1_isod(self):
        self.check_fls('dataline1-isod.csv')

    def testFLS_dataline1_isodatetime(self):
        self.check_fls('dataline1-isodatetime.csv')

    def testFLS_dataline1_isodt(self):
        self.check_fls('dataline1-isodt.csv')

    def testFLS_dataline1_isodt_tsv(self):
        self.check_fls('dataline1-isodt.tsv')

    def testFLS_dataline1_minimal(self):
        self.check_fls('dataline1-minimal.csv')

    def testFLS_dataline1_nulls1(self):
        self.check_fls('dataline1-nulls1.csv')

    def testFLS_dataline1_onebool(self):
        self.check_fls('dataline1-onebool.txt')

    def testFLS_dataline1_onereal(self):
        self.check_fls('dataline1-onereal.txt')

    def testFLS_dataline1_onestring(self):
        self.check_fls('dataline1-onestring.txt')

    def testFLS_dataline1_semicolon(self):
        self.check_fls('dataline1-semicolon.txt')

    def testFLS_dataline1_semicolon2(self):
        self.check_fls('dataline1-semicolon2.txt')

    def testFLS_dataline1_semicolon3(self):
        self.check_fls('dataline1-semicolon3.txt')

    def testFLS_dataline1_semicolon4(self):
        self.check_fls('dataline1-semicolon4.txt')

    def testFLS_dataline1_semicolon5(self):
        self.check_fls('dataline1-semicolon5.txt')

    def testFLS_dataline1_semicolon6(self):
        self.check_fls('dataline1-semicolon6.txt')

    def testFLS_dataline1_sig_cp1252(self):
        self.check_fls('dataline1-sig-cp1252.csv')

    def testFLS_dataline1_sig_equiv_utf16(self):
        self.check_fls('dataline1-sig-equiv-utf16.csv')

    def testFLS_dataline1_sig_equiv_utf8(self):
        self.check_fls('dataline1-sig-equiv-utf8.csv')

    def testFLS_dataline1_sig_latin1(self):
        self.check_fls('dataline1-sig-latin1.csv')

    def testFLS_dataline1_sig_latin9(self):
        self.check_fls('dataline1-sig-latin9.csv')

    def testFLS_dataline1_simple(self):
        self.check_fls('dataline1-simple.csv')

    def testFLS_dataline1_small_cp1252(self):
        self.check_fls('dataline1-small-cp1252.csv')

    def testFLS_dataline1_small_latin1(self):
        self.check_fls('dataline1-small-latin1.csv')

    def testFLS_dataline1_small_latin9(self):
        self.check_fls('dataline1-small-latin9.csv')

    def testFLS_dataline1_small_write_kw(self):
        self.check_fls('dataline1-small-write-kw.csv')

    def testFLS_dataline1_small_write_serial(self):
        self.check_fls('dataline1-small-write-serial.csv')

    def testFLS_dataline1_small(self):
        self.check_fls('dataline1-small.csv')

    def testFLS_dataline1_small2(self):
        self.check_fls('dataline1-small2.csv')

    def testFLS_dataline1_strings1(self):
        self.check_fls('dataline1-strings1.csv')

    def testFLS_dataline1_tiny1cd_pandas(self):
        self.check_fls('dataline1-tiny1cd-pandas.csv')

    def testFLS_dataline1_tiny1cd(self):
        self.check_fls('dataline1-tiny1cd.csv')

    def testFLS_dataline1_tiny1cd3(self):
        self.check_fls('dataline1-tiny1cd3.csv')

    def testFLS_dataline1_tiny1cn_pandas(self):
        self.check_fls('dataline1-tiny1cn-pandas.csv')

    def testFLS_dataline1_tiny1cn(self):
        self.check_fls('dataline1-tiny1cn.csv')

    def testFLS_dataline1_tiny1cn3(self):
        self.check_fls('dataline1-tiny1cn3.csv')

    def testFLS_dataline1_tiny1nd_dot(self):
        self.check_fls('dataline1-tiny1nd-dot.csv')

    def testFLS_dataline1_tiny1nd_NULL(self):
        self.check_fls('dataline1-tiny1nd-NULL.csv')

    def testFLS_dataline1_tiny1nd_pandas(self):
        self.check_fls('dataline1-tiny1nd-pandas.csv')

    def testFLS_dataline1_tiny1nd(self):
        self.check_fls('dataline1-tiny1nd.csv')

    def testFLS_dataline1_tiny1nd3(self):
        self.check_fls('dataline1-tiny1nd3.csv')

    def testFLS_dataline1_tiny1ndq(self):
        self.check_fls('dataline1-tiny1ndq.csv')

    def testFLS_dataline1_tiny1nn_pandas(self):
        self.check_fls('dataline1-tiny1nn-pandas.csv')

    def testFLS_dataline1_tiny1nn(self):
        self.check_fls('dataline1-tiny1nn.csv')

    def testFLS_dataline1_tiny1nn3(self):
        self.check_fls('dataline1-tiny1nn3.csv')

    def testFLS_dataline1_tz(self):
        self.check_fls('dataline1-tz.csv')

    def testFLS_dataline1_usd(self):
        self.check_fls('dataline1-usd.csv')

    def testFLS_dataline1_usd2y(self):
        self.check_fls('dataline1-usd2y.csv')

    def testFLS_dataline1_usdt(self):
        self.check_fls('dataline1-usdt.csv')

    def testFLS_dataline1_usdt2y(self):
        self.check_fls('dataline1-usdt2y.csv')


if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
