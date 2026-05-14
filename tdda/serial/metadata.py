import copy
import json
import re
import sys

from collections import Counter
import csv

from tdda.version import writable_version
from tdda.serial.constants import URI, TDDASERIAL
from tdda.serial.dateutils import (
    detect_format_style,
    strftime_to_literaldate,
    strftime_to_yyyydate,
    to_strftime,
)
from tdda.utils import listify, nvl, warn, swap_ext, error


class TDDASerialError(Exception):
    pass


class MISSING:
    ERROR = 2
    WARNING = 1
    ALLOWED = 0


class FieldType:
    """Constants for the supported field types in tdda.serial metadata.

    Use these values as the ``fieldtype`` parameter in
    :class:`FieldMetadata`.
    """

    BOOL = 'bool'

    INT = 'int'
    FLOAT = 'float'
    NUMBER = 'number'

    DATE = 'date'
    DATETIME = 'datetime'
    DATETIME_WITH_TIMEZONE = 'datetime_tz'
    TIME = 'time'
    ISO8601 = 'iso8601'

    STRING = 'string'


class DateFormat:
    """Named date/datetime format constants for tdda.serial metadata.

    These values can be used as the ``format`` parameter in
    :class:`FieldMetadata` for date and datetime fields, or as the
    ``date_format`` / ``datetime_format`` parameter in
    :class:`SerialMetadata`.

    ISO8601 formats accept any ISO variant on read and write the
    canonical form. European and US formats use slash-separated
    day/month/year or month/day/year respectively.
    """

    # ISO8601 generic (read any ISO variant, write canonical)
    ISO8601_DATE = 'iso8601-date'  # write: %Y-%m-%d
    ISO8601_DATETIME = 'iso8601-datetime'  # write: %Y-%m-%dT%H:%M:%S
    ISO8601_DATETIME_TZ = 'iso8601-datetime-tz'  # write: %Y-%m-%dT%H:%M:%S%z
    ISO8601_UNSPECIFIED = 'iso8601'  # write: %Y-%m-%dT%H:%M:%S

    # European generic (read canonical slash, write canonical slash)
    EURO_DATE = 'eu-date'  # write: %d/%m/%Y
    EURO_DATETIME = 'eu-datetime'  # write: %d/%m/%Y %H:%M:%S
    EURO_DATE_2Y = 'eu-date-2y'  # write: %d/%m/%y
    EURO_DATETIME_2Y = 'eu-datetime-2y'  # write: %d/%m/%y %H:%M:%S
    EURO_UNSPECIFIED = 'eu'  # not yet implemented

    # US generic (read canonical slash, write canonical slash)
    US_DATE = 'us-date'  # write: %m/%d/%Y
    US_DATETIME = 'us-datetime'  # write: %m/%d/%Y %H:%M:%S
    US_DATE_2Y = 'us-date-2y'  # write: %m/%d/%y
    US_DATETIME_2Y = 'us-datetime-2y'  # write: %m/%d/%y %H:%M:%S
    US_UNSPECIFIED = 'us'  # not yet implemented


class DateStyle:
    """Constants controlling the format style used for date strings.

    Used when converting between date format representations.
    LITERAL uses human-readable names (e.g. 'YYYY-MM-DD'), YYYY uses
    four-digit-year notation, PERCENT uses strftime % codes.
    """

    LITERAL = 'literal'
    YYYY = 'yyyy'
    PERCENT = 'percent'


def restyle_format(fmt, date_style):
    """Convert a format string to the requested DateStyle.

    ISO8601 named formats are left unchanged.
    Returns fmt unchanged if date_style is None.
    """
    if not fmt or not date_style:
        return fmt
    if fmt.lower().startswith('iso'):
        return fmt
    strftime = to_strftime(fmt)
    if date_style == DateStyle.PERCENT:
        return strftime
    if date_style == DateStyle.LITERAL:
        result = strftime_to_literaldate(strftime)
    else:
        result = strftime_to_yyyydate(strftime)
    return result if '%' not in result else strftime


