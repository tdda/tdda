import json
import os
import re

from yaml import load as yamlload, dump as yamldump

try:
    from yaml import CLoader as YAMLLoader, CDumper as YAMLDumper
except ImportError:
    from yaml import YAMLLoader, YAMLDumper

from tdda.serial.metadata import (
    DateFormat,
    FieldMetadata,
    FieldType,
    RE_ISO8601,
    SerialMetadata,
    writer,
)
from tdda.serial.utils import FRICTIONLESS_MD_RE
from tdda.utils import nvl, listify, warn, error

FRICTIONLESS_TELL_KEYS = ('package', 'resource', 'schema')

FRICTIONLESS_TYPE_TO_FIELDTYPE = {
    'boolean': FieldType.BOOL,
    'integer': FieldType.INT,
    'string': FieldType.STRING,
    'number': FieldType.NUMBER,
    'datetime': FieldType.DATETIME,
    'date': FieldType.DATE,
    'time': FieldType.TIME,
    'object': FieldType.STRING,  # JSON
    'year': FieldType.INT,
    'yearmonth': FieldType.STRING,  # YYYY-MM
    'duration': FieldType.STRING,
    'geopoint': FieldType.STRING,
    'geojson': FieldType.STRING,
    'any': FieldType.STRING,
    'array': FieldType.STRING,  # JSON array
}


FIELDTYPE_TO_FRICTIONLESS = {
    FieldType.BOOL: 'boolean',
    FieldType.INT: 'integer',
    FieldType.FLOAT: 'number',
    FieldType.NUMBER: 'number',
    FieldType.STRING: 'string',
    FieldType.DATE: 'date',
    FieldType.DATETIME: 'datetime',
    FieldType.DATETIME_WITH_TIMEZONE: 'datetime',
}


