import os
import re

from collections import namedtuple

from tdda.referencetest import ReferenceTestCase, tag

from tdda.serial.converter import SerialConverter
from tdda.serial.csvw import CSVWMetadata
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
from tdda.utils import TDDAError


from tdda.serial.testserial import (
    tdpath,
    tmppath,
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

    def check_infer(self, name, prov=False, **kw):
        base, ext = os.path.splitext(name)
        stem = base if ext == '.csv' else base + '-' + ext[1:]
        suffix = '-prov-inferred.serial' if prov else '-inferred.serial'
        outname = stem + suffix
        Warn, buf = testwarn()
        md = infer_format_from_flat_file(tdpath(name), warner=Warn,
                                         raise_error=True, **kw)
        outpath = tmppath(outname)
        with open(outpath, 'w') as f:
            f.write(md.to_json())
        self.assertFileCorrect(outpath, tdpath(outname), ignore_lines=self.IGL)
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
        self.assertEqual(buf, [
            "encoding: 'UTF-8' (default, no evidence)",
            "quote_char: '\"' (default, no evidence)",
        ])

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
        buf, md = self.check_infer('allformats.csv', prov=True, verbosity=0)
        self.assertEqual(buf, [])

    def testInferOnestringSingleField(self):
        buf, md = self.check_infer('onestring.txt', prov=True,
                                   verbosity=0, single_field=True)
        self.assertEqual(md.delimiter, NO_DELIMITER)

    def testInferAmbiguousAllAmbiguous(self):
        # All date fields ambiguous: should default to EU and warn
        md, buf = self.infer(tdpath('ambig-all.csv'), verbosity=0)
        self.assertEqual(md.date_format, '%d/%m/%Y')
        self.assertEqual(len(buf), 1)
        self.assertIn('defaulting to EU', buf[0])
        self.assertIn('"dt"', buf[0])

    def testInferAmbiguousGuidedByEU(self):
        # One unambiguous EU field guides resolution of ambiguous field
        md, buf = self.infer(tdpath('ambig-guided-eu.csv'), verbosity=0)
        self.assertEqual(md.date_format, '%d/%m/%Y')
        self.assertEqual(len(buf), 1)
        self.assertIn('assuming EU', buf[0])
        self.assertIn('"ambig"', buf[0])

    def testInferAmbiguousGuidedByUS(self):
        # One unambiguous US field guides resolution of ambiguous field
        md, buf = self.infer(tdpath('ambig-guided-us.csv'), verbosity=0)
        self.assertEqual(md.date_format, '%m/%d/%Y')
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

    def testInferAllCsvwTypes(self):
        buf, md = self.check_infer('all-csvw-types.csv', prov=True,
                                   verbosity=0)

    def testInferAllformats(self):
        buf, md = self.check_infer('allformats.csv', prov=True, verbosity=0)

    def testInferAllformats2unspec(self):
        buf, md = self.check_infer('allformats2unspec.csv', prov=True,
                                   verbosity=0)

    def testInferAmbigAll(self):
        buf, md = self.check_infer('ambig-all.csv', prov=True, verbosity=0)

    def testInferAmbigGuidedEu(self):
        buf, md = self.check_infer('ambig-guided-eu.csv', prov=True,
                                   verbosity=0)

    def testInferAmbigGuidedUs(self):
        buf, md = self.check_infer('ambig-guided-us.csv', prov=True,
                                   verbosity=0)

    def testInferCodingUtf16(self):
        buf, md = self.check_infer('coding-utf16.csv', prov=True, verbosity=0)

    def testInferCodingUtf8(self):
        buf, md = self.check_infer('coding-utf8.csv', prov=True, verbosity=0)

    def testInferDdd(self):
        buf, md = self.check_infer('ddd.csv', prov=True, verbosity=0)

    def testInferDdd2(self):
        buf, md = self.check_infer('ddd2.csv', prov=True, verbosity=0)

    def testInferDdd3(self):
        buf, md = self.check_infer('ddd3.csv', prov=True, verbosity=0)

    def testInferElements3Old(self):
        buf, md = self.check_infer('elements3-old.csv', prov=True,
                                   verbosity=0)

    def testInferEurod(self):
        buf, md = self.check_infer('eurod.csv', prov=True, verbosity=0)

    def testInferEurod2y(self):
        buf, md = self.check_infer('eurod2y.csv', prov=True, verbosity=0)

    def testInferEurodtWriteKw(self):
        buf, md = self.check_infer('eurodt-write-kw.csv', prov=True,
                                   verbosity=0)

    def testInferEurodtWriteSerial(self):
        buf, md = self.check_infer('eurodt-write-serial.csv', prov=True,
                                   verbosity=0)

    def testInferEurodt(self):
        buf, md = self.check_infer('eurodt.csv', prov=True, verbosity=0)

    def testInferEurodt2y(self):
        buf, md = self.check_infer('eurodt2y.csv', prov=True, verbosity=0)

    def testInferIsod(self):
        buf, md = self.check_infer('isod.csv', prov=True, verbosity=0)

    def testInferIsodatetime(self):
        buf, md = self.check_infer('isodatetime.csv', prov=True, verbosity=0)

    def testInferIsodt(self):
        buf, md = self.check_infer('isodt.csv', prov=True, verbosity=0)

    def testInferMinimal(self):
        buf, md = self.check_infer('minimal.csv', prov=True, verbosity=0)

    def testInferNulls1(self):
        buf, md = self.check_infer('nulls1.csv', prov=True, verbosity=0)

    def testInferSigCp1252(self):
        buf, md = self.check_infer('sig-cp1252.csv', prov=True, verbosity=0)

    def testInferSigEquivUtf16(self):
        buf, md = self.check_infer('sig-equiv-utf16.csv', prov=True,
                                   verbosity=0)

    def testInferSigEquivUtf8(self):
        buf, md = self.check_infer('sig-equiv-utf8.csv', prov=True,
                                   verbosity=0)

    def testInferSigLatin1(self):
        buf, md = self.check_infer('sig-latin1.csv', prov=True, verbosity=0)

    def testInferSigLatin9(self):
        buf, md = self.check_infer('sig-latin9.csv', prov=True, verbosity=0)

    def testInferSimple(self):
        buf, md = self.check_infer('simple.csv', prov=True, verbosity=0)

    def testInferSmallCp1252(self):
        buf, md = self.check_infer('small-cp1252.csv', prov=True, verbosity=0)

    def testInferSmallLatin1(self):
        buf, md = self.check_infer('small-latin1.csv', prov=True, verbosity=0)

    def testInferSmallLatin9(self):
        buf, md = self.check_infer('small-latin9.csv', prov=True, verbosity=0)

    def testInferSmallWriteKw(self):
        buf, md = self.check_infer('small-write-kw.csv', prov=True,
                                   verbosity=0)

    def testInferSmallWriteSerial(self):
        buf, md = self.check_infer('small-write-serial.csv', prov=True,
                                   verbosity=0)

    def testInferSmall(self):
        buf, md = self.check_infer('small.csv', prov=True, verbosity=0)

    def testInferSmall2(self):
        buf, md = self.check_infer('small2.csv', prov=True, verbosity=0)

    def testInferStrings1(self):
        buf, md = self.check_infer('strings1.csv', prov=True, verbosity=0)

    def testInferTiny1cdPandas(self):
        buf, md = self.check_infer('tiny1cd-pandas.csv', prov=True,
                                   verbosity=0)

    def testInferTiny1cd(self):
        buf, md = self.check_infer('tiny1cd.csv', prov=True, verbosity=0)

    def testInferTiny1cd3(self):
        buf, md = self.check_infer('tiny1cd3.csv', prov=True, verbosity=0)

    def testInferTiny1cnPandas(self):
        buf, md = self.check_infer('tiny1cn-pandas.csv', prov=True,
                                   verbosity=0)

    def testInferTiny1cn(self):
        buf, md = self.check_infer('tiny1cn.csv', prov=True, verbosity=0)

    def testInferTiny1cn3(self):
        buf, md = self.check_infer('tiny1cn3.csv', prov=True, verbosity=0)

    def testInferTiny1ndDot(self):
        buf, md = self.check_infer('tiny1nd-dot.csv', prov=True, verbosity=0)

    def testInferTiny1ndNull(self):
        buf, md = self.check_infer('tiny1nd-NULL.csv', prov=True, verbosity=0)

    def testInferTiny1ndPandas(self):
        buf, md = self.check_infer('tiny1nd-pandas.csv', prov=True,
                                   verbosity=0)

    def testInferTiny1nd(self):
        buf, md = self.check_infer('tiny1nd.csv', prov=True, verbosity=0)

    def testInferTiny1nd3(self):
        buf, md = self.check_infer('tiny1nd3.csv', prov=True, verbosity=0)

    def testInferTiny1ndq(self):
        buf, md = self.check_infer('tiny1ndq.csv', prov=True, verbosity=0)

    def testInferTiny1nnPandas(self):
        buf, md = self.check_infer('tiny1nn-pandas.csv', prov=True,
                                   verbosity=0)

    def testInferTiny1nn(self):
        buf, md = self.check_infer('tiny1nn.csv', prov=True, verbosity=0)

    def testInferTiny1nn3(self):
        buf, md = self.check_infer('tiny1nn3.csv', prov=True, verbosity=0)

    def testInferTz(self):
        buf, md = self.check_infer('tz.csv', prov=True, verbosity=0)

    def testInferUsd(self):
        buf, md = self.check_infer('usd.csv', prov=True, verbosity=0)

    def testInferUsd2y(self):
        buf, md = self.check_infer('usd2y.csv', prov=True, verbosity=0)

    def testInferUsdt(self):
        buf, md = self.check_infer('usdt.csv', prov=True, verbosity=0)

    def testInferUsdt2y(self):
        buf, md = self.check_infer('usdt2y.csv', prov=True, verbosity=0)

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
        buf, md = self.check_infer('isodt.tsv', prov=True, verbosity=0)

    # .ssv file

    def testInferTiny1ndWeirdSsv(self):
        buf, md = self.check_infer('tiny1nd-weird.ssv', prov=True,
                                   verbosity=0)


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