# Canonical write strftime for each named generic format
NAMED_FORMAT_TO_STRFTIME = {
    DateFormat.ISO8601_DATE: '%Y-%m-%d',
    DateFormat.ISO8601_DATETIME: '%Y-%m-%dT%H:%M:%S',
    DateFormat.ISO8601_DATETIME_TZ: '%Y-%m-%dT%H:%M:%S%z',
    DateFormat.ISO8601_UNSPECIFIED: '%Y-%m-%dT%H:%M:%S',
}

# Specific strftime strings → generic named format (many to one)
STRFTIME_TO_NAMED_FORMAT = {
    # ISO8601 variants
    '%Y-%m-%d': DateFormat.ISO8601_DATE,
    '%Y/%m/%d': DateFormat.ISO8601_DATE,
    '%Y-%m-%d %H:%M:%S': DateFormat.ISO8601_DATETIME,
    '%Y-%m-%dT%H:%M:%S': DateFormat.ISO8601_DATETIME,
    '%Y/%m/%d %H:%M:%S': DateFormat.ISO8601_DATETIME,
    '%Y/%m/%dT%H:%M:%S': DateFormat.ISO8601_DATETIME,
    '%Y-%m-%d %H:%M:%S.%f': DateFormat.ISO8601_DATETIME,
    '%Y-%m-%dT%H:%M:%S.%f': DateFormat.ISO8601_DATETIME,
    # Euro variants
    '%d/%m/%Y': DateFormat.EURO_DATE,
    '%d-%m-%Y': DateFormat.EURO_DATE,
    '%d.%m.%Y': DateFormat.EURO_DATE,
    '%d/%m/%Y %H:%M:%S': DateFormat.EURO_DATETIME,
    '%d-%m-%Y %H:%M:%S': DateFormat.EURO_DATETIME,
    '%d.%m.%Y %H:%M:%S': DateFormat.EURO_DATETIME,
    '%d/%m/%y': DateFormat.EURO_DATE_2Y,
    '%d-%m-%y': DateFormat.EURO_DATE_2Y,
    '%d.%m.%y': DateFormat.EURO_DATE_2Y,
    '%d/%m/%y %H:%M:%S': DateFormat.EURO_DATETIME_2Y,
    '%d-%m-%y %H:%M:%S': DateFormat.EURO_DATETIME_2Y,
    '%d.%m.%y %H:%M:%S': DateFormat.EURO_DATETIME_2Y,
    # US variants
    '%m/%d/%Y': DateFormat.US_DATE,
    '%m-%d-%Y': DateFormat.US_DATE,
    '%m/%d/%Y %H:%M:%S': DateFormat.US_DATETIME,
    '%m-%d-%Y %H:%M:%S': DateFormat.US_DATETIME,
    '%m/%d/%y': DateFormat.US_DATE_2Y,
    '%m-%d-%y': DateFormat.US_DATE_2Y,
    '%m/%d/%y %H:%M:%S': DateFormat.US_DATETIME_2Y,
    '%m-%d-%y %H:%M:%S': DateFormat.US_DATETIME_2Y,
}

ISO8601_NAMED_FORMATS = {
    DateFormat.ISO8601_DATE,
    DateFormat.ISO8601_DATETIME,
    DateFormat.ISO8601_DATETIME_TZ,
    DateFormat.ISO8601_UNSPECIFIED,
}

UNSPECIFIED_NAMED_FORMATS = {
    DateFormat.ISO8601_UNSPECIFIED,
    DateFormat.EURO_UNSPECIFIED,
    DateFormat.US_UNSPECIFIED,
}

ALL_NAMED_FORMATS = set(NAMED_FORMAT_TO_STRFTIME) | UNSPECIFIED_NAMED_FORMATS


