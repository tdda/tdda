import copy
import json
import re
import sys

from collections import Counter
import csv

from tdda.version import version as VERSION
from tdda.serial.constants import URI, TDDASERIAL
from tdda.utils import listify, nvl, warn, swap_ext, error

class TDDASerialError(Exception):
    pass


class MISSING:
    ERROR = 2
    WARNING = 1
    ALLOWED = 0


class FieldType:
    BOOL = 'bool'

    INT = 'int'
    FLOAT = 'float'
    NUMBER = 'number'

    DATE = 'date'
    DATETIME = 'datetime'
    DATETIME_WITH_TIMEZONE = 'datetime_tz'
    ISO8601 = 'iso8601'

    STRING = 'string'


class DateFormat:
    ISO8601_DATE = 'iso8601-date'
    ISO8601_DATETIME = 'iso8601-datetime'
    ISO8601_DATETIME_TZ = 'iso8601-datetime-tz'
    ISO8601_UNSPECIFIED = 'iso8601'

    EURO_DATE = 'eu-date'
    EURO_DATETIME = 'eu-datetime'


ISO8601_NAMED_FORMATS = {
    DateFormat.ISO8601_DATE,
    DateFormat.ISO8601_DATETIME,
    DateFormat.ISO8601_DATETIME_TZ,
    DateFormat.ISO8601_UNSPECIFIED,
}


class Defaults:
    ENCODING = 'UTF-8'
    DELIMITER = ','
    QUOTE_CHAR = '"'
    ESCAPE_CHAR = '\\'
    STUTTER = False
    HEADER_ROW_COUNT = 1
    NULL_INDICATOR = ''
    DATE_FORMAT = DateFormat.ISO8601_DATE
    DATETIME_FORMAT = DateFormat.ISO8601_DATETIME


CONTEXT_KEY = '@context'
RE_ISO8601 = re.compile(r'^%Y.%m.%d([T ]%H.%M.%S(\.%f)?)?$')


# Allowed keys in .serial files
METADATA_FLAVOURS = [
    TDDASERIAL.key,
    'csvw',
    'pandas.read_csv',
    'polars.read_csv',
]



METADATA_FLAVOUR_MAP = {
    'tdda.serial': 'tdda.serial',
    'pandas.read_csv': 'pandas.read_csv',
    'pandas.DataFrame.to_csv': 'pandas.DataFrame.to_csv',
    'polars.read_csv': 'polars.write_csv',
    'polars.DataFrame.to_csv': 'polars.DataFrame.to_csv',
    'csvw': 'csvw',
    'python.csv.reader': 'python.csv.reader',
    'python.csv.writer': 'python.csv.writer',

    '.': 'tdda.serial',
    'pd.r': 'pandas.read_csv',
    'pd.w': 'pandas.DataFrame.to_csv',
    'pl.r': 'polars.read_csv',
    'pl.w': 'polars.DataFrame.to_csv',
    'csv.r': 'python.csv.reader',
    'csv.w': 'python.csv.writer',
}


VERBOSITY = 2     # show errors and warnings. 1 for errors only. 0 for none
                  # 3 for extra information

FIELDTYPES = tuple(FieldType.__dict__.values())

QUOTING_CODES = None
QUOTING_NAMES = None


