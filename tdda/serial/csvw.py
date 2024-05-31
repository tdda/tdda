import json
import os
import re

from tdda.serial.base import (
    Metadata,
    FieldMetadata,
    MISSING,
    RE_ISO8601
)
from tdda.utils import nvl


# From https://w3c.github.io/csvw/primer/#datatypes
# Diag: From https://w3c.github.io/csvw/primer/datatypes.svg

CSVW_TYPE_TO_MTYPE = {
    'boolean': 'bool',
    'integer': 'int',
    'string': 'string',
    'number': 'number',
    'datetime': 'datetime',
    'date': 'date',

    'double': 'number',
    'decimal': 'number',
    'float': 'number',

    'long': 'int',
    'int': 'int',
    'short': 'int',
    'byte': 'int',

    'unsignedLong': 'int',
    'unsignedInt': 'int',
    'unsignedShort': 'int',
    'unsignedByte': 'int',

    'nonNegativeInteger': 'int',
    'nonPositiveInteger': 'int',
    'negativeInteger': 'int',
    'positiveInteger': 'int',

    'normalizedString': 'string',
    'anyURI': 'string',
    'token': 'string',
    'language': 'string',
    'Name': 'string',
    'NMTOKEN': 'string',

    'xml': 'string',
    'html': 'string',
    'json': 'string',

    'dateTime': 'datetime',

    # Read as strings for now

    'base64Binary': 'string',
    'binary': 'string',
    'hexBinary': 'string',

    'anyAtomicType': 'string',
    'dateTimeStamp': 'string',  # with timezone

    'duration': 'string',
    'dayTimeDuration': 'string',
    'yearMonthDuration': 'string',
    'time': 'string',

    'QName': 'string',

    'gDay': 'string',
    'gMonth': 'string',
    'gMonthDay': 'string',
    'gYear': 'string',
    'gYearMonth': 'string',
}


class CSVWConstants:
    CONTEXT = 'http://www.w3.org/ns/csvw'


