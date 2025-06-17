import datetime
import os
import re
import tempfile

from tdda.referencetest import ReferenceTestCase, tag

from tdda.serial.base import RE_ISO8601, URI
from tdda.serial.csvw import csvw_date_format_to_md_date_format
from tdda.serial.reader import (
    find_metadata_kind,
)


THISDIR = os.path.abspath(os.path.dirname(__file__))
TESTDATADIR = os.path.join(THISDIR, 'testdata')
EXAMPLESDIR = os.path.join(THISDIR, 'examples')

TMPDIR = tempfile.mkdtemp()

TDDASERIAL_PATTERNS = [
    r'^\s*"format": "http://tdda\.info/ns/tdda\.serial[.0-9/]*",?$',
    r'^\s*"writer": "tdda\.serial[-.0-9]*",?$',
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

    def test_find_metadata_priority(self):
        d = {
            'tdda.serial' : {'sep': ','},
            'pandas.read_csv' : {'sep': '|'},
            'csvw' : {'sep': '\t'},
            'e': 3
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
            'pandas.read_csv' : {'quote': '*'},
            'tdda.serial' : {'quote': "'"},
            'csvw' : {'quote': '|'},
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
                'A': {
                    'r': {
                        'tdda.serial': {
                            'quote_char': "'"
                        }
                    }
                }
            },
            'e': {
                'f': {
                    'g': 'bar',
                    'h': {
                        'i': {
                             'csvw': {
                                 'blah': 'blah'
                             }
                        }
                    },
                    'j': 2,
                    'pandas.read_csv': {
                        'sep': ','
                    }
                }
            }
        }
        kind, md = find_metadata_kind(d)
        self.assertEqual(kind, 'pandas.read_csv')  # least deep
        self.assertEqual(md, {'sep': ","})


def tiny_python_values(nulls=False):
    """
    Generate tiny 5x2 or 5x3 set of values for a DataFrame
    with Python booleans, integers, floats, strings and dates.

    If nulls is True, the second row (row 1) is all null
    and there are three rows.

    Otherwise, there are two, non-null rows.
    """
    values = {
        'b': [False, True],
        'i': [0, 1],
        'f': [0.5, 1.5],
        's': ['', 'a'],
#        'd': [datetime.date(1970, 1, 1), datetime.date(1999, 12, 31)]
        't': [datetime.datetime(1970, 1, 1), datetime.datetime(1999, 12, 31)]
    }
    if nulls:
        values = {
            k: v[:1] + [None] + v[1:]
            for k, v in values.items()
        }
    return values


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



if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
