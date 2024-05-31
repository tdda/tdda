import json
import sys

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

    STRING = 'string'


class DateFormat:
    ISO8601_DATE = 'iso8601date'
    ISO8601_DATETIME = 'iso8601datetime'
    ISO8601_DATETIME_TZ = 'iso8601datetime_tz'

    EURO_DATE = 'eu date'
    EURO_DATETIME = 'eu datetime'


class URI:
    TDDAMETADATA = 'http://tdda.info/ns/tddametadata'
    CSVW = 'http://www.w3.org/ns/csvw'


CONTEXT_KEY = '@context'
RE_ISO8601 = r'^%Y-%m-%d([T ]%H:%M:%S(\.%f)?)?$'

VERBOSITY = 2     # show errors and warnings. 1 for errors only. 0 for none

MTYPES = tuple(FieldType.__dict__.values())


class MetadataError(Exception):
    pass


class FieldMetadata:
    """
    Container for data about a field (column) in a serial data source
    such as CSV file

    Args:
        name:   Name of the field/column. This need not be the same as the
                name in the file. MANDATORY.

        mtype:  the type of the field. Must be one of the values
                in MTYPES. MANDATORY.

        csvname: Name of the column in the file. OPTIONAL.

        format:  Format of the field in the file.
                 Used mainly with date and datetime columns.
                 OPTIONAL

        nullmarkers: values to be interpreted as NULL (missing/NA) values.
                     OPTIONAL.


    """
    def __init__(self, name, mtype=None,
                 format=None, nullmarkers=None,
                 allow_extras=False, **kw):
        self.name = name
        self.mtype = mtype
        self.altnames = None

        self.delimiter = None
        self.encoding = None

        self.header_row_count = None
        self.comment_prefix = None
        self.line_terminators = None
        self.quote_char = None
        self.skip_blank_rows = None
        self.skip_initial_space = None
        self.skip_columns = None
        self.skip_rows = None
        self.nullmarkers = nullmarkers
        # stutter

        for k, v in kw.items():
            if allow_extras:
                self.__dict__[k] = v
            else:
                msg = f'Unexpected kwarg to FieldMetadata for {name}: "{k}"'
                raise KeyError(msg)

        self.errors = []
        self.warnings = []

        self.valid = None

    def get_val(self, d, k, missing=MISSING.ALLOWED):
        if not k in d:
            msg = f'Key "{k}" not found for field {self.name}'
            if missing == MISSING.ERROR:
                self.errors.append(msg)
            elif missing == MISSING.WARNING:
                self.warnings.append(msg)
            elif missing != MISSING.ALLOWED:
                raise Exception(f'Unknown value "{missing}" for missing')
        return d.get(k, None)

    def validate(self):
        if self.mtype not in MTYPES:
            self.errors.append(
                f'Unknown field type "{self.mtype}" for field {self.name}'
            )

    def unobjectify(self):
        return {k: unobjectify(v) for k, v in self.__dict__.items()
                if nonnull(v)}


class Metadata:
    def __init__(self,
        fields=None,
        path=None,
        encoding=None,
        delimiter=None,
        quote_char=None,
        escape_char=None,
        stutter_quotes=None,
        date_format=None,
        null_indicators=None,
        header_rows=0,
        verbosity=VERBOSITY
    ):
        self.fields = fields or []
        self.path = path
        self.encoding = encoding
        self.delimiter = delimiter
        self.quote_char = quote_char
        self.escape_char = escape_char
        self.stutter_quotes = stutter_quotes
        self.date_format = None

        self.errors = []
        self.warnings = []

        self.metadata_source = None
        self.metadata_source_path = None
        self.valid = None
        self.header_rows = header_rows
        self._verbosity = verbosity

#        self.metametadata = {
#            'creationhash': ''
#        }


    def error(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    def get_val(self, d, k, missing=MISSING.ALLOWED):
        if not k in d:
            msg = f'Key "{k}" not found in file metadata.'
            if missing == MISSING.ERROR:
                self.error(msg)
            elif missing == MISSING.WARNING:
                self.warn(msg)
            elif missing != MISSING.ALLOWED:
                raise Exception(f'Unknown value "{missing}" for missing.')
        return d.get(k, None)

    def validate(self):
        valid = True
        if self._verbosity > 0:
            for msg in self.errors:
                print(f'** FATAL ERROR: {msg}', file=sys.stderr)
                valid = False
            for field in self.fields:
                field.validate()
                for msg in field.errors:
                    print(f'** FATAL ERROR: {msg}', file=sys.stderr)
                    valid = False
        if self._verbosity > 1:
            for msg in self.warnings:
                print(f'** WARNING: {msg}', file=sys.stderr)
            for field in self.fields:
                for msg in field.warnings:
                    print(f'** WARNING: {msg}', file=sys.stderr)

        self.valid = valid

    def unobjectify(self):
        d = {'@context': URI.TDDAMETADATA}
        d.update({
            k: unobjectify(v) for k, v in self.__dict__.items()
                                  if not k.startswith('_')
                                  and nonnull(v)
        })
        return d

    def to_json(self, indent=4):
        return json.dumps(self.unobjectify(), indent=indent)

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
    raise Exception('Attempt to unobjectify unexpected type.\n'
                    f'Type: {type(o)}: Value: {repr(o)}')


def nonnull(v):
    """
    test value v for whether it should be dumped.
    """
    return v is not None and v != [] and v != () and v != {}