def serial_format_to_strftime(v):
    """Convert a tdda.serial format string to a strftime format string.

    Named ISO8601/Euro/US formats map to their canonical strftime via
    ``NAMED_FORMAT_TO_STRFTIME``. Unspecified formats (``eu``, ``us``)
    raise ``NotImplementedError``. Raw strftime strings (containing
    ``%``) pass through unchanged. ``None`` returns ``None``.
    """
    if v is None:
        return None
    if v in UNSPECIFIED_NAMED_FORMATS and v != DateFormat.ISO8601_UNSPECIFIED:
        raise NotImplementedError(
            f'Date format "{v}" is not yet implemented. '
            f'Use a specific format such as "{v}-date" or "{v}-datetime".'
        )
    if v in NAMED_FORMAT_TO_STRFTIME:
        return NAMED_FORMAT_TO_STRFTIME[v]
    style = detect_format_style(v)
    if style in ('yyyydate', 'literaldate'):
        return to_strftime(v)
    return v  # raw strftime string: pass through


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
SERIAL_METADATA_FLAVOURS = [
    TDDASERIAL.key,
    'csvw',
    'pandas.read_csv',
    'polars.read_csv',
]

CSVW_ONLY_KEYS = (
    'n_tables',
    'table_number',
)


METADATA_FLAVOUR_MAP = {
    'tdda.serial': 'tdda.serial',
    'pandas.read_csv': 'pandas.read_csv',
    'pandas.DataFrame.to_csv': 'pandas.DataFrame.to_csv',
    'polars.read_csv': 'polars.read_csv',
    'polars.DataFrame.write_csv': 'polars.DataFrame.write_csv',
    'csvw': 'csvw',
    'frictionless.package': 'frictionless.package',
    'frictionless.resource': 'frictionless.resource',
    'frictionless': 'frictionless',
    'python.csv.reader': 'python.csv.reader',
    'python.csv.writer': 'python.csv.writer',
    '.': 'tdda.serial',
    'pd.r': 'pandas.read_csv',
    'pd.w': 'pandas.DataFrame.to_csv',
    'pl.r': 'polars.read_csv',
    'pl.w': 'polars.DataFrame.write_csv',
    'csv.r': 'python.csv.reader',
    'csv.w': 'python.csv.writer',
    'fless': 'frictionless',
    'fless.r': 'frictionless.resource',
    'fless.p': 'frictionless.package',
    'fl': 'frictionless',
    'fl.r': 'frictionless.resource',
    'fl.p': 'frictionless.package',
}

VERBOSITY = 2  # show errors and warnings. 1 for errors only. 0 for none
# 3 for extra information

FIELDTYPES = tuple(FieldType.__dict__.values())

QUOTING_CODES = {
    k: v for k, v in csv.__dict__.items() if k.startswith('QUOTE_')
}
QUOTING_CODES['QUOTE_STRINGS_ONLY'] = -1
QUOTING_NAMES = {v: k for k, v in QUOTING_CODES.items()}