class CSVWMetadata(Metadata):
    """
    Subclass of CSVW specifically for CSV Metadata provided in CSVW format.

    Imports the information from a csvw JSON file
    (typically foo-metadata.json for file foo.csv)
    to the CSVMetadata.

    Args:
        spec should either be a path to a CSVW file (usually .json)
             or a dictionary of the form returned by performing
             a json.load such a (valid) CSVW).

    Validation Properties:
            .valid     is True if no errors were encountered
            .errors    is a list of (textual) errors (if any)
            .warnings  is a list of (textual) warnings generated
                       while reading the CSVW information

    """
    def __init__(self, spec, extensions=False, table_number=None,
                 for_table_name=None, verbosity=2):
        super().__init__(verbosity=verbosity)
        self._url = None
        self._csvw_base_url = None
        self._csvw_language = None
        self._extensions = extensions
        self._fullpath = None
        self.metadata_source_dir = None
        self.table_number = table_number
        self.for_table_name = for_table_name

        self.read(spec)
        self.get_schema_and_columns()

        # First process the file-level metadata
        self.get_context()
        self.get_url()

        self.get_dialect()

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
            self.metadata_source_path = os.path.abspath(spec)
            self.metadata_source_dir = os.path.dirname(os.path.abspath(spec))
        else:
            self._csvw = spec

    def get_schema_and_columns(self):
        """
        Sets _schema and _columns from CSVW
        """
        try:
            tables = self._csvw.get('tables')
            if tables:
                N = self.n_tables = len(tables)
                if (N > 1
                        and self.table_number is None
                        and not self.for_table_name):
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
                    loc = self.metadata_source_path
                    sloc = f' in {loc}' if loc else ''
                    raise Exception(f'No table {n} found{sloc}.')
                self._table = table
                self._schema = self._table.get('tableSchema')
            else:
                self._table = None
                self._schema = self._csvw.get('tableSchema')
                n = 0
        except KeyError:
            raise Exception('Could not find schema information in CSVW file\n'
                            "at ['tables'][{n}]['tableSchema'].")

        if type(self._schema) is str:
            path = os.path.join(nvl(self.metadata_source_dir, ''),
                                 self._schema)
            with open(path) as f:
                self._schema = json.load(f)

        if self._schema:
            try:
                self._columns = self._schema['columns']
            except:
                raise KeyError('Could not find columns information in CSVW'
                               ' file at '
                               "['tables'][0]['tableSchema']['columns'].")
        else:
            self._columns = []

    def get_context(self):
        """
        CSVW files have a mandatory @context property that should have
        the value http://www.w3.org/ns/csvw (CSVWConstants.CONTEXT).

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
                self.warn('@context can only have 1 or 2 values when a list. '
                          f'{len(value)} found')
        else:
            context = value

        if context == CSVWConstants.CONTEXT:
            self.metadata_source = context
        else:
            self.warn('Unexpected value "{context}" for purported CSVW source.')
        if properties:
            self._csvw_base_url = properties.get('@base')
            self._csvw_language = properties.get('@language')


    def get_url(self):
        self._url = self._csvw.get('url') or (
            self._table.get('url') if self._table else None
        )
        if not self._url:
            self.warn('Mandatory property "url" not found in CSVW file.')
        if (getattr(self, 'metadata_source_dir', None)
               and self._url
               and not '://' in self._url):
            self._fullpath = os.path.join(self.metadata_source_dir, self._url)

    def get_dialect(self):
        """
        Reads the dialect parameter from the first tableSchema
        of the first table in the csvw spec.

        If there no dialect section, reads it from 'dc:replaces'
        instead, if there is one.
        """
        self._dialect = dialect = self._csvw.get('dialect', {})
        dcreplaces = self._csvw.get('dc:replaces')

        # Pull stiff out of dcreplaces if necessary
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

        self._double_quote = self.get_val(dialect, 'doubleQuote')
        self.header_row_count = self.get_val(dialect, 'headerRowCount')
        header = self.get_val(dialect, 'header')
        if header and not self.header_row_count:
            self.header_row_count = 1
        self.comment_prefix = self.get_val(dialect, 'commentPrefix')
        self.line_terminators = self.get_val(dialect, 'lineTerminators')
        self.quote_char = self.get_val(dialect, 'quoteChar')
        self.skip_blank_rows = self.get_val(dialect, 'skipRows')
        self.skip_rows = self.get_val(dialect, 'skipRows')
        self.skip_initial_space = self.get_val(dialect, 'skipInitialSpace')
        self.skip_columns = self.get_val(dialect, 'skipCols')
        header_rows = self.get_val(dialect, 'headerRowCount')
        header = self.get_val(dialect, 'headerRowCount')
        self.header_rows = 0 if header == False else nvl(header_rows, 1)

        # Allowed to be a boolean or string value. If string:
        # string value: true false, start, end
        # This standarizes to booeans if "true" or "false"
        self.trim = self.get_val(dialect, 'trim')
        if self.trim is not None:
            if self.trim not in (True, False, "true", "false", "start", "end"):
                self.warn(f'Illegal value "{self.trim}" for delect attribute '
                          '"trim". Ignoring')
                self.trim = None
        if self.trim == "true":
            self.trim = True
        elif self.trim == "false":
            self.trim = False


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
            datatype = field.get_val(f, 'datatype')  #, missing=MISSING.ERROR)

            fmt = None
            if datatype:
                if isinstance(datatype, dict):
                    fmt = datatype.get('format')
                    mtype = CSVW_TYPE_TO_MTYPE.get(datatype.get('base'))
                else:
                    mtype = CSVW_TYPE_TO_MTYPE.get(datatype)
                field.mtype = mtype
            else:
                mtype = None
            if not fmt:
                fmt = field.get_val(f, 'format')
            if fmt:
                if mtype.startswith('date'):
                    fmt = csvw_date_format_to_md_date_format(
                        fmt,
                        extensions=self._extensions
                    )
                field.format = fmt
            elif mtype and mtype.startswith('date'):
                field.format = 'ISO8601'  # too pandas specific


            titles = field.get_val(f, 'titles')
            if titles:
                if isinstance(titles, list):
                    field.altnames = titles
                elif isinstance(titles, dict):
                    field.altnames = titles
                elif type(titles) is str:
                    field.altnames = [titles]
                else:
                    self.warn(f'Did not understand value "{titles}"'
                              f'of type "{type(titles)}" '
                              f'for titles of column {name}; ignoring.')
            description = field.get_val(f, 'dc:description')
            if description:
                field.description = description


class CSVWMultiMetadata:
    def __init__(self, spec, extensions=False):
        table = CSVWMetadata(spec, extensions)
        self.tables = [table]
        n_tables = table.n_tables
        if n_tables > 1:
            self.tables.extend([
                CSVWMetadata(spec, extensions, table_number=i)
                for i in range(1, n_tables + 1)
            ])



def csvw_date_format_to_md_date_format(fmt, extensions=False):
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
    return 'ISO8601' if (re.match(RE_ISO8601, outfmt) or fmt == '') else outfmt


