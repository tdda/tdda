import datetime
import os
import re
import tempfile

from tdda.referencetest import ReferenceTestCase, tag

from tdda.serial.metadata import (
    RE_ISO8601,
    URI,
    SerialMetadata,
    FieldMetadata,
    DateFormat,
    NAMED_FORMAT_TO_STRFTIME,
    ISO8601_NAMED_FORMATS,
    is_iso8601_format,
)
from tdda.serial.csvw import csvw_date_format_to_serial
from tdda.serial.frictionless import frictionless_date_format_to_serial
from tdda.serial.pandasio import (
    to_pandas_date_format,
    pandas_date_format_to_serial,
)
from tdda.serial.reader import (
    find_metadata_kind,
)
from tdda.serial.utils import (
    find_associated_metadata_file,
    find_metadata_type_from_path,
)
from tdda.utils import TDDAError, testwarn


THISDIR = os.path.abspath(os.path.dirname(__file__))
TESTDATADIR = os.path.join(THISDIR, 'testdata')
EXAMPLESDIR = os.path.join(THISDIR, 'examples')
GLOBDIR = os.path.join(TESTDATADIR, 'globfiles')
REFTESTDATA = os.path.normpath(
    os.path.join(THISDIR, '..', 'constraints', 'testdata')
)

TMPDIR = tempfile.mkdtemp()

TDDASERIAL_PATTERNS = [
    r'^\s*"format": "http://tdda\.info/ns/tdda\.serial[.0-9/]*",?$',
    r'^\s*"(writer|dc:creator)": "tdda\.serial[-.0-9rc]*",?$',
]


THREE_FLAVOURS = ['tdda.serial', 'pandas.read_csv', 'pandas.DataFrame.to_csv']
PANDAS2 = ['pandas.read_csv', 'pandas.DataFrame.to_csv']


def tdpath(path):
    return os.path.join(TESTDATADIR, path)


def epath(path):
    """Examples path"""
    return os.path.join(EXAMPLESDIR, path)


