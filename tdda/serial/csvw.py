import json
import os
import re

from tdda.serial.metadata import (
    DateFormat,
    FieldMetadata,
    FieldType,
    RE_ISO8601,
    SerialMetadata,
    TDDASerialError,
    writer,
)
from tdda.serial.utils import CSVW_MD_RE

from tdda.utils import nvl, listify, warn, error


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
    """
    Subclass of SerialMetadata specifically for CSVW Metadata provided
    in CSVW format.

    Imports the information from a csvw JSON file
    (typically foo-metadata.json for file foo.csv)
    to SerialMetadata.

    Args:
        spec should normally either be a path to a CSVW file (usually .json)
             or a dictionary of the form returned by performing
             a json.load such a (valid) CSVW).
             If None, minimal initialization is performed

    Validation Properties:
            ._valid     is True if no errors were encountered
            ._errors    is a list of (textual) errors (if any)
            ._warnings  is a list of (textual) warnings generated
                        while reading the CSVW information

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
        """
        Reads the CSVW spec from the file if spec is a path to a file
        Stores spec in ._csvw.

        Args:
            spec: path to CSVW file or JSON-read contents thereof
                  (or equivalent)
        """
        if type(spec) == str:
            with open(spec) as f:
                self._csvw = json.load(f)
            self._metadata_source_path = os.path.abspath(spec)
            self._metadata_source_dir = os.path.dirname(os.path.abspath(spec))
        else:
            self._csvw = spec
            print('0000', spec)

    def field_to_csvw_json(self, field):
        d = {}
        self.set_if_non_null(d, 'name', nvl(field.csvname, field.name))
        csvw_type = FIELDTYPE_TO_CSVW.get(field.fieldtype)
        self.set_if_attr_non_null(d, 'titles', 'name')
        fmt = field.format
        if fmt is None and field.fieldtype.startswith('date'):
            if field.fieldtype == FieldType.DATETIME:
                fmt = nvl(self.datetime_format, self.date_format)
            else:
                fmt = self.date_format
            csvw_fmt = serial_date_format_to_csvw(fmt, field.fieldtype)
            if csvw_type is not None:
                d['datatype'] = {'base': csvw_type, 'format': csvw_fmt}
            else:
                self.set_if_non_null(d, 'datatype', csvw_type)
        else:
            self.set_if_non_null(d, 'datatype', csvw_type)
            if field.true_values and field.false_values:
                d['format'] = booleans_to_csvw(
                    field.true_values, field.false_values
                )
            elif (
                field.fieldtype == FieldType.BOOL
                and self.true_values
                and self.false_values
            ):
                d['format'] = booleans_to_csvw(
                    self.true_values, self.false_values
                )
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
            csvfile = self.choose_csv_from_csvw_name(path)
        out = self.to_csvw_json(csvfile=csvfile, lang=lang, indent=indent)
        with open(path, 'w') as f:
            f.write(out)

    def set_if_attr_non_null(self, d, key, attribute=None):
        """
        Set item key in dictionary d to the value of
        the given attribute of self, which defaults to key.

        Args:
            d          dictionary
            key        key to set
            attribute  attribute in self to look up (defaults to key)

        Returns:
            None
        """
        value = getattr(self, nvl(attribute, key), None)
        if value is not None:
            d[key] = value

    def set_if_non_null(self, d, key, value):
        """
        Set item key in dictionary d to value, if it is not null.

        Args:
            d          dictionary
            key        key to set
            value      the value to which to set the key in d

        Returns:
            None
        """
        if value is not None:
            d[key] = value

    def get_schema_and_columns(self):
        """
        Sets _schema and _columns from CSVW
        """
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
        """
        CSVW files have a mandatory @context property that should have
        the value http://www.w3.org/ns/csvw (CSVW.CONTEXT).

        That can be stored as a string or as the first item in a list.
        The value is a list, the second element should be a dictionary
        containing one or both of the keys:

            @base — a base URL for interpreting other URLS
            @language - a natural language code such as en

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
        """
        Reads the dialect parameter from the first tableSchema
        of the first table in the csvw spec.

        If there no dialect section, reads it from 'dc:replaces'
        instead, if there is one.
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
        """
        Processes the dialect part of a CSVW specification.

        https://w3c.github.io/csvw/metadata/#dfn-dialect-descriptions
        specifies the defaults for these as:

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
                    f'Illegal value "{self.trim}" for delect attribute '
                    '"trim". Ignoring'
                )
                self.trim = None
        if self.trim == 'true':
            self.trim = True
        elif self.trim == 'false':
            self.trim = False

    def get_non_dialect_attrs(self):
        nulls = self._csvw.get('null')
        if nulls:
            self.null_indicator = nulls

    def get_fields_metadata(self):
        fields = self.fields  # empty dict
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
                field.format = DateFormat.ISO8601_UNSPECIFIED

            titles = field.get_val(f, 'titles')
            if titles:
                if isinstance(titles, list):
                    field.altnames = titles
                elif isinstance(titles, dict):
                    field.altnames = titles
                elif type(titles) is str:
                    field.altnames = [titles]
                else:
                    self.warn(
                        f'Did not understand value "{titles}"'
                        f'of type "{type(titles)}" '
                        f'for titles of column {name}; ignoring.'
                    )
            description = field.get_val(f, 'dc:description')
            if description:
                field.description = description

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
    """
    Converts CSVW date formats to nearest equivalent Python
    data format.
    """
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
    if extensions:
        outfmt = outfmt.replace('+ZZ:zz', '%:z').replace('+ZZzz', '%z')
    # TODO: why? Just leave?
    return (
        DateFormat.ISO8601_UNSPECIFIED
        if (re.match(RE_ISO8601, outfmt) or fmt == '')
        else outfmt
    )


def serial_date_format_to_csvw(fmt, extensions=False, fieldtype=None):
    if fmt == DateFormat.ISO8601_UNSPECIFIED:
        return (
            'yyyy-mm-dd'
            if fieldtype == 'date'
            else 'yyyy-mm-ddTHH:MM:SS+ZZ:zz'
            if fieldtype == 'datetime_tz'
            else 'yyyy-mm-ddTHH:MM:SS'
        )

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
        outfmt = outfmt.replace('%:z', '+ZZ:zz')
    return outfmt


def serial_to_csvw(md, name='data.csv'):
    """
    Converts a SerialMetadata object to a CSVWMetadata Object.

    Args:
        md: A SerialMetatadata object.

    Returns:
            A (braoadly equivalent) CSVWMetadata obkect
    """
    csvw = CSVWMetadata(url=name)
    csvw.__dict__.update(md.__dict__)
    return csvw
