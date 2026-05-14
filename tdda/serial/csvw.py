import json
import os
import re

from tdda.serial.dateutils import strftime_to_yyyydate
from tdda.serial.metadata import (
    DateFormat,
    FieldMetadata,
    FieldType,
    NAMED_FORMAT_TO_STRFTIME,
    RE_ISO8601,
    SerialMetadata,
    TDDASerialError,
    serial_format_to_strftime,
    writer,
)
from tdda.serial.utils import CSVW_MD_RE

from tdda.utils import nvl, listify, oxford_list, plural, warn, error


# ISO8601 named formats: CSVW date/datetime type defaults to ISO8601,
# so no format object needed for these.
_ISO8601_NAMED = frozenset(
    {
        DateFormat.ISO8601_DATE,
        DateFormat.ISO8601_DATETIME,
        DateFormat.ISO8601_DATETIME_TZ,
        DateFormat.ISO8601_UNSPECIFIED,
    }
)

# From https://w3c.github.io/csvw/primer/#datatypes
# Diag: From https://w3c.github.io/csvw/primer/datatypes.svg

CSVW_TYPE_TO_FIELDTYPE = {
    'boolean': FieldType.BOOL,
    'integer': FieldType.INT,
    'string': FieldType.STRING,
    'number': FieldType.NUMBER,
    'datetime': FieldType.DATETIME,
    'date': FieldType.DATE,
    'double': FieldType.NUMBER,
    'decimal': FieldType.NUMBER,
    'float': FieldType.NUMBER,
    'long': FieldType.INT,
    'int': FieldType.INT,
    'short': FieldType.INT,
    'byte': FieldType.INT,
    'unsignedLong': FieldType.INT,
    'unsignedInt': FieldType.INT,
    'unsignedShort': FieldType.INT,
    'unsignedByte': FieldType.INT,
    'nonNegativeInteger': FieldType.INT,
    'nonPositiveInteger': FieldType.INT,
    'negativeInteger': FieldType.INT,
    'positiveInteger': FieldType.INT,
    'normalizedString': FieldType.STRING,
    'anyURI': FieldType.STRING,
    'token': FieldType.STRING,
    'language': FieldType.STRING,
    'Name': FieldType.STRING,
    'NMTOKEN': FieldType.STRING,
    'xml': FieldType.STRING,
    'html': FieldType.STRING,
    'json': FieldType.STRING,
    'dateTime': 'datetime',
    # Read as strings for now
    'base64Binary': FieldType.STRING,
    'binary': FieldType.STRING,
    'hexBinary': FieldType.STRING,
    'anyAtomicType': FieldType.STRING,
    'dateTimeStamp': FieldType.STRING,  # with timezone
    'duration': FieldType.STRING,
    'dayTimeDuration': FieldType.STRING,
    'yearMonthDuration': FieldType.STRING,
    'time': FieldType.STRING,
    'QName': FieldType.STRING,
    'gDay': FieldType.STRING,
    'gMonth': FieldType.STRING,
    'gMonthDay': FieldType.STRING,
    'gYear': FieldType.STRING,
    'gYearMonth': FieldType.STRING,
}


FIELDTYPE_TO_CSVW = {
    FieldType.BOOL: 'boolean',
    FieldType.INT: 'integer',
    FieldType.FLOAT: 'float',
    FieldType.NUMBER: 'number',
    FieldType.STRING: 'string',
    FieldType.DATE: 'date',
    FieldType.DATETIME: 'datetime',
    FieldType.DATETIME_WITH_TIMEZONE: 'datetime',
}


class CSVW:
    CONTEXT = 'http://www.w3.org/ns/csvw'