class FieldMetadata:
    """
    Container for data about a field (column) in a serial data source
    such as CSV file

    Args:
        name:   Name of the field/column. This need not be the same as the
                name in the file. MANDATORY.

        fieldtype:  the type of the field. Must be one of the values
                    in FIELDTYPES. MANDATORY.

        csvname: Name of the column in the file. OPTIONAL.

        format:  Format of the field in the file.
                 Used mainly with date and datetime columns.
                 OPTIONAL

        null_indicator: values to be interpreted as NULL (missing/NA) values.
                     OPTIONAL.


    """
    def __init__(self, name, fieldtype=None, csvname=None,
                 format=None, null_indicator=None,
                 true_values=None, false_values=None,
                 allow_extras=False, description=None, **kw):
        self.name = name
        self.csvname = csvname or name
        self.fieldtype = fieldtype
        self.altnames = None
        self.format = format
        self.null_indicator = null_indicator
        self.true_values = listify(true_values)
        self.false_values = listify(false_values)
        self.description = description

        for k, v in kw.items():
            if allow_extras:
                self.__dict__[k] = v
            else:
                msg = f'Unexpected kwarg to FieldMetadata for {name}: "{k}"'
                raise KeyError(msg)

        self._errors = []
        self._warnings = []

        self.valid = None

    def get_val(self, d, k, missing=MISSING.ALLOWED):
        if not k in d:
            msg = f'Key "{k}" not found for field {self.name}'
            if missing == MISSING.ERROR:
                self._errors.append(msg)
            elif missing == MISSING.WARNING:
                self._warnings.append(msg)
            elif missing != MISSING.ALLOWED:
                raise TDDASerialError(
                    f'Unknown value "{missing}" for missing'
                )
        return d.get(k, None)

    def validate(self):
        if self.fieldtype not in FIELDTYPES:
            self._errors.append(
                f'Unknown field type "{self.fieldtype}" for field {self.name}'
            )

    def unobjectify(self):
        d = {k: unobjectify(v) for k, v in self.__dict__.items()
                if nonnull(v)}
        if d['csvname'] == d['name']:
            del d['csvname']
        return d

    def __deepcopy__(self, memo):
        md = FieldMetadata(self.name)
        for k, v in self.__dict__.items():
            if not k.startswith('_'):
                md.__dict__[k] = copy.deepcopy(v, memo)
        return md

    def __repr__(self):
        parts = ', '.join(f'{k}={repr(v)}'
                               for k, v in self.__dict__.items()
                               if v is not None and v != [])
        return f'FieldMetadata({parts})'


class SerialMetadata:
    def __init__(self,
        fields=None,
        path=None,
        encoding=None,
        delimiter=None,
        quote_char=None,
        escape_char=None,
        stutter_quotes=None,
        date_format=None,
        datetime_format=None,
        null_indicator=None,
        header_row_count=None,
        header_row=None,
        quoting=None,
        decimal_point=None,
        dps=None,
        accept_percentages_as_floats = None,
        map_missing_trailing_cols_to_null = None,
        verbosity=VERBOSITY,
        libs=None,
        source=None,
        extra_kwargs='warn',
        **kw
    ):
        if kw:
            if extra_kwargs in ('error', 'warn'):
                from pprint import pformat
                s = pformat(kw)
                report = error if extra_kwargs == 'error' else warn
                report(f'Unexpected arguments for Serial Metadata:\n{s}')
        if isinstance(fields, list):
            self.fields = fields
            self._fields_as_list = True
        else:
            self.fields = []
            if isinstance(fields, dict):
                for extname, f in fields.items():
                    f['csvname'] = extname
                    self.fields.append(f)
            self._fields_as_list = False
        self.path = path
        self.encoding = encoding
        self.delimiter = delimiter
        self.quote_char = quote_char
        self.escape_char = escape_char
        self.stutter_quotes = stutter_quotes
        self.date_format = date_format
        self.null_indicator = null_indicator

        self.accept_percentages_as_floats = accept_percentages_as_floats
        self.map_missing_trailing_cols_to_null = (
            map_missing_trailing_cols_to_null
        )

        self.header_row_count = header_row_count
        self.header_row = header_row
        self.comment_prefix = None
        self.line_terminators = None
        self.skip_blank_rows = None
        self.skip_initial_space = None
        self.skip_columns = None
        self.skip_rows = None
        self.quoting = quoting_as_name(quoting)
        self.decimal_point = decimal_point
        self.dps = dps

        self.libs = libs or {}

        self._errors = []
        self._warnings = []

        self.metadata_source = None
        self.metadata_source_path = None
        self.valid = None
        self._verbosity = verbosity

        if self.header_row_count is None and self.header_row:
            self.header_row_count = 1
        if self.header_row is None and header_row_count:
            self.header_row = 0