class FieldMetadata:
    """Metadata for a single field (column) in a flat file.

    Args:
        name (str): Internal name for the field/column used in the
            resulting dataframe. Need not match the name in the file
            (see csvname). MANDATORY.
        fieldtype (str): Type of the field. Must be one of the values
            in FieldType: bool, int, float, number, string, date,
            datetime, datetime_tz, time, iso8601. OPTIONAL.
        csvname (str): Name of the column in the file, if different
            from name. OPTIONAL.
        format (str): Format of the field. Interpretation depends on
            fieldtype. For date/datetime: a named format (e.g.
            'iso8601-date', 'eu-datetime') or a strftime string (e.g.
            '%d/%m/%Y'). For bool: a boolean format spec (e.g.
            'yes|no'). Unambiguous because fieldtype is known.
            OPTIONAL.
        null_indicator (str or list): String(s) to interpret as
            NULL/NA in this field. Overrides the dataset-level
            null_indicator. OPTIONAL.
        true_values (str or list): String(s) to interpret as True
            for bool fields. OPTIONAL.
        false_values (str or list): String(s) to interpret as False
            for bool fields. OPTIONAL.
        description (str): Human-readable description of the field.
            OPTIONAL.
        thou_sep (str): Thousands separator character (e.g. ',').
            TBC. OPTIONAL.
        dp: TBC. OPTIONAL.
        dps (int): Number of decimal places for float fields.
            TBC. OPTIONAL.
        examples (list): Example values for the field. TBC. OPTIONAL.
        rdf_type (str): RDF type URI for the field. TBC. OPTIONAL.
        altnames (list): Alternative names for the field (e.g. from
            CSVW titles). TBC. OPTIONAL.
    """

    def __init__(
        self,
        name,
        fieldtype=None,
        csvname=None,
        format=None,
        null_indicator=None,
        true_values=None,
        false_values=None,
        allow_extra_keys=False,
        description=None,
        thou_sep=None,
        dp=None,
        dps=None,
        examples=None,
        rdf_type=None,
        altnames=None,
        **kw,
    ):
        self.name = name
        self.csvname = csvname or name
        self.fieldtype = fieldtype
        self.altnames = None
        self.format = format
        self.null_indicator = null_indicator
        self.true_values = listify(true_values)
        self.false_values = listify(false_values)
        self.description = description
        self.thou_sep = thou_sep
        self.dp = dp
        self.dps = dps
        self.examples = examples
        self.rdf_type = rdf_type

        for k, v in kw.items():
            if allow_extra_keys:
                self.__dict__[k] = v
            else:
                msg = f'Unexpected kwarg to FieldMetadata for {name}: "{k}"'
                raise KeyError(msg)

        self._errors = []
        self._warnings = []

        self._valid = None

    def get_val(self, d, k, missing=MISSING.ALLOWED):
        if not k in d:
            msg = f'Key "{k}" not found for field {self.name}'
            if missing == MISSING.ERROR:
                self._errors.append(msg)
            elif missing == MISSING.WARNING:
                self._warnings.append(msg)
            elif missing != MISSING.ALLOWED:
                raise TDDASerialError(f'Unknown value "{missing}" for missing')
        return d.get(k, None)

    def validate(self):
        if self.fieldtype is not None and self.fieldtype not in FIELDTYPES:
            self._errors.append(
                f'Unknown field type "{self.fieldtype}" for field {self.name}'
            )

    def unobjectify(self):
        d = {
            k: unobjectify(v)
            for k, v in self.__dict__.items()
            if nonnull(v) and not k.startswith('_')
        }
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
        parts = ', '.join(
            f'{k}={repr(v)}'
            for k, v in self.__dict__.items()
            if v is not None and v != []
        )
        return f'FieldMetadata({parts})'