class CSVWMetadata(SerialMetadata):
    """SerialMetadata subclass that reads CSVW metadata.

    Imports metadata from a CSVW JSON file (typically
    foo-metadata.json for file foo.csv) into the SerialMetadata
    representation.

    Args:
        spec (str or dict): Path to a CSVW file (usually .json), or a
            dict of the form returned by json.load on a valid CSVW
            file. If None, minimal initialization is performed.
        extensions (bool): If True, accept tdda CSVW extensions.
        table_number (int): If set, use the nth table (indexed from
            zero) from a multi-table CSVW file.
        for_table_name (str): If set, select the table whose url ends
            with this name from a multi-table CSVW file.
        url (str): Override the url for the data file.
        verbosity (int): Controls warning/error output.

    Validation attributes (read-only):
        _valid (bool): True if no errors were encountered.
        _errors (list): Textual errors found while reading.
        _warnings (list): Textual warnings generated while reading.
    """

    def __init__(
        self,
        spec=None,
        extensions=False,
        table_number=None,
        for_table_name=None,
        url=None,
        verbosity=2,
    ):
        super().__init__(verbosity=verbosity)
        self._url = url
        self._csvw_base_url = None
        self._csvw_language = None
        self._extensions = extensions
        self._fullpath = None
        self._source = 'csvw'
        self._metadata_source_dir = None
        self.table_number = table_number
        self.for_table_name = for_table_name

        if spec is None:  # Only normally used by to_csvw and tests
            return

        self.read(spec)
        self.get_schema_and_columns()

        # First process the file-level metadata
        self.get_context()
        self.get_url()

        self.get_dialect()
        self.get_non_dialect_attrs()

        # Extract field metadata
        self.get_fields_metadata()

        self.validate()

    def read(self, spec):
        """Read the CSVW spec from file or dict and store in ``._csvw``.

        Args:
            spec (str or dict): Path to a CSVW file, or a dict
                of the form returned by json.load on a valid CSVW file.
        """
        if type(spec) == str:
            with open(spec) as f:
                self._csvw = json.load(f)
            self._metadata_source_path = os.path.abspath(spec)
            self._metadata_source_dir = os.path.dirname(os.path.abspath(spec))
        else:
            self._csvw = spec

    def field_to_csvw_json(self, field):
        d = {}
        self.set_if_non_null(d, 'name', field.name)
        csvw_type = FIELDTYPE_TO_CSVW.get(field.fieldtype)
        if field.csvname and field.csvname != field.name:
            d['titles'] = field.csvname
        fmt = field.format
        if field.fieldtype and field.fieldtype.startswith('date'):
            if fmt is None:
                if field.fieldtype == FieldType.DATETIME:
                    fmt = nvl(self.datetime_format, self.date_format)
                else:
                    fmt = self.date_format
            if fmt:
                csvw_fmt = serial_date_format_to_csvw(
                    fmt, fieldtype=field.fieldtype
                )
                if csvw_type is not None and csvw_fmt is not None:
                    d['datatype'] = {'base': csvw_type, 'format': csvw_fmt}
                else:
                    self.set_if_non_null(d, 'datatype', csvw_type)
            else:
                self.set_if_non_null(d, 'datatype', csvw_type)
        else:
            true_vals = field.true_values or (
                self.true_values if field.fieldtype == FieldType.BOOL else None
            )
            false_vals = field.false_values or (
                self.false_values
                if field.fieldtype == FieldType.BOOL
                else None
            )
            if true_vals and false_vals:
                csvw_fmt = booleans_to_csvw(true_vals, false_vals)
                if csvw_type is not None:
                    d['datatype'] = {'base': csvw_type, 'format': csvw_fmt}
                else:
                    self.set_if_non_null(d, 'datatype', csvw_type)
            else:
                self.set_if_non_null(d, 'datatype', csvw_type)
        self.set_if_attr_non_null(d, 'dc:description', 'description')
        return d

    def to_csvw_json(
        self, csvfile=None, lang=None, indent=4, resource_type=None
    ):
        csvfile = nvl(csvfile, nvl(self._url, 'data.csv'))
        dialect = {}

        tableSchema = {}
        for key, attr in (
            ('dc:description', 'description'),
            ('dc:title', 'title'),
        ):
            self.set_if_attr_non_null(tableSchema, key, attr)
        columns = [self.field_to_csvw_json(field) for field in self.fields]
        if columns:
            tableSchema['columns'] = columns

        self._null = self.single_null_indicator()
        self._trim = (  # can be 'true', 'false', 'start' or 'end' in csvw
            'true'
            if self.trim == True
            else 'false'
            if self.trim == False
            else self.trim
        )
        for key, attr in (
            ('encoding', None),
            ('delimiter', None),
            ('header', None),
            ('headerRowCount', 'header_row_count'),
            # ('null', '_null'),
            ('doubleQuote', 'stutter_quotes'),
            ('quoteChar', 'quote_char'),
            ('commentPrefix', 'comment_char'),
            ('lineTerminators', 'line_terminator'),
            ('skipRows', 'skip_row_count'),
            ('skipColumns', 'skip_columns_count'),
            ('lineTerminators', 'line_terminator'),
            ('trim', '_trim'),
            # 'date_format'
            # 'true_value'
            # 'false_value'
        ):
            self.set_if_attr_non_null(dialect, key, attr)

        context = [CSVW.CONTEXT, {'@language': lang}] if lang else CSVW.CONTEXT
        d = {
            '@context': context,
            'dc:conformsTo': 'data-package',
            'dc:creator': getattr(self, 'creator', writer()),
            'tables': [
                {
                    'tableSchema': tableSchema,
                    'url': csvfile,
                },
            ],
            'dialect': dialect,
        }
        self.set_if_attr_non_null(d, 'null', '_null')
        return json.dumps(d, indent=indent)

    to_json = to_csvw_json  # Surely?

    def write_csvw(self, path, csvfile=None, lang=None, indent=4):
        if not csvfile:
            csvfile = self.path or self.choose_csv_from_csvw_name(path)
        out = self.to_csvw_json(csvfile=csvfile, lang=lang, indent=indent)
        with open(path, 'w') as f:
            f.write(out)

    def set_if_attr_non_null(self, d, key, attribute=None):
        """Set ``d[key]`` to ``self.<attribute>`` if non-null.

        Args:
            d (dict): Dictionary to update.
            key (str): Key to set.
            attribute (str): Attribute of self to look up; defaults to key.
        """
        value = getattr(self, nvl(attribute, key), None)
        if value is not None:
            d[key] = value

    def set_if_non_null(self, d, key, value):
        """Set ``d[key] = value`` if value is not None.

        Args:
            d (dict): Dictionary to update.
            key (str): Key to set.
            value: Value to assign.
        """
        if value is not None:
            d[key] = value

    def get_schema_and_columns(self):
        """Set ``_schema`` and ``_columns`` from the CSVW spec."""
        try:
            tables = self._csvw.get('tables')
            if tables:
                N = self.n_tables = len(tables)
                if (
                    N > 1
                    and self.table_number is None
                    and not self.for_table_name
                ):
                    self.warn(f'Only processing first table of {N}.')
                name = self.for_table_name
                if name:
                    L = len(name)
                    for i, t in enumerate(tables):
                        if t.get('url', '')[-L:] == name:
                            n = self.table_number = i
                            break
                    else:
                        raise KeyError(f'No table for {name} found.')
                else:
                    n = self.table_number = nvl(self.table_number, 0)
                if len(tables) > n:
                    table = tables[n]
                else:
                    self.n_tables = 0
                    loc = self._metadata_source_path
                    sloc = f' in {loc}' if loc else ''
                    error(f'No table {n} found{sloc}.')
                self._table = table
                self._schema = self._table.get('tableSchema')
            else:
                self._table = None
                self._schema = self._csvw.get('tableSchema')
                n = 0
        except KeyError:
            error(
                'Could not find schema information in CSVW file\n'
                "at ['tables'][{n}]['tableSchema']."
            )

        if type(self._schema) is str:
            path = os.path.join(
                nvl(self._metadata_source_dir, ''), self._schema
            )
            with open(path) as f:
                self._schema = json.load(f)

        if self._schema:
            try:
                self._columns = self._schema['columns']
            except:
                raise KeyError(
                    'Could not find columns information in CSVW'
                    ' file at '
                    "['tables'][0]['tableSchema']['columns']."
                )
        else:
            self._columns = []

    def get_context(self):
        """Read and validate the mandatory ``@context`` property.

        CSVW files must have ``@context`` set to
        http://www.w3.org/ns/csvw (``CSVW.CONTEXT``). It may be stored
        as a plain string or as the first item in a list; when a list,
        the second element may be a dict with keys ``@base`` (a base URL
        for resolving other URLs) and/or ``@language`` (a language code
        such as ``en``).
        """
        value = self._csvw.get('@context')
        properties = None
        if value is None:
            self.warn('No @context found in (purported) CSVW source.')
            return
        elif type(value) == list:
            if len(value) in (1, 2):
                context = value[0]
                if len(value) == 2:
                    properties = value[1]
            else:
                self.warn(
                    '@context can only have 1 or 2 values when a list. '
                    f'{len(value)} found'
                )
        else:
            context = value

        if context == CSVW.CONTEXT:
            self._metadata_source = context
        else:
            self.warn(
                'Unexpected value "{context}" for purported CSVW source.'
            )
        if properties:
            self._csvw_base_url = properties.get('@base')
            self._csvw_language = properties.get('@language')

    def get_url(self):
        self._url = self._csvw.get('url') or (
            self._table.get('url') if self._table else None
        )
        if not self._url:
            self.warn('Mandatory property "url" not found in CSVW file.')
        if (
            getattr(self, '_metadata_source_dir', None)
            and self._url
            and not '://' in self._url
        ):
            self._fullpath = os.path.join(self._metadata_source_dir, self._url)

    def get_dialect(self):
        """Read the dialect from the CSVW spec into ``_dialect``.

        Reads from the first table's dialect section. Falls back to the
        ``dc:replaces`` block if no dialect section is present.
        """
        self._dialect = dialect = self._csvw.get('dialect', {})
        if not dialect and hasattr(self, '_table') and self._table is not None:
            self._dialect = dialect = self._table.get('dialect', {})
        dcreplaces = self._csvw.get('dc:replaces')

        # Pull stuff out of dcreplaces if necessary
        if dcreplaces:
            replaces = json.loads(dcreplaces)
            resources = replaces.get('resources')
            if resources and len(resources) > 0:
                resource = resources[0]
                if resource:
                    encoding = resource.get('encoding')
                    if dialect.get('encoding') is None:
                        dialect['encoding'] = encoding
                    dcdialect = resource.get('dialect')
                    if dcdialect and not dialect.get('delimiter'):
                        csv = dcdialect.get('csv')
                        if csv:
                            delimiter = csv.get('delimiter')
                            if dialect.get('delimiter') is None:
                                dialect['delimiter'] = delimiter

        self.process_dialect()

    def process_dialect(self):
        r"""
        Processes the dialect part of a CSVW specification.

        https://w3c.github.io/csvw/metadata/#dfn-dialect-descriptions
        specifies the defaults for these as:

        .. code-block:: json

            {
                "encoding": "utf-8",
                "lineTerminators": ["\r\n", "\n"],
                "quoteChar": "\"",
                "doubleQuote": true,
                "skipRows": 0,
                "commentPrefix": "#",
                "header": true,
                "headerRowCount": 1,
                "delimiter": ",",
                "skipColumns": 0,
                "skipBlankRows": false,
                "skipInitialSpace": false,
                "trim": false
            }

        which presumably means that a conformant CSV reader will
        use those settings if they are not specified in the CSVW file.
        """
        dialect = self._dialect
        self.delimiter = self.get_val(dialect, 'delimiter')
        self.encoding = self.get_val(dialect, 'encoding')
        self.null_indicator = self.get_val(dialect, 'null')
        self.stutter_quotes = self.get_val(dialect, 'doubleQuote')
        self.header_row_count = self.get_val(dialect, 'headerRowCount')
        header = self.get_val(dialect, 'header')
        if header and not self.header_row_count:
            self.header_row_count = 1
        self.comment_char = self.get_val(dialect, 'commentPrefix')
        self.line_terminators = self.get_val(dialect, 'lineTerminators')
        self.quote_char = self.get_val(dialect, 'quoteChar')
        self.skip_blank_rows = self.get_val(dialect, 'skipRows')
        self.skip_rows = self.get_val(dialect, 'skipRows')
        self.skip_initial_space = self.get_val(dialect, 'skipInitialSpace')
        self.skip_columns = self.get_val(dialect, 'skipCols')
        header_row_count = self.get_val(dialect, 'headerRowCount')
        header = self.get_val(dialect, 'header')
        self.header_row_count = (
            0 if header == False else nvl(header_row_count, 1)
        )

        # Allowed to be a boolean or string value. If string:
        # string value: true false, start, end
        # This standarizes to booeans if "true" or "false"
        self.trim = self.get_val(dialect, 'trim')
        if self.trim is not None:
            if self.trim not in (True, False, 'true', 'false', 'start', 'end'):
                self.warn(
                    f'Illegal value "{self.trim}" for delect attribute "trim". Ignoring'
                )
                self.trim = None
        if self.trim == 'true':
            self.trim = True
        elif self.trim == 'false':
            self.trim = False

    def get_non_dialect_attrs(self):
        table = self._table or {}
        nulls = self._csvw.get('null') or table.get('null')
        if nulls:
            self.null_indicator = nulls

    def get_fields_metadata(self):
        fields = self.fields  # empty dict
        multi_title_fields = []
        for i, f in enumerate(self._columns, 1):
            name = f.get('name')
            virtual = f.get('virtual')
            if virtual:
                self.warn(f'Skipping virtual column for field {name}.')
                continue
            if not name:
                self.error(f'No name for field {i}; skipping.')
                continue
            if name in fields:
                self.error(f'Duplicate field name ({name}) in CSVW file.')
                continue

            field = FieldMetadata(name)
            fields.append(field)
            datatype = field.get_val(f, 'datatype')  # , missing=MISSING.ERROR)

            fmt = None
            if datatype:
                if isinstance(datatype, dict):
                    fmt = datatype.get('format')
                    fieldtype = CSVW_TYPE_TO_FIELDTYPE.get(
                        datatype.get('base')
                    )
                else:
                    fieldtype = CSVW_TYPE_TO_FIELDTYPE.get(datatype)
                field.fieldtype = fieldtype
            else:
                fieldtype = None
            if not fmt:
                fmt = field.get_val(f, 'format')
            if fmt:
                if fieldtype and fieldtype.startswith('date'):
                    self._csvw_date_format = fmt
                    fmt = csvw_date_format_to_serial(
                        fmt, extensions=self._extensions
                    )
                field.format = fmt
            elif fieldtype and fieldtype.startswith('date'):
                pass

            titles = field.get_val(f, 'titles')
            if titles:
                if isinstance(titles, list):
                    if len(titles) > 1:
                        multi_title_fields.append(name)
                    field.csvname = titles[0]
                elif type(titles) is str:
                    field.csvname = titles
                else:
                    self.warn(
                        f'Did not understand value "{titles}"'
                        f'of type "{type(titles)}" '
                        f'for titles of column {name}; ignoring.'
                    )
            description = field.get_val(f, 'dc:description')
            if description:
                field.description = description

        if multi_title_fields:
            n = len(multi_title_fields)
            self.warn(
                f'{plural(n, "Field", inc_n=False)} '
                f'{oxford_list(multi_title_fields)} '
                f'{plural(n, "has", full_plural="have")} '
                f'multiple titles: only using first.'
            )

    def choose_csv_from_csvw_name(self, csvw_name):
        sep = self.delimiter or ','
        ext = {',': 'csv', '\t': 'tsv', '|': 'psv', ';': 'ssv'}.get(sep, 'txt')
        base_name = os.path.basename(csvw_name)
        m = re.match(CSVW_MD_RE, base_name)
        stem = m.group(1) if m else os.path.splitext(base_name)[0]
        return f'{stem}.{ext}'