#        self.metametadata = {
#            'creationhash': ''
#        }

        if isinstance(self.fields, list):
            self.fields = [(FieldMetadata(**f) if isinstance(f, dict) else f)
                           for f in self.fields]

        self._source = source


    def error(self, msg):
        self._errors.append(msg)

    def warn(self, msg):
        self._warnings.append(msg)

    def get_val(self, d, k, missing=MISSING.ALLOWED):
        if not k in d:
            msg = f'Key "{k}" not found in file metadata.'
            if missing == MISSING.ERROR:
                self.error(msg)
            elif missing == MISSING.WARNING:
                self.warn(msg)
            elif missing != MISSING.ALLOWED:
                raise TDDASerialError(
                    f'Unknown value "{missing}" for missing.'
                )
        return d.get(k, None)

    def validate(self):
        valid = True
        if self._verbosity > 0:
            for msg in self._errors:
                print(f'** FATAL ERROR: {msg}', file=sys.stderr)
                valid = False
            for field in self.fields:
                field.validate()
                for msg in field._errors:
                    print(f'** FATAL ERROR: {msg}', file=sys.stderr)
                    valid = False
        if self._verbosity > 1:
            for msg in self._warnings:
                print(f'** WARNING: {msg}', file=sys.stderr)
            for field in self.fields:
                for msg in field._warnings:
                    print(f'** WARNING: {msg}', file=sys.stderr)

        self.valid = valid

    def unobjectify(self):
        d = {
            'format': URI.TDDASERIAL,
            'writer': writer(),
        }
        m = {
            k: unobjectify(v) for k, v in self.__dict__.items()
                                  if not k.startswith('_')
                                  and k != 'libs'
                                  and nonnull(v)
        }
        nulls = m.get('null_indicator')
        quoting = m.get('quoting')
        if quoting:
            m['quoting'] = quoting_as_name(quoting)
        if type(nulls) == list and len(nulls) == 1:
            m['null_indicator'] = nulls[0]
        if m:
            d[TDDASERIAL.key] = m

        for (lib, params) in self.libs.items():
            d[lib] = {
                k: unobjectify(v)
                for (k, v) in params.items()
            }
        return d

    def to_json(self, indent=4):
        return json.dumps(self.unobjectify(), indent=indent)

    def write(self, path, use_serial_ext=True, verbose=0):
        """
        Writes metadata to file.

        Args:
            path: path to write to. If this does not end in '.serial'
                  is will be changed to .serial unless keep_ext is set to True

            use_serial_ext: Set to True to keep the extension provided in path.
        """
        outpath = swap_ext(path, '.serial') if use_serial_ext else path
        with open(outpath, 'w') as f:
            f.write(self.to_json())
        if verbose:
            print(f'Written {outpath}.')

    def single_date_format(self, warner=None):
        """
        Get a single date/time format from serial metadata.
        This is typically needed for write parameters.

        Roughly this:
            Uses the default, if set
            Otherwise looks at fields:
                If there's a mode it uses that
                If there's a tied, it uses iso8601datetime
        """
        Warn = nvl(warner, warn)
        default = DateFormat.ISO8601_DATETIME
        if self.date_format:
            return self.date_format
        formats = Counter()
        for f in self.fields:
            if f.fieldtype.startswith('date') and f.format:
                fmt = f.format
                if fmt and fmt.startswith('iso'):
                    fmt = default
                formats[fmt] += 1
        if len(formats) == 1:
            return list(formats)[0]
        elif len(formats) == 0:
            return default

        m = max(v for v in formats.values())
        formats = {k: v for k, v in formats.items() if v == m}
        if len(formats) == 1:
            mode = list(formats)[0]
            Warn(f'Multiple data formats; using mode ({mode}).')
            return mode
        else:
            Warn(f'Multiple data formats; using ISO 8601.')
            return default

    def single_null_indicator(self, default='', warner=None):
        """
        Get a single null indicator (for writing, mostly)
        """
        Warn = nvl(warner, warn)
        if self.null_indicator is None:
            # look at fields
            nulls = Counter()
            for f in self.fields:
                N = f.null_indicator
                if N is not None:
                    if isinstance(N, str):
                        nulls[N] += 1
                    else:
                        for null in N:
                            nulls[null] += 1
            if len(nulls) == 0:
                return default
            elif len(nulls) == 1:
                return list(nulls)[0]
            else:
                m = max(v for v in nulls.values())
                nulls = {k: v for k, v in nulls.items() if v == m}
                if len(nulls) == 1:
                    mode = list(nulls)[0]
                    Warn(f'Multiple null indicators; using mode ("{mode}").')
                    return mode
                else:
                    null = sorted(list(nulls))[0]
                    Warn(f'Multiple null indicators; using "{null}".')
                    return null

        elif isinstance(self.null_indicator, str):
            return self.null_indicator
        elif len(self.null_indicator) == 0:
            return default
        elif len(self.null_indicator) == 1:
            return self.null_indicator[0]
        else:  # multiple null indicators
            null = self.null_indicator[0]
            Warn(f'Multiple null indicators: using first ("{null}").')
            return null

    def __deepcopy__(self, memo):
        md = SerialMetadata()
        for k, v in self.__dict__.items():
            if not k.startswith('_'):
                md.__dict__[k] = copy.deepcopy(v, memo)
        return md

    def copy_serial(self, inc_libs=False):
        md = SerialMetadata()
        exclusions = [] if not inc_libs else ['libs']
        for k, v in self.__dict__.items():
            if not k.startswith('_') and not k in exclusions:
                md.__dict__[k] = copy.deepcopy(v)
        return md

    def __str__(self):
        return self.to_json()