class SerialMetadata:
    """
    Metadata describing the format and structure of a flat file (CSV or
    similar). Corresponds to the 'tdda.serial' section of a .serial file.

    All parameters are optional. Where not specified, library defaults
    (e.g. pandas.read_csv defaults) apply.

    Args:
        fields (list or dict): List of :class:`FieldMetadata` objects,
            or a dict mapping CSV column names to field attribute dicts.
            Use a list when specifying all fields (complete schema); use
            a dict when specifying only a subset (partial schema),
            allowing extra fields in the file. OPTIONAL.
        path (str): Path to the associated flat file. OPTIONAL.
        encoding (str): Character encoding of the file (e.g. 'UTF-8',
            'latin-1'). OPTIONAL.
        delimiter (str): Field separator character (e.g. ',', '|',
            '\\t'). OPTIONAL.
        quote_char (str): Quote character used to wrap fields containing
            delimiters or newlines (e.g. '"'). OPTIONAL.
        escape_char (str): Escape character used within quoted strings
            (e.g. '\\\\'). OPTIONAL.
        stutter_quotes (bool): If True, quotes within quoted strings are
            doubled rather than escaped (doublequote=True in pandas).
            OPTIONAL.
        date_format (str): Default date/datetime format for all date and
            datetime fields in the dataset. Can be a named format (e.g.
            'iso8601-date', 'eu-datetime') or a strftime string.
            Overridden by per-field format if set. OPTIONAL.
        null_indicator (str or list): String(s) to interpret as NULL/NA
            values throughout the file. OPTIONAL.
        header_row_count (int): Number of header rows at the top of the
            file. 0 means no header. Defaults to 1. OPTIONAL.
        header_row: TBC. OPTIONAL.
        quoting (str): CSV quoting style (e.g. 'QUOTE_MINIMAL',
            'QUOTE_ALL'). Accepts Python csv module quoting constants
            by name or value. OPTIONAL.
        decimal_point (str): Character used as decimal separator
            (e.g. '.' or ','). OPTIONAL.
        dps (int): Default number of decimal places for float fields.
            TBC. OPTIONAL.
        accept_percentages_as_floats (bool): If True, values like
            '12.5%' are read as 0.125. OPTIONAL.
        map_missing_trailing_cols_to_null (bool): If True, short rows
            (fewer fields than expected) are padded with nulls rather
            than causing an error. Useful for Excel-generated CSVs.
            OPTIONAL.
        true_values (str or list): Default string(s) to interpret as
            True for bool fields across the dataset. OPTIONAL.
        false_values (str or list): Default string(s) to interpret as
            False for bool fields across the dataset. OPTIONAL.
        thou_sep (str): Thousands separator character. TBC. OPTIONAL.
        dp: TBC. OPTIONAL.
        verbosity (int): Controls warning/error output. 0=silent,
            1=errors only, 2=errors and warnings (default), 3=verbose.
        libs (dict): Library-specific parameter blocks (e.g.
            'pandas.read_csv', 'polars.read_csv'). When present for a
            given library, these parameters are used directly instead
            of being derived from the tdda.serial section. OPTIONAL.
        source: TBC. OPTIONAL.
        extra_kwargs (str): Controls handling of unrecognised keyword
            arguments. 'warn' (default) issues a warning, 'error'
            raises an error, 'allow' silently accepts.
    """

    def __init__(
        self,
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
        accept_percentages_as_floats=None,
        map_missing_trailing_cols_to_null=None,
        true_values=None,
        false_values=None,
        thou_sep=None,
        dp=None,
        verbosity=VERBOSITY,
        libs=None,
        source=None,
        extra_kwargs='warn',
        **kw,
    ):
        #        if datetime_format is not None and date_format is None:
        #            date_format = datetime_format
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
        self.date_format = nvl(date_format, datetime_format)
        self.datetime_format = datetime_format
        self.null_indicator = null_indicator

        self.accept_percentages_as_floats = accept_percentages_as_floats
        self.map_missing_trailing_cols_to_null = (
            map_missing_trailing_cols_to_null
        )
        self.true_values = None
        self.false_values = None
        self.header_row_count = header_row_count
        self.header_row = header_row
        self.comment_char = None
        self.line_terminators = None
        self.skip_blank_rows = None
        self.skip_initial_space = None
        self.skip_columns = None
        self.skip_rows = None
        self.quoting = quoting_as_name(quoting)
        self.decimal_point = decimal_point
        self.trim = None
        self.thou_sep = thou_sep
        self.dp = dp
        self.dps = dps

        self.libs = libs or {}

        self._errors = []
        self._warnings = []

        self._metadata_source = None
        self._metadata_source_path = None
        self._valid = None
        self._verbosity = verbosity

        if self.header_row_count is None and self.header_row:
            self.header_row_count = 1
        if self.header_row is None and header_row_count:
            self.header_row = 0

        #        self.metametadata = {
        #            'creationhash': ''
        #        }

        if isinstance(self.fields, list):
            self.fields = [
                (FieldMetadata(**f) if isinstance(f, dict) else f)
                for f in self.fields
            ]

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
                error(f'** FATAL ERROR: {msg}', exit=False)
                valid = False
            for field in self.fields:
                field.validate()
                for msg in field._errors:
                    error(f'** FATAL ERROR: {msg}', exit=False)
                    valid = False
        v = self._verbosity > 1
        for msg in self._warnings:
            warn(f'** WARNING: {msg}', verbose=v)
        for field in self.fields:
            for msg in field._warnings:
                warn(f'** WARNING: {msg}', verbose=v)

        self._valid = valid

    def unobjectify(self, date_style=None):
        d = {
            'format': URI.TDDASERIAL,
            'writer': writer(),
        }
        m = {
            k: unobjectify(v)
            for k, v in self.__dict__.items()
            if not k.startswith('_')
            and k != 'libs'
            and nonnull(v)
            and not k in CSVW_ONLY_KEYS
        }
        nulls = m.get('null_indicator')
        quoting = m.get('quoting')
        if quoting:
            m['quoting'] = quoting_as_name(quoting)
        if type(nulls) == list and len(nulls) == 1:
            m['null_indicator'] = nulls[0]
        if date_style:
            for key in ('date_format', 'datetime_format'):
                if key in m:
                    m[key] = restyle_format(m[key], date_style)
            for field_d in m.get('fields', []):
                if 'format' in field_d:
                    old = field_d['format']
                    field_d['format'] = restyle_format(
                        field_d['format'], date_style
                    )
        if m:
            d[TDDASERIAL.key] = m

        for lib, params in self.libs.items():
            if lib != TDDASERIAL.key:
                d[lib] = {k: unobjectify(v) for (k, v) in params.items()}
        return d

    def to_json(self, indent=4, date_style=None):
        return json.dumps(
            self.unobjectify(date_style=date_style), indent=indent
        )

    def write(
        self, path, use_serial_ext=True, indent=4, verbose=0, date_style=None
    ):
        """Write metadata to a ``.serial`` file.

        Args:
            path (str): Output path. Changed to ``.serial`` extension
                unless ``use_serial_ext`` is False.
            use_serial_ext (bool): If False, keep the extension in path
                unchanged.
            indent (int): JSON indentation level (default 4).
            verbose (int): If non-zero, print the output path.
            date_style (DateStyle): Controls output date format style.
        """
        outpath = swap_ext(path, '.serial') if use_serial_ext else path
        with open(outpath, 'w') as f:
            f.write(self.to_json(indent=indent, date_style=date_style))
        if verbose:
            print(f'Written {outpath}.')

    def single_date_format(self, warner=None):
        """Get a single date/time format from serial metadata.

        Typically needed for write parameters. Uses the default format
        if set; otherwise looks at field formats and uses the modal
        value, or iso8601datetime if there is a tie.
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
        """Return a single null indicator string, for use when writing."""
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
        f'Attempt to unobjectify unexpected type.\nType: {type(o)}: Value: {repr(o)}'
    )


def nonnull(v):
    """Return True if v is non-null and non-empty (should be serialized)."""
    return v is not None and v != [] and v != () and v != {}


def writer():
    return f'{TDDASERIAL.key}-{writable_version()}'


def is_iso8601_format(fmt, inc_names=True, return_specific=False):
    if inc_names:
        if fmt.lower() in ISO8601_NAMED_FORMATS:
            return fmt.lower() if return_specific else True
    style = detect_format_style(fmt)
    if style in ('yyyydate', 'literaldate'):
        try:
            strftime = to_strftime(fmt)
        except ValueError:
            return False
    else:
        strftime = fmt
    m = re.match(RE_ISO8601, strftime)
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


def quoting_as_code(name):
    if name is None:
        return None

    return name if isinstance(name, int) else QUOTING_CODES[name]


def quoting_as_name(code):
    if code is None:
        return None

    return code if isinstance(code, str) else QUOTING_NAMES[code]


def get_metadata_flavour(flavour):
    out_flavour = METADATA_FLAVOUR_MAP.get((flavour or '.').lower())
    if flavour and out_flavour is None:
        error(f'Unknown metadata flavour: {flavour}')
    return out_flavour


def get_metadata_flavours(flavours):
    return [
        get_metadata_flavour(f) for f in (flavours or '.').strip().split(',')
    ]