def booleans_to_csvw(true_values, false_values):
    trues, falses = listify(true_values), listify(false_values)
    if len(trues) > 1:
        warn(f'Several true values: using {trues[0]}')
    if len(falses) > 1:
        warn(f'Several false values: using {falses[0]}')
    return f'{trues[0]}|{falses[0]}'


class CSVWMultiMetadata:
    def __init__(self, spec, extensions=False):
        table = CSVWMetadata(spec, extensions)
        self.tables = [table]
        n_tables = table.n_tables
        if n_tables > 1:
            self.tables.extend(
                [
                    CSVWMetadata(spec, extensions, table_number=i)
                    for i in range(1, n_tables + 1)
                ]
            )


def csvw_date_format_to_serial(fmt, extensions=False):
    """Convert a CSVW date format string to the nearest yyyydate equivalent."""
    if not fmt:
        return None
    if '%' in fmt:
        return fmt
    outfmt = (
        fmt.replace('dd', 'd')
        .replace('d', '%d')
        .replace('MM', 'M')
        .replace('M', '%m')
        .replace('yyyy', '%Y')
        .replace('yy', '%y')
        .replace('HH', '%H')
        .replace('mm', '%M')
        .replace('SSS', 'S')
        .replace('SS', 'S')
        .replace('S', '%f')
        .replace('ss', '%S')
    )
    outfmt = outfmt.replace('xxx', '%:z').replace('xx', '%z')
    if extensions:
        outfmt = outfmt.replace('+ZZ:zz', '%:z').replace('+ZZzz', '%z')
    if re.match(RE_ISO8601, outfmt):
        return DateFormat.ISO8601_UNSPECIFIED
    yyyy = strftime_to_yyyydate(outfmt)
    return yyyy if '%' not in yyyy else outfmt