def tmppath(name):
    return os.path.join(TMPDIR, name)


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
        map_date_format = csvw_date_format_to_serial
        self.assertEqual(map_date_format('yyyy-MM-dd'), 'iso8601')
        self.assertEqual(map_date_format('yyyyMMdd'), 'YYYYMMDD')
        self.assertEqual(map_date_format('dd-MM-yyyy'), 'DD-MM-YYYY')
        self.assertEqual(map_date_format('d-M-yyyy'), 'DD-MM-YYYY')
        self.assertEqual(map_date_format('MM-dd-yyyy'), 'MM-DD-YYYY')
        self.assertEqual(map_date_format('M-d-yyyy'), 'MM-DD-YYYY')
        self.assertEqual(map_date_format('dd/MM/yyyy'), 'DD/MM/YYYY')
        self.assertEqual(map_date_format('d/M/yyyy'), 'DD/MM/YYYY')
        self.assertEqual(map_date_format('MM/dd/yyyy'), 'MM/DD/YYYY')
        self.assertEqual(map_date_format('M/d/yyyy'), 'MM/DD/YYYY')
        self.assertEqual(map_date_format('dd.MM.yyyy'), 'DD.MM.YYYY')
        self.assertEqual(map_date_format('d.M.yyyy'), 'DD.MM.YYYY')
        self.assertEqual(map_date_format('MM.dd.yyyy'), 'MM.DD.YYYY')
        self.assertEqual(map_date_format('M.d.yyyy'), 'MM.DD.YYYY')

        self.assertEqual(map_date_format('yyyy-MM-ddTHH:mm:ss.S'), 'iso8601')
        self.assertEqual(map_date_format('yyyy-MM-ddTHH:mm:ss'), 'iso8601')
        self.assertEqual(
            map_date_format('yyyy-MM-ddTHH:mm'), 'YYYY-MM-DDTHH:MM'
        )

        self.assertEqual(map_date_format('yyyy-MM-dd HH:mm:ss.S'), 'iso8601')
        self.assertEqual(map_date_format('yyyy-MM-dd HH:mm:ss'), 'iso8601')
        self.assertEqual(
            map_date_format('yyyy-MM-dd HH:mm'), 'YYYY-MM-DD HH:MM'
        )

        self.assertEqual(
            map_date_format('dd-MM-yyyy HH:mm:ss.S'), 'DD-MM-YYYY HH:MM:SS.SSS'
        )
        self.assertEqual(
            map_date_format('MM-dd-yyyy HH:mm:ss'), 'MM-DD-YYYY HH:MM:SS'
        )
        self.assertEqual(map_date_format('dd-MM-yy HH:mm'), 'DD-MM-YY HH:MM')
        self.assertIsNone(map_date_format(''))

    def testFrictionlessDateFormatsMapping(self):
        f = frictionless_date_format_to_serial
        self.assertEqual(f(None, 'date'), DateFormat.ISO8601_DATE)
        self.assertEqual(f(None, 'datetime'), DateFormat.ISO8601_DATETIME)
        self.assertEqual(f(None), DateFormat.ISO8601_UNSPECIFIED)
        self.assertEqual(f('default', 'date'), DateFormat.ISO8601_DATE)
        self.assertEqual(f('default', 'datetime'), DateFormat.ISO8601_DATETIME)
        self.assertEqual(f('default'), DateFormat.ISO8601_UNSPECIFIED)
        self.assertIsNone(f('any', 'date'))
        self.assertIsNone(f('any', 'datetime'))
        self.assertEqual(f('%d/%m/%Y', 'date'), '%d/%m/%Y')
        self.assertEqual(
            f('%d/%m/%Y %H:%M:%S', 'datetime'), '%d/%m/%Y %H:%M:%S'
        )
        self.assertEqual(f('%Y-%m-%d', 'date'), '%Y-%m-%d')

    def testSingleDateFormat(self):
        # Nothing. Use ISO 8601
        isod = DateFormat.ISO8601_DATE
        isodt = DateFormat.ISO8601_DATETIME
        f1 = '%d/%m/%Y'
        f2 = '%d/%m/%Y %H:%M:%S'
        f3 = '%Y-%m-%d %H:%M:%S'
        f4 = '%Y-%m-%dT%H:%M:%S'

        m = SerialMetadata()
        self.assertEqual(m.single_date_format(), isodt)

        # dateformat set. Use that
        m = SerialMetadata(date_format=f1)
        self.assertEqual(m.single_date_format(), f1)

        d1 = FieldMetadata('d1', fieldtype='date', format=f1)
        d2 = FieldMetadata('d2', fieldtype='date', format=f1)
        dt1 = FieldMetadata('dt1', fieldtype='datetime', format=f2)
        dt2 = FieldMetadata('dt2', fieldtype='datetime', format=f2)
        dt3 = FieldMetadata('dt3', fieldtype='datetime', format=f3)

        dt4 = FieldMetadata('dt4', fieldtype='datetime', format=f4)
        dt5 = FieldMetadata('dt5', fieldtype='datetime', format=f4)

        dt6 = FieldMetadata('dt6', fieldtype='datetime', format=isodt)
        dt7 = FieldMetadata('dt7', fieldtype='datetime', format=isodt)

        # Default and fields: default wins
        m = SerialMetadata(date_format=f1, fields=[dt1, dt2])
        self.assertEqual(m.single_date_format(), f1)

        # Same format for multiple fields
        m = SerialMetadata(fields=[dt4, dt5])
        self.assertEqual(m.single_date_format(), f4)

        # Most frequent, no ties wins
        m = SerialMetadata(fields=[dt1, dt4, dt5])
        warn, buf = testwarn()
        self.assertEqual(m.single_date_format(warner=warn), f4)
        self.assertEqual(
            buf, ['Multiple data formats; using mode (%Y-%m-%dT%H:%M:%S).']
        )

        # iso8601 beats ties
        m = SerialMetadata(fields=[dt1, dt4, dt5, dt6, dt7])
        warn, buf = testwarn()
        self.assertEqual(m.single_date_format(warner=warn), isodt)
        self.assertEqual(buf, ['Multiple data formats; using ISO 8601.'])

        # Ties result in iso8601
        m = SerialMetadata(fields=[dt1, dt4])
        warn, buf = testwarn()
        self.assertEqual(m.single_date_format(warner=warn), isodt)
        self.assertEqual(buf, ['Multiple data formats; using ISO 8601.'])

    def testIsIso8601Format(self):
        # Boolean values, including names
        self.assertEqual(is_iso8601_format('iso8601'), True)
        self.assertEqual(is_iso8601_format('iso8601-date'), True)
        self.assertEqual(is_iso8601_format('iso8601-datetime'), True)
        self.assertEqual(is_iso8601_format('iso8601-datetime-tz'), True)

        self.assertEqual(is_iso8601_format('ISO8601'), True)
        self.assertEqual(is_iso8601_format('ISO8601-date'), True)
        self.assertEqual(is_iso8601_format('ISO8601-datetime'), True)
        self.assertEqual(is_iso8601_format('ISO8601-datetime-TZ'), True)

        self.assertEqual(is_iso8601_format('iso-8601'), False)
        self.assertEqual(is_iso8601_format('iso-8601date'), False)
        self.assertEqual(is_iso8601_format('iso8601-date-time'), False)
        self.assertEqual(is_iso8601_format('iso8601-datetime-zone'), False)

        self.assertEqual(is_iso8601_format('%Y-%m-%d'), True)
        self.assertEqual(is_iso8601_format('%Y/%m/%d'), True)
        self.assertEqual(is_iso8601_format('%Y.%m.%d'), True)

        self.assertEqual(is_iso8601_format('%Y-%m-%d %H:%M:%S'), True)
        self.assertEqual(is_iso8601_format('%Y/%m/%dT%H:%M:%S'), True)
        self.assertEqual(is_iso8601_format('%Y.%m.%d %H:%M:%S.%f'), True)
        self.assertEqual(is_iso8601_format('%Y.%m.%dT%H:%M:%S.%f'), True)

        self.assertEqual(is_iso8601_format('%Y-%m-%d%h:%m:%s'), False)
        self.assertEqual(is_iso8601_format('%Y/%m/%d:%h:%m:%s'), False)
        self.assertEqual(is_iso8601_format('%Y.%m.%d %h:%m:%s,%f'), False)
        self.assertEqual(is_iso8601_format('%Y.%m.%dT%h:%m:%s-%f'), False)

        # Boolean values, excluding names
        self.assertEqual(is_iso8601_format('iso8601', inc_names=False), False)
        self.assertEqual(
            is_iso8601_format('iso8601-date', inc_names=False), False
        )
        self.assertEqual(
            is_iso8601_format('iso8601-datetime', inc_names=False), False
        )
        self.assertEqual(
            is_iso8601_format('iso8601-datetime-tz', inc_names=False), False
        )

        self.assertEqual(is_iso8601_format('%Y-%m-%d', inc_names=False), True)

        # Specific values
        self.assertEqual(
            is_iso8601_format('iso8601', return_specific=True), 'iso8601'
        )
        self.assertEqual(
            is_iso8601_format('iso8601-date', return_specific=True),
            'iso8601-date',
        )
        self.assertEqual(
            is_iso8601_format('iso8601-datetime', return_specific=True),
            'iso8601-datetime',
        )
        self.assertEqual(
            is_iso8601_format('iso8601-datetime-tz', return_specific=True),
            'iso8601-datetime-tz',
        )

        self.assertEqual(
            is_iso8601_format('%Y-%m-%d', return_specific=True), 'iso8601-date'
        )

        self.assertEqual(
            is_iso8601_format('%Y-%m-%d', return_specific=True), 'iso8601-date'
        )

        self.assertEqual(
            is_iso8601_format('%Y/%m/%dT%H:%M:%S', return_specific=True),
            'iso8601-datetime',
        )

        # Timezones not actually handled yet.

    def testSingleNullIndicator(self):
        m = SerialMetadata()
        self.assertEqual(m.single_null_indicator(), '')
        self.assertEqual(m.single_null_indicator(default='.'), '.')

        m = SerialMetadata(null_indicator='.')
        self.assertEqual(m.single_null_indicator(), '.')
        self.assertEqual(m.single_null_indicator(default='NULL'), '.')

        m = SerialMetadata(null_indicator=['.', 'null'])
        warner, buf = testwarn()
        self.assertEqual(m.single_null_indicator(warner=warner), '.')
        self.assertEqual(buf, ['Multiple null indicators: using first (".").'])

        warner, buf = testwarn()
        self.assertEqual(
            m.single_null_indicator(default='NULL', warner=warner), '.'
        )
        self.assertEqual(buf, ['Multiple null indicators: using first (".").'])

        f1 = FieldMetadata('f1', fieldtype='int', null_indicator='.')
        f2 = FieldMetadata('f2', fieldtype='int', null_indicator='.')
        f3 = FieldMetadata('f3', fieldtype='int', null_indicator='')
        f4 = FieldMetadata('f4', fieldtype='int', null_indicator=['', '.'])
        f5 = FieldMetadata('f5', fieldtype='int', null_indicator='NULL')

        m = SerialMetadata(fields=[f1])
        self.assertEqual(m.single_null_indicator(), '.')

        m = SerialMetadata(fields=[f1, f2, f3])
        warner, buf = testwarn()
        self.assertEqual(m.single_null_indicator(warner=warner), '.')
        self.assertEqual(buf, ['Multiple null indicators; using mode (".").'])

        m = SerialMetadata(fields=[f1, f3])
        warner, buf = testwarn()
        self.assertEqual(m.single_null_indicator(warner=warner), '')
        self.assertEqual(buf, ['Multiple null indicators; using "".'])

        m = SerialMetadata(null_indicator='nil', fields=[f1, f3])
        warner, buf = testwarn()
        self.assertEqual(m.single_null_indicator(warner=warner), 'nil')
        self.assertEqual(buf, [])


