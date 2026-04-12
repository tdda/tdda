from collections import namedtuple

from tdda.referencetest import ReferenceTestCase, tag

from tdda.serial.converter import SerialConverter
from tdda.serial.csvw import CSVWMetadata
from tdda.serial.frictionless import (
    FrictionlessMetadata,
)
from tdda.serial.metadata import FieldType
from tdda.serial.dateutils import infer_date_format_from_strings
from tdda.serial.infer import (
    analyse_values,
    careful_split,
    infer_format_from_flat_file,
)


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

    def check_infer(self, name, **kw):
        stem = name.rsplit('.', 1)[0]
        outname = stem + '-prov-inferred.serial'
        Warn, buf = testwarn()
        md = infer_format_from_flat_file(tdpath(name), warner=Warn, **kw)
        outpath = tmppath(outname)
        with open(outpath, 'w') as f:
            f.write(md.to_json())
        self.assertFileCorrect(outpath, tdpath(outname), ignore_lines=self.IGL)
        return buf

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
        buf = self.check_infer('allformats.csv', verbosity=0)
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


if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