def serial_date_format_to_csvw(fmt, extensions=False, fieldtype=None):
    if fmt == DateFormat.ISO8601_UNSPECIFIED:
        return (
            'yyyy-MM-dd'
            if fieldtype == FieldType.DATE
            else 'yyyy-MM-ddTHH:mm:ssxxx'
            if fieldtype == FieldType.DATETIME_WITH_TIMEZONE
            else 'yyyy-MM-ddTHH:mm:ss'
        )

    fmt = serial_format_to_strftime(fmt) or fmt

    if '%b' in fmt or '%B' in fmt:
        warn(
            f'Date format {fmt!r} uses alpha month names which CSVW'
            ' cannot represent. Omitting date format.'
        )
        return None
    if '%p' in fmt:
        warn(
            f'Date format {fmt!r} uses AM/PM which CSVW cannot'
            ' represent. Omitting date format.'
        )
        return None

    outfmt = (
        fmt.replace('%S', 'ss')
        .replace('%f', 'SS')
        .replace('%M', 'mm')
        .replace('%H', 'HH')
        .replace('%y', 'yy')
        .replace('%Y', 'yyyy')
        .replace('%m', 'MM')
        .replace('%d', 'dd')
    )
    if extensions:
        outfmt = outfmt.replace('%:z', 'xxx').replace('%z', 'xx')
    return outfmt


def serial_to_csvw(md, name='data.csv'):
    """Convert a SerialMetadata object to a CSVWMetadata object.

    Args:
        md (SerialMetadata): Metadata to convert.
        name (str): Data file name to record in the CSVW url field
            (default 'data.csv').

    Returns:
        A broadly equivalent CSVWMetadata object.
    """
    csvw = CSVWMetadata(url=name)
    csvw.__dict__.update(md.__dict__)
    return csvw