class TestFindMetadata(ReferenceTestCase):
    def test_find_metadata_empty(self):
        kind, md = find_metadata_kind({})
        self.assertIsNone(kind)
        self.assertIsNone(md)

        kind, md = find_metadata_kind([{}])
        self.assertIsNone(kind)
        self.assertIsNone(md)

        kind, md = find_metadata_kind([])
        self.assertIsNone(kind)
        self.assertIsNone(md)

    def test_find_metadata_one_level(self):
        d = {'@context': URI.CSVW}
        kind, md = find_metadata_kind(d)
        self.assertEqual(kind, 'csvw')
        self.assertEqual(md, d)

        d = {'tdda.serial': {}}
        kind, md = find_metadata_kind(d)
        self.assertEqual(kind, 'tdda.serial')
        self.assertEqual(md, {})

        d = {'pandas.read_csv': {'sep': '|'}}
        kind, md = find_metadata_kind(d)
        self.assertEqual(kind, 'pandas.read_csv')
        self.assertEqual(md, {'sep': '|'})

    def testDetectMetadataKindFromPath(self):
        # CSVW
        self.assertEqual(
            find_metadata_type_from_path('foo-metadata.json'),
            ('csvw', ('foo', 'metadata', None, '.json')),
        )
        self.assertEqual(
            find_metadata_type_from_path('foo-csvmetadata.json'),
            ('csvw', ('foo', 'csvmetadata', 'csv', '.json')),
        )
        self.assertEqual(
            find_metadata_type_from_path('foo-csv-metadata.json'),
            ('csvw', ('foo', 'csv-metadata', 'csv-', '.json')),
        )

        self.assertEqual(
            find_metadata_type_from_path('foo.metadata.json'),
            ('csvw', ('foo', 'metadata', None, '.json')),
        )
        self.assertEqual(
            find_metadata_type_from_path('foo.csvmetadata.json'),
            ('csvw', ('foo', 'csvmetadata', 'csv', '.json')),
        )
        self.assertEqual(
            find_metadata_type_from_path('foo.csv.metadata.json'),
            ('csvw', ('foo', 'csv.metadata', 'csv.', '.json')),
        )

        self.assertEqual(
            find_metadata_type_from_path('foo.csv-metadata.json'),
            ('csvw', ('foo', 'csv-metadata', 'csv-', '.json')),
        )

        self.assertEqual(
            find_metadata_type_from_path('foo.bar-baz.csv-metadata.json'),
            ('csvw', ('foo.bar-baz', 'csv-metadata', 'csv-', '.json')),
        )
        self.assertEqual(
            find_metadata_type_from_path('foo-bar.baz.csv-metadata.json'),
            ('csvw', ('foo-bar.baz', 'csv-metadata', 'csv-', '.json')),
        )

        self.assertEqual(
            find_metadata_type_from_path('foo.resource.json'),
            ('frictionless', ('foo', 'resource', '.json')),
        )
        self.assertEqual(
            find_metadata_type_from_path('foo.package.json'),
            ('frictionless', ('foo', 'package', '.json')),
        )
        self.assertEqual(
            find_metadata_type_from_path('foo.schema.json'),
            ('frictionless', ('foo', 'schema', '.json')),
        )

        self.assertEqual(
            find_metadata_type_from_path('foo-resource.json'),
            ('frictionless', ('foo', 'resource', '.json')),
        )
        self.assertEqual(
            find_metadata_type_from_path('foo-package.json'),
            ('frictionless', ('foo', 'package', '.json')),
        )
        self.assertEqual(
            find_metadata_type_from_path('foo-schema.json'),
            ('frictionless', ('foo', 'schema', '.json')),
        )

        self.assertEqual(
            find_metadata_type_from_path('foo.bar-baz.resource.json'),
            ('frictionless', ('foo.bar-baz', 'resource', '.json')),
        )
        self.assertEqual(
            find_metadata_type_from_path('foo-bar.baz.resource.json'),
            ('frictionless', ('foo-bar.baz', 'resource', '.json')),
        )

        self.assertEqual(
            find_metadata_type_from_path('foo.json'), (None, None)
        )

    def test_find_metadata_priority(self):
        d = {
            'tdda.serial': {'sep': ','},
            'pandas.read_csv': {'sep': '|'},
            'csvw': {'sep': '\t'},
            'e': 3,
        }
        kind, md = find_metadata_kind(d)
        self.assertEqual(kind, 'tdda.serial')
        self.assertEqual(md, {'sep': ','})

        # preferred

        kind, md = find_metadata_kind(d, 'pandas.read_csv')
        self.assertEqual(kind, 'pandas.read_csv')
        self.assertEqual(md, {'sep': '|'})

        kind, md = find_metadata_kind(d, 'csvw')
        self.assertEqual(kind, 'csvw')
        self.assertEqual(md, {'sep': '\t'})

        kind, md = find_metadata_kind(d, 'tdda.serial')
        self.assertEqual(kind, 'tdda.serial')
        self.assertEqual(md, {'sep': ','})

    def test_find_metadata_two_levels(self):
        c = {
            'pandas.read_csv': {'quote': '*'},
            'tdda.serial': {'quote': "'"},
            'csvw': {'quote': '|'},
        }
        d = {
            'a': 'foo',
            'b': 2,
            'c': c,
        }
        kind, md = find_metadata_kind(d)
        self.assertEqual(kind, 'tdda.serial')
        self.assertEqual(md, {'quote': "'"})

        # preferred

        kind, md = find_metadata_kind(d, 'pandas.read_csv')
        self.assertEqual(kind, 'pandas.read_csv')
        self.assertEqual(md, {'quote': '*'})

        kind, md = find_metadata_kind(d, 'csvw')
        self.assertEqual(kind, 'csvw')
        self.assertEqual(md, {'quote': '|'})

        kind, md = find_metadata_kind(d, 'tdda.serial')
        self.assertEqual(kind, 'tdda.serial')
        self.assertEqual(md, {'quote': "'"})

    def test_find_metadata_deep(self):
        d = {
            'a': 1,
            'b': {
                'c': 1,
                'd': 'foo',
                'A': {'r': {'tdda.serial': {'quote_char': "'"}}},
            },
            'e': {
                'f': {
                    'g': 'bar',
                    'h': {'i': {'csvw': {'blah': 'blah'}}},
                    'j': 2,
                    'pandas.read_csv': {'sep': ','},
                }
            },
        }
        kind, md = find_metadata_kind(d)
        self.assertEqual(kind, 'pandas.read_csv')  # least deep
        self.assertEqual(md, {'sep': ','})