def unobjectify(o):
    if o is None or type(o) in (bool, int, float, str):
        return o
    if isinstance(o, list) or isinstance(o, tuple):
        return [unobjectify(v) for v in o if nonnull(v)]
    if isinstance(o, dict):
        return {k: unobjectify(v) for k, v in o.items() if nonnull(v)}
    if hasattr(o, 'unobjectify'):
        return o.unobjectify()
    if o.__class__.__name__.endswith('DataTypeClass'):  # Polars Datatype
        return str(o)
    error(
        'Attempt to unobjectify unexpected type.\n'
        f'Type: {type(o)}: Value: {repr(o)}'
    )


def nonnull(v):
    """
    test value v for whether it should be dumped.
    """
    return v is not None and v != [] and v != () and v != {}


def writer():
    return f'{TDDASERIAL.key}-{VERSION}'


def is_iso8601_format(fmt, inc_names=True, return_specific=False):
    if inc_names:
        if fmt.lower() in ISO8601_NAMED_FORMATS:
            return fmt.lower() if return_specific else True
    m = re.match(RE_ISO8601, fmt)
    if m:
        if return_specific:
            if m.group(1):
                return DateFormat.ISO8601_DATETIME
            else:
                return DateFormat.ISO8601_DATE
        else:
            return True
    else:
        return False


def get_quoting_codes():
    global QUOTING_CODES, QUOTING_NAMES

    QUOTING_CODES = {
        k: v for k, v in csv.__dict__.items()
        if k.startswith('QUOTE_')
    }
    QUOTING_CODES['STRING_ONLY'] = -1
    QUOTING_NAMES = {
        v: k for k, v in QUOTING_CODES.items()
    }


def quoting_as_code(name):
    if name is None:
        return None
    if QUOTING_CODES is None:
        get_quoting_codes()

    return name if isinstance(name, int) else QUOTING_CODES[name]


def quoting_as_name(code):
    if code is None:
        return None
    if QUOTING_NAMES is None:
        get_quoting_codes()

    return code if isinstance(code, str) else QUOTING_NAMES[code]


def get_metadata_flavour(flavour):
    out_flavour = METADATA_FLAVOUR_MAP.get((flavour or '.').lower())
    if flavour and out_flavour is None:
        error(f'Unknown metadata flavour: {flavour}')
    return out_flavour


def get_metadata_flavours(flavours):
    return [
       get_metadata_flavour(f)
       for f in (flavours or '.').strip().split(',')
    ]