class FrictionlessMetadata(SerialMetadata):
    """SerialMetadata subclass that reads Frictionless metadata.

    Imports metadata from a Frictionless YAML or JSON file (typically
    foo.resource.yaml or similar for file foo.csv) into the
    SerialMetadata representation.

    Args:
        spec (str or dict): Path to a Frictionless file (.yaml or
            .json), or a dict of the form returned by loading a valid
            Frictionless file. If None, minimal initialization is
            performed.
        extensions (bool): If True, accept tdda Frictionless
            extensions.
        table_number (int): If set, use the nth table (indexed from
            zero) from a multi-table Frictionless file.
        for_table_name (str): If set, select the table whose path ends
            with this name from a multi-table Frictionless file.
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
        verbosity=2,
    ):
        super().__init__(verbosity=verbosity)
        self._url = None
        self._frictionless_base_url = None
        self._frictionless_language = None
        self._extensions = extensions
        self._fullpath = None
        self._source = 'frictionless'
        self._metadata_source_dir = None
        self.table_number = table_number
        self.for_table_name = for_table_name

        if spec is None:  # Only normally used by to_frictionless and tests
            return

        self.read(spec)
        self.get_schema_and_fields()
        self.get_resource_metadata()

        self.get_dialect()
        self.get_schema_and_fields_metadata()

        self.validate()

    def read(self, spec):
        """Read the Frictionless spec from file or dict into ``._frictionless``.

        Args:
            spec (str or dict): Path to a Frictionless file (.yaml or
                .json), or a dict of the form returned by loading one.
        """
        if type(spec) == str:
            self._frictionless = load_json_or_yaml(spec)
            self._metadata_source_path = os.path.abspath(spec)
            self._metadata_source_dir = os.path.dirname(os.path.abspath(spec))
        else:
            self._frictionless = spec

    def get_resource_metadata(self):
        r = self._resource
        self._table_name = r.get('name')  # really resource name. But...
        self.path = r.get('path')
        self._scheme = r.get('scheme')  # file
        self._format = r.get('format')  # csv
        if self._format and self._format != 'csv':
            warn(
                f'The format is "{self._format}"; expected "csv". Continuing.'
            )
        self._mediatype = r.get('mediaType')  # text/csv
        if self._mediatype and self._mediatype != 'text/csv':
            warn(
                f'The format is "{self._format}"; expected "text/csv". Continuing.'
            )
        self.encoding = r.get('encoding')

    def field_to_frictionless_dict(self, field):
        d = {}
        self.set_if_non_null(d, 'name', nvl(field.csvname, field.name))
        self.set_if_non_null(
            d, 'type', FIELDTYPE_TO_FRICTIONLESS.get(field.fieldtype)
        )
        self.set_if_attr_non_null(d, 'titles', 'name')
        fmt = field.format
        if fmt is None and field.fieldtype.startswith('date'):
            fmt = self.date_format
            d['format'] = serial_date_format_to_frictionless(
                fmt, field.fieldtype
            )
        elif field.true_values and field.false_values:
            d['trueValues'] = listify(field.true_values)
            d['falseValues'] = listify(field.false_values)
        elif field.fieldtype == FieldType.BOOL:
            if self.true_values and self.false_values:
                d['trueValues'] = listify(self.true_values)
                d['falseValues'] = listify(self.false_values)
        self.set_if_attr_non_null(d, 'description', 'description')
        return d

    def to_frictionless_dict(
        self, csvfile=None, lang=None, resource_type=None
    ):
        dialect = {}
        self.set_if_attr_non_null(dialect, 'header', 'header_row')
        if self.header_row_count > 0:
            dialect['header'] = True
            dialect['headerRows'] = list(range(nvl(self.header_row_count, 1)))
        self.set_if_attr_non_null(dialect, 'delimiter')
        self.set_if_attr_non_null(dialect, 'quoteChar', 'quote_char')
        self.set_if_attr_non_null(dialect, 'doubleQuote', 'stutter_quotes')
        self.set_if_attr_non_null(dialect, 'escapeChar', 'escape_char')
        name = nvl(csvfile, nvl(self.path, 'data.csv'))
        d = {
            'name': os.path.splitext(os.path.basename(name))[0],
            'type': 'table',
            'path': nvl(csvfile, nvl(self.path, 'data.csv')),
            'scheme': 'file',
            'format': 'csv',
            'mediatype': 'text/csv',
        }
        if self.encoding:
            self.set_if_attr_non_null(d, 'encoding')
        if dialect:
            self.set_if_non_null(d, 'dialect', dialect)

        schema = {}
        fields = [
            self.field_to_frictionless_dict(field) for field in self.fields
        ]
        if fields:
            schema['fields'] = fields
        if listify(self.null_indicator) != []:
            schema['missingValues'] = listify(self.null_indicator)
        for key, attr in (
            ('commentPrefix', 'comment_prefix'),
            ('lineTerminators', 'line_terminator'),
        ):
            self.set_if_attr_non_null(schema, key, attr)

        if self.trim in (True, 'start'):
            schema['skipInitialSpace'], True

        d['schema'] = schema
        if resource_type == 'package':
            d = {'resources': [d]}
        return d

    def write_frictionless(self, path, csvfile=None, indent=None, lang=None):
        if not csvfile:
            csvfile = self.path or self.choose_csv_from_frictionless_name(path)
        basename = os.path.basename(path)
        is_pkg = bool(re.search(r'\.package\.(json|yaml)$', basename))
        resource_type = 'package' if is_pkg else None
        d = self.to_frictionless_dict(
            csvfile=csvfile, lang=lang, resource_type=resource_type
        )
        write_json_or_yaml(d, path, indent=indent)

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

    def get_schema_and_fields(self):
        """Set ``_schema`` and ``_fields`` from the Frictionless spec.

        Handles three layouts: resource inside a package, standalone
        resource with a schema key, or bare schema without a wrapper.
        """
        if 'resources' in self._frictionless:  # package
            self._resources = resources = self._frictionless.get('resources')
            if self._resources:
                N = self.n_resources = len(resources)
                if (
                    N > 1
                    and self.table_number is None
                    and not self.for_table_name
                ):
                    self.warn(f'Only processing first resource of {N}.')
                name = self.for_table_name
                if name:
                    L = len(name)
                    for i, t in enumerate(resources):
                        if t.get('name', '')[-L:] == name:
                            n = self.table_number = i
                            break
                    else:
                        raise KeyError(f'No resource for {name} found.')
                else:
                    n = self.table_number = nvl(self.table_number, 0)
                if len(resources) > n:
                    self._resource = resources[n]
                else:
                    self.n_resources = 0
                    loc = self._metadata_source_path
                    sloc = f' in {loc}' if loc else ''
                    error(f'No resource {n} found{sloc}.')
            else:
                error('No resources in package.')
        elif 'schema' in self._frictionless:
            self._resource = self._frictionless
        else:
            error('No package, resource or schema found')
        self._schema = self._resource.get('schema')
        if not self._schema:
            error('Could not find schema.')

        if type(self._schema) is str:  # TODO
            path = os.path.join(
                nvl(self._metadata_source_dir, ''), self._schema
            )
            self._schema = load_json_or_yaml(path)

        self._fields = self._schema.get('fields')

    def get_url(self):
        self._url = self._frictionless.get('url') or (
            self._table.get('url') if self._table else None
        )
        if not self._url:
            self.warn(
                'Mandatory property "url" not found in Frictionless file.'
            )
        if (
            getattr(self, '_metadata_source_dir', None)
            and self._url
            and not '://' in self._url
        ):
            self._fullpath = os.path.join(self._metadata_source_dir, self._url)

    def get_dialect(self):
        """Read the dialect from the Frictionless spec.

        Supports flat v4 dialect (CSV keys at top level) and the older
        nested ``{'csv': {...}}`` form. Falls back to ``dc:replaces`` if
        no dialect section is present.
        """
        self._dialect = dialect = self._resource.get('dialect', {})
        # Flat form (correct v4): CSV keys at top level of dialect.
        # Nested form (older): CSV keys under dialect['csv'].
        # If 'csv' key present use it; otherwise treat dialect as flat.
        csv = dialect.get('csv') or dialect

        self.header = dialect.get('header')
        self._header_rows = dialect.get('headerRows') or dialect.get(
            'header_rows'
        )
        if self._header_rows is not None:
            self.num_header_rows = len(self._header_rows)
        self._header_join = dialect.get('headerJoin')
        self._header_case = dialect.get('headerCase')
        self.comment_char = dialect.get('commentChar')
        self.skip_blank_rows = dialect.get('skipBlankRows')
        self._comment_rows = dialect.get('commentRows')  # list of rows
        self._descriptor = csv.get('descriptor')  # str|dict
        self.delimiter = csv.get('delimiter')  # str
        self.line_terminator = csv.get('lineTerminator')  # ? str
        self.quote_char = csv.get('quoteChar')  # str
        self.stutter_quotes = csv.get('doubleQuote')  # bool
        self.escape_char = csv.get('escapeChar')  # str
        self.null_sequence = csv.get('nullSequence')  # str
        self.skip_initial_space = csv.get('skipInitialSpace')  # bool
        self.comment_char = csv.get('commentChar')  # str

        if self.null_sequence:  # don't understand what this is
            warn(f'*****\nNULL SEQUENCE FOUND: "{self.null_sequnce}"!!!\n****')

        self.header_row_count = (
            0 if self.header == False else nvl(self.header_row_count, 1)
        )

    def get_schema_and_fields_metadata(self):
        fields = self._schema.get('fields') or []
        self.fields = []
        for i, f in enumerate(fields, 1):
            name = f.get('name')
            if not name:
                error(f'No name for field {i}; skipping.')
            csvname = name
            description = f.get('description')
            examples = f.get('examples')
            raw_fieldtype = f.get('type')
            fieldtype = FRICTIONLESS_TYPE_TO_FIELDTYPE.get(raw_fieldtype)

            true_values = false_values = None
            dps = dp = thou_sep = None
            if fieldtype == FieldType.BOOL:
                true_values = f.get('trueValues')
                false_values = f.get('falseValues')
            if fieldtype in (FieldType.INT, FieldType.FLOAT, FieldType.NUMBER):
                thou_sep = f.get('groupChar')
                if fieldtype in (FieldType.FLOAT, FieldType.NUMBER):
                    dp = f.get('decimal')
            fmt = f.get('format')
            if fieldtype in (FieldType.DATE, FieldType.DATETIME):
                fmt = frictionless_date_format_to_serial(fmt, fieldtype)

            titles = f.get('titles')
            altnames = None
            null_indicator = f.get('missingValues')
            if titles:
                if isinstance(titles, list):
                    altnames = titles
                elif isinstance(titles, dict):
                    altnames = titles
                elif type(titles) is str:
                    altnames = [titles]
                else:
                    self.warn(
                        f'Did not understand value "{titles}"'
                        f'of type "{type(titles)}" '
                        f'for titles of column {name}; ignoring.'
                    )
            description = f.get('dc:description')
            rdf_type = f.get('rdfType')

            field = FieldMetadata(
                name,
                fieldtype=fieldtype,
                csvname=csvname,
                format=fmt,
                null_indicator=null_indicator,
                true_values=true_values,
                false_values=false_values,
                description=description,
                thou_sep=thou_sep,
                dp=dp,
                dps=dps,
                examples=examples,
                altnames=altnames,
                rdf_type=rdf_type,
            )
            self.fields.append(field)
        self.null_indicator = self._schema.get('missingValues')
        self.primary_key = self._schema.get('primaryKey')
        self.foreign_keys = self._schema.get('foreignKeys')

    def choose_csv_from_frictionless_name(self, frictionless_name):
        sep = self.delimiter or ','
        ext = {',': 'csv', '\t': 'tsv', '|': 'psv', ';': 'ssv'}.get(sep, 'txt')
        base_name = os.path.basename(frictionless_name)
        m = re.match(FRICTIONLESS_MD_RE, base_name)
        stem = m.group(1) if m else os.path.splitext(base_name)[0]
        return f'{stem}.{ext}'


def booleans_to_frictionless(true_values, false_values):
    trues, falses = listify(true_values), listify(false_values)
    if len(trues) > 1:
        warn(f'Several true values: using {trues[0]}')
    if len(falses) > 1:
        warn(f'Several false values: using {falses[0]}')
    print(f'>>>{repr(true_values)} --- {repr(false_values)}')
    return f'{trues[0]}|{falses[0]}'


class FrictionlessMultiMetadata:
    def __init__(self, spec, extensions=False):
        table = FrictionlessMetadata(spec, extensions)
        self.tables = [table]
        n_tables = table.n_tables
        if n_tables > 1:
            self.tables.extend(
                [
                    FrictionlessMetadata(spec, extensions, table_number=i)
                    for i in range(1, n_tables + 1)
                ]
            )


def frictionless_date_format_to_serial(fmt, fieldtype=None):
    """
    Converts a Frictionless date format string to a serial format string.

    Frictionless uses Python strptime patterns, 'default', or 'any'.
    """
    if not fmt or fmt == 'default':
        if fieldtype == FieldType.DATE:
            return DateFormat.ISO8601_DATE
        elif fieldtype == FieldType.DATETIME:
            return DateFormat.ISO8601_DATETIME
        return DateFormat.ISO8601_UNSPECIFIED
    if fmt == 'any':
        return None
    return fmt


def serial_date_format_to_frictionless(fmt, extensions=False, fieldtype=None):
    return fmt


def serial_to_frictionless(md):
    """Convert a SerialMetadata object to a FrictionlessMetadata object.

    Args:
        md (SerialMetadata): Metadata to convert.

    Returns:
        A broadly equivalent FrictionlessMetadata object.
    """
    frictionless = FrictionlessMetadata()
    frictionless.__dict__.update(md.__dict__)
    return frictionless


def isyaml(path):
    if path.lower().endswith('yaml'):
        return True
    elif path.lower().endswith('json'):
        return False
    error('Frictionless files should be .yaml or .json')


def load_json_or_yaml(path):
    with open(path) as f:
        if isyaml(path):
            return yamlload(f, Loader=YAMLLoader)
        else:
            return json.load(f)


def write_json_or_yaml(d, path, indent=None, verbose=False):
    with open(path, 'w') as f:
        if isyaml(path):
            f.write(
                yamldump(
                    d,
                    default_flow_style=False,
                    indent=nvl(indent, 2),
                    sort_keys=False,
                )
            )
        else:
            f.write(json.dumps(d, indent=nvl(indent, 4)))
    if verbose:
        print(f'Written {path}.')