def ntype(name):
    d = {
        'b': 'boolean',
        'i': 'Int64',
        'f': 'float',
        'r': 'float',
        's': 'string',
        'd': 'datetime64[ns]',
        't': 'datetime64[ns]',
    }
    return d[name[:1].lower()]


def remove_common_key_vals(left, right):
    for k in list(left.keys()):
        if left[k] == right[k]:
            del left[k]
            del right[k]


class TestToPandasDateFormat(ReferenceTestCase):
    def testNoneReturnsNone(self):
        self.assertIsNone(to_pandas_date_format(None))
        self.assertIsNone(to_pandas_date_format(None, for_write=True))

    def testISO8601NamedFormatsRead(self):
        # All ISO8601 named formats → 'ISO8601' on read
        for fmt in ISO8601_NAMED_FORMATS:
            self.assertEqual(
                to_pandas_date_format(fmt),
                'ISO8601',
                f'format {fmt!r} should give ISO8601 on read',
            )

    def testISO8601NamedFormatsWrite(self):
        # All ISO8601 named formats → canonical strftime on write
        for fmt in ISO8601_NAMED_FORMATS:
            result = to_pandas_date_format(fmt, for_write=True)
            self.assertEqual(
                result,
                NAMED_FORMAT_TO_STRFTIME[fmt],
                f'format {fmt!r} should give strftime on write',
            )

    def testYYYYDateAndLiteralDateFormats(self):
        # yyyydate and literaldate Euro/US formats → canonical strftime
        cases = {
            'DD/MM/YYYY': '%d/%m/%Y',
            'DD/MM/YYYY HH:MM:SS': '%d/%m/%Y %H:%M:%S',
            'DD/MM/YY': '%d/%m/%y',
            'MM/DD/YYYY': '%m/%d/%Y',
            'MM/DD/YYYY HH:MM:SS': '%m/%d/%Y %H:%M:%S',
            'MM/DD/YY': '%m/%d/%y',
            '31/12/2000': '%d/%m/%Y',
            '31/12/2000 12:34:56': '%d/%m/%Y %H:%M:%S',
            '31/12/00': '%d/%m/%y',
            '12/31/2000': '%m/%d/%Y',
            '12/31/2000 12:34:56': '%m/%d/%Y %H:%M:%S',
            '12/31/00': '%m/%d/%y',
        }
        for fmt, expected in cases.items():
            self.assertEqual(
                to_pandas_date_format(fmt), expected, f'format {fmt!r} read'
            )
            self.assertEqual(
                to_pandas_date_format(fmt, for_write=True),
                expected,
                f'format {fmt!r} write',
            )

    def testSpecificStrftimePassthrough(self):
        # Specific strftime strings pass through unchanged
        for fmt in ('%d/%m/%Y', '%Y%m%d', '%m-%d-%Y', '%d.%m.%Y %H:%M:%S'):
            self.assertEqual(to_pandas_date_format(fmt), fmt)
            self.assertEqual(to_pandas_date_format(fmt, for_write=True), fmt)

    def testUnspecifiedRaisesNotImplemented(self):
        self.assertRaises(
            NotImplementedError,
            to_pandas_date_format,
            DateFormat.EURO_UNSPECIFIED,
        )
        self.assertRaises(
            NotImplementedError,
            to_pandas_date_format,
            DateFormat.US_UNSPECIFIED,
        )

    def testPandasDateFormatToSerial(self):
        self.assertEqual(
            pandas_date_format_to_serial('ISO8601'),
            DateFormat.ISO8601_UNSPECIFIED,
        )
        self.assertEqual(pandas_date_format_to_serial('%d/%m/%Y'), '%d/%m/%Y')
        self.assertEqual(
            pandas_date_format_to_serial('%Y-%m-%dT%H:%M:%S'),
            '%Y-%m-%dT%H:%M:%S',
        )


class TestLegacyDatetimeFormat(ReferenceTestCase):
    def testDatetimeFormatAlias(self):
        # datetime_format is accepted as legacy alias for date_format
        m = SerialMetadata(datetime_format='iso8601')
        self.assertEqual(m.date_format, 'iso8601')

    def testDateFormatWinsOverDatetimeFormat(self):
        # date_format takes precedence over datetime_format
        m = SerialMetadata(date_format='eu-date', datetime_format='iso8601')
        self.assertEqual(m.date_format, 'eu-date')


class TestWildcardSerialLookup(ReferenceTestCase):
    def gpath(self, name):
        return os.path.join(GLOBDIR, name)

    def testSimpleWildcard(self):
        result = find_associated_metadata_file(self.gpath('foobar.csv'))
        self.assertEqual(result, self.gpath('foo@.serial'))

    def testWildcardDifferentExtension(self):
        result = find_associated_metadata_file(self.gpath('fooqux.txt'))
        self.assertEqual(result, self.gpath('foo@.serial'))

    def testTwoWildcards(self):
        result = find_associated_metadata_file(self.gpath('pre1mid2.csv'))
        self.assertEqual(result, self.gpath('pre@mid@.serial'))

    def testExactBeatsWildcard(self):
        result = find_associated_metadata_file(self.gpath('exact.csv'))
        self.assertEqual(result, self.gpath('exact.serial'))

    def testAmbiguousWildcard(self):
        with self.assertRaisesRegex(TDDAError, 'Ambiguous wildcard'):
            find_associated_metadata_file(
                self.gpath('foobaz.csv'), raise_error=True
            )

    def testNoMatch(self):
        result = find_associated_metadata_file(self.gpath('nomatch.csv'))
        self.assertIsNone(result)


if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
