import datetime
import re
import sys

import pandas as pd

from tdda.serial.constants import TDDASERIAL
from tdda.serial.csvw import CSVWMetadata
from tdda.serial.base import (
    SerialMetadata,
    FieldMetadata,
    FieldType,
    DateFormat,
    Defaults
)
from tdda.serial.utils import find_associated_metadata_file
from tdda.utils import nvl, err, warn, listify, Dummy
from tdda.pd.utils import first_non_null


DATETIME_RE = re.compile(r'^datetime[0-9]+\[[a-z]+(,?)(.*)\]$')
DTYPE_RE = re.compile(r'^([A-Za-z])([0-9]+)?(\[[a-z]+(,?)(.*)\])$')


FIELDTYPE_TO_PANDAS_DTYPE = {
    'bool': 'boolean',
    'int': 'Int64',
    'string': 'string',
    'number': 'float',
    'float': 'float',
    'datetime': 'datetime',  # not passed to Pandas
    'date': 'date',          # not passed to Pandas
}


PANDAS_DTYPE_TO_FIELDTYPE = {
    'boolean': 'bool',
    'bool': 'bool',
    'Int': 'int',
    'int': 'int',
    'Float': 'float',
    'float': 'float',
    'string': 'string',
    'object': 'string',
    'float': 'float',
    'datetime': 'datetime',
    'date': 'date',
#    'category' : ???,
#    'period' : ???,
#    'Spares' : ???,
#    'interval' : ???,
#    'Interval' : ???,
}


class PANDAS:
    read_key = 'pandas.read_csv'
    write_key = 'pandas.DataFrame.to_csv'


def csvw2pandas_kwargs(spec, extensions=False):
    """
    Construct a suitable set of kwargs to pass to pandas.read_csv
    to get it to read a CSV file in conformance to the csvw
    specification in spec.

    Args:
        spec should either be a path to a CSVW file (usually .json or .csvw)
             or a dictionary of the form returned by performing
             a json.load such a (valid) CSVW).

    Returns:
        kwargs dictionary for pandas csv_read function, implementing
        the spec given as closely as possible.
    """
    md = CSVWMetadata(spec, extensions=extensions)
    kw = tddaserial_to_pandas_read_csv_args(md)
    return kw


def tddaserial_to_pandas_read_csv_args(md):
    if PANDAS.read_key in md.libs:
        return md.libs[PANDAS.read_key]
    kw = {}
    date_fields = {
        f.name: f for f in md.fields
                if f.fieldtype and f.fieldtype.startswith('date')
    }
    kw['dtype'] = {
        f.name: FIELDTYPE_TO_PANDAS_DTYPE.get(f.fieldtype)
        for f in md.fields
        if f.name not in date_fields
        and FIELDTYPE_TO_PANDAS_DTYPE.get(f.fieldtype) is not None
    } or None
    if any(v.format for v in date_fields):
        kw['date_format'] = {name: to_pandas_date_format(f.format)
                             for name, f in date_fields.items()}
    if date_fields:
        kw['parse_dates'] = list(date_fields)

    if any(v.altnames for v in md.fields):
        kw['names'] = [v.name for v in md.fields]
        kw['header'] = 0

    if md.delimiter:
        kw['sep'] = md.delimiter

    if md.encoding:
        kw['encoding'] = md.encoding

    if md.header_row_count == 0:
        kw['header'] = None

    if md.escape_char:
        kw['escapechar'] = md.escape_char

    if md.quote_char:
        kw['quotechar'] = md.quote_char

    if md.stutter_quotes in (True, False):
        kw['doublequote'] = md.stutter_quotes

    if md.null_indicators is not None:
        kw['na_values'] = listify(md.null_indicators)
        kw['keep_default_na'] = False
    # CSVW-style booleans
    booleans = [
        f.format
        for f in md.fields
        if getattr(f, 'format', None) and f.fieldtype == 'bool'
    ]
    trues, falses = set(), set()
    if booleans:
        for b in booleans:
            parts = b.split('|')
            if len(parts) == 2:
                trues.add(parts[0])
                falses.add(parts[1])
            else:
                print(f'*** Warning: Boolean specification {b} not understood;'
                       ' ignoring')
            if trues.intersection(falses):
                print(f'*** Conflicting values for booleans.')
            else:
                kw['true_values'] = list(trues)
                kw['false_values'] = list(falses)
    names = []
    dtypes = {}
    date_formats = {}
    date_fields = []
    fields = []
    for fmd in md.fields:
        if fmd.true_values and fmd.fieldtype.lower().startswith('bool'):
             trues.update(fmd.true_values)
        if fmd.false_values and fmd.fieldtype.lower().startswith('bool'):
             falses.update(fmd.false_values)
    if trues:
        kw['true_values'] = list(trues)
    if falses:
        kw['false_values'] = list(falses)
    if dtypes:
        kw['dtype'] = dtypes
    if date_formats:
        kw['date_format'] = date_formats
        kw['parse_dates'] = date_fields
    return kw


def pandas_read_csv_to_tddaserial(params, prefer_nullable=False):
    """
    Given a dictionary of pandas.read_csv parameters
    (usually from a 'pandas.read_csv' block in a .serial file),
    Construct the equivalent tdda.serial parameters, so far as possible
    and return these as a pair of dicts---the first with the general
    parameters and the second with the FieldMetadata dictionaries
    """
    kw = {}
    kw['delimiter'] = params.get('sep')
    if 'header' in params:
        header = params['header']
        if header is None:
            kw['header_row_count'] = 0
        elif isinstance(header, list):
            kw['header_row_count'] = len(list)
        elif header == 0 or header == 'infer':
            pass  # don't set
        elif isinstance(header, int):
            kw['header_row_count'] = header + 1
        else:
            warn(f'Value of {header} for header not recognized. Ignoring.')
    kw['escape_char'] = params.get('escapechar')
    kw['quote_char'] = params.get('quotechar')
    kw['stutter_quotes'] = params.get('doublequote')
    true_values = params.get('true_values')
    false_values = params.get('false_values')

    namelist = params.get('names')
    names = nvl(namelist, set())
    has_names = bool(namelist)
    dtypes = params.get('dtypes')
    formats = params.get('date_format')
    if not has_names:
        for source in (dtypes, formats):
            if isinstance(source, dict):
                names.update(set(source))
    fields = []
    for name in names:
        type_ = fmt = None
        if isinstance(dtypes, dict):
            dtype = dtypes.get(name)
            if dtype:
                type_ = pandas_dtype_to_fieldtype(
                    dtype, prefer_nullable=prefer_nullable
                )
        if isinstance(formats, dict):
            date_format = formats.get(name)
            if date_format:
                fmt, type_ = pandas_date_format_to_tddaserial(date_format)
        if has_names or type_ or fmt:
            fields.append(
                FieldMetadata(
                    name, fieldtype=type_, format=fmt,
                    true_values=true_values, false_values=false_values
                )
            )

    if not has_names:
        # Names were not provided as list.
        # Need to turn fields into dictionary so as not to assume
        # it is complete
        fields = {
            field.name: field
            for field in fields
        }
    if fields:
        kw['fields'] = fields
    return kw


def pandas_dtype_to_fieldtype(dtype, col=None, prefer_nullable=True):
    """
    Converts a pandas dtype to a serial.base.FieldType

    Args:

        dtype   is the pandas datatype to be converted.
                It can be provided as the actual dtype (df[col].dtype)
                or as the string version of that (str(df[col].dtype)).

        col     (Optional) the column of values (a pd.Series, typically)

        prefer_nullable:  If True, will demote floats to ints where possible

    Returns:

        The fieldtype (a value from FieldType) if recognized,
        or None if no recognized dtype is found.
    """

    dt = str(dtype) if type(dtype) is not str else dtype
    dtl = dt.lower()
    if dtl.startswith('int') or dtl.startswith('uint'):
        return FieldType.INT
    elif dtl.startswith('float'):
        if prefer_nullable and (col is not None):
            nonnull = col.dropna()
            if nonnull.size > 0:
                if (nonnull.astype(int) == nonnull).sum() == len(nonnull):
                    return FieldType.INT
        return FieldType.FLOAT
    elif dt.startswith('string'):
        return FieldType.STRING
    elif dt.startswith('datetime'):
        m = re.match(DATETIME_RE, dt)
        if m:
            if m.group(1):
                return FieldType.DATETIME_WITH_TIMEZONE
            else:
                return FieldType.DATETIME
    elif dtl.startswith('bool'):
        return FieldType.BOOL
    elif dtl == 'object':
        if col is None:
            return FieldType.STRING  # Most likely
        else:
            nonnulls = col.dropna()
            if nonnulls.size == 0:
                return FieldType.STRING  # Most likely
            r = nonnulls.min()
            m = item(r)
            t = type(m)
            if t is str:
                return FieldType.STRING
            elif pd.isnull(m):
                return FieldType.STRING
            elif t is bool:
                return FieldType.BOOL
            elif t is int:
                return FieldType.INT
            elif t is float:
                return FieldType.FLOAT
            elif t is datetime.date:
                return FieldType.DATE
            elif t is datetime.datetime:
                return FieldType.DATETIME
            elif str(t).endwith('Timestamp'):
                return FieldType.DATETIME_TZ
    else:
        return None


def pandas_write_to_read_params(df, **kw):
    date_format = kw.get('date_format', 'ISO8601')
    d = {
        'encoding': kw.get('encoding', Defaults.ENCODING),
        'delimiter': kw.get('sep', Defaults.DELIMITER),
        'quotechar': kw.get('quotechar', Defaults.QUOTE_CHAR),
        'escapechar': kw.get('escapechar', Defaults.ESCAPE_CHAR),
        'na_values': kw.get('na_rep', Defaults.NULL_INDICATORS),
        'keep_default_na': False,  # because we're specifying na_rep
        'header': None if kw.get('header') == False else 0,
        'date_format': date_format,
    }
    idx = kw.get('index')
    if idx is None or idx == True:
        d['index_col'] = 0       # Use column 0 and index
    else:
        d['index_col'] = False   # Do not use any column as index
                                 #
                                 # Why yes, in Python 0 == False == 0
                                 # So Pandas must be checking the type
                                 # or using is for the comparison
                                 # or something.
                                 #
                                 # Yes, this is a little bit crazy,
                                 # and a big bit confusing.

    typemap = {}
    dts = []
    for col in df:
        t = str(df[col].dtype)
        if is_dtype_writable(t):
            typemap[col] = t
        elif is_dtype_datelike(t):
            dts.append(col)
        elif t != 'object':
            warn(f'Unhandled pandas dtype "{t}"')
        if t == 'object':
            v = first_non_null(df[col])
            if type(v) in (datetime.date, datetime.datetime):
                dts.append(col)

    if typemap:
        d['dtype'] = typemap
    if dts:
        d['parse_dates'] = dts
    return d


def is_dtype_writable(t):
    writable = ('int', 'float', 'bool', 'string')
    for w in writable:
        if t.lower().startswith(w):
            return True
    return False


def is_dtype_datelike(t):
    datelike = ('datetime',)
    for d in datelike:
        if t.lower().startswith(d):
            return True
    return False


def pandas_df_to_metadata(df, outpath=None, flavours=None, **kw):
    """
    Create SerialMetadata for writing DataFrame df from pandas.

    Args:
        df     the DataFrame used to get field name and type information

        outpath   path to which to write the metadata.
                  If None, not written.
                  Always returned.

        flavours: the flavours to include.
                  If no flavours are provided, this will write the tdda.serial
                  form and pandas read and write flavours.

        kw:       the parameters used with df.to_csv

    Returns:
        SerialMetadata object
    """
    fields = [
        pandas_col_to_field_metadata(df[c])
        for c in df
    ]
    idx = kw.get('index')
    if idx != False:  # will write index
        dtype = df.index.dtype
        dtype = pandas_dtype_to_fieldtype(df.index.dtype)
        name = kw.get('index_label') or ''
        index_field = FieldMetadata(name, dtype, description='Pandas Index')
        fields = [index_field] + fields
    header = kw.get('header')
    if header is None or header == 1 or is_sequence(header):  # also True
        header_row_count = 1
    elif header == 0:  # also False
        header_row_count = 0

    flavours = listify(flavours)
    if not flavours:
        flavours = [TDDASERIAL.key, PANDAS.write_key, PANDAS.read_key]
    if TDDASERIAL.key in flavours:
        md = SerialMetadata(
                   fields,
                   # path=path,
                   encoding=kw.get('encoding', Defaults.ENCODING),
                   delimiter=kw.get('sep', Defaults.DELIMITER),
                   quote_char=kw.get('quotechar', Defaults.QUOTE_CHAR),
                   escape_char=kw.get('escapechar', Defaults.ESCAPE_CHAR),
                   null_indicators=kw.get('na_values',
                                          Defaults.NULL_INDICATORS),
                   header_row_count=header_row_count,
                   datetime_format=kw.get('date_format',
                                          DateFormat.ISO8601_UNSPECIFIED),
             )
    else:
        md = SerialMetadata()

    if PANDAS.write_key in flavours:
        # literally the parameters passed in
        lib_params = {
            k: repr(v)
            for k, v in kw.items()
        }
        md.libs[PANDAS.write_key] = lib_params

    if PANDAS.read_key in flavours:
        lib_params = pandas_write_to_read_params(df, **kw)
        md.libs[PANDAS.read_key] = lib_params

    if outpath:
        md.write(outpath)

    return md


def pandas_col_to_field_metadata(field, fieldtype=None,
                                 fmt=None, prefer_nullable=False):
    """
    Produces a FieldMetadata object for the pandas series provided
    in field.

    Args:

        field: a pandas series

        fieldtype:         Optional fieldtype to use. Must be compatible
                           with the data in the field if validate is True

        fmt:               Optional format informaiton for the field

        prefer_nullable:   promote int-ish floats to ints

    Returns:

        FieldMetadata object for the field

    """
    if fieldtype:
        fieldtype = fieldtype
    else:
        fieldtype = pandas_dtype_to_fieldtype(field.dtype, col=field,
                                              prefer_nullable=prefer_nullable)

    if not fmt:
        if fieldtype == FieldType.DATE:
            fmt = DateFormat.ISO8601_DATE
        elif fieldtype == FieldType.DATETIME:
            fmt = DateFormat.ISO8601_DATETIME
        elif fieldtype == FieldType.DATETIME_WITH_TIMEZONE:
            fmt = DateFormat.ISO8601_DATETIME_TZ
    return FieldMetadata(field.name, fieldtype, format=fmt)


def item(v):
    return v.item() if hasattr(v, 'item') else v


def yn2bool(v):
    """
    Convert string v
        to True is it starts with Y or y
        to False if it startsw ith N or n
    Otherwise return None
    """
    return (
        None if pd.isnull(v)
        else True if v.lower().startswith('y')
        else False if v.lower().startswith('n')
        else None
    )


def to_pandas_date_format(v):
    if v is None:
        return None
    if v.startswith('iso8601'):
        return 'ISO8601'
    return v  # for now


def pandas_date_format_to_tddaserial(fmt):
    if fmt == 'ISO8601':
        return DateFormat.ISO8601_UNSPECIFIED, FieldType.ISO8601
    else:
        return fmt


def pandas_df_to_csv(df, path=None,
                     serial_out=None,
                     flavours=None,
                     serial_in=None,
                     preferred_in_flavour=None,
                     find_safe_null=False,
                     **kw):
    """
    Write pandas dataframe provided to flat file to the path or buffer
    provided with options to use a tdda serial file to specify the format
    or to write a companion .serial file.

    Args:
        df: the dataframe to write

    path_or_buf: the path, path object, or buf for writing

    serial_out: An optional tdda serial file to write with the
                format used.
                This can be a path or True.
                If True, the .serial path will be the
                path for the data with the extension swapped to .serial.

    flavours:   By default, the .tddaserial file will include
                  the following three flavours:
                      tdda.serial
                      pandas.DataFrame.to_csv
                      pandas.read_csv
                  If a single flavour, or a list of flavours is provided,
                  that flavour or flavours will be written.
                  '*' can be used to specify that all possible
                  flavours should be written.

    tddaserial_in_path: Path for an optional tdda serial file from which
                        to read the write parameters.
                        If set to True, the the path will be inferred,
                        where possible.

    preferred_in_flavour: If there are multiple formats available
                          in the tddaserial file, by default it will
                          use the first available of:
                             pandas.DataFrame.to_csv
                             pandas.read_csv
                             tdda.serial
                          failing which, anything it can find.

                          If a preferred_flavour is specified,
                          that will be used if available.

    **kw: keyword parameters are passed straight to DataFrame.write_csv.
          Any specified here override those generated be reading
          tddaserial_in_path. It is usually better not to mix
          tddaserial_in_path and **kw, as it is easy to generate
          incompatibilities.

    Returns:
        Object with:
            .serial_out_path  (if written, else None)
            .path             (path written to)
    """
    serial_in_path = serial_out_path = None
    if serial_in:
        if serial_in == True:
            serial_in_path = find_associated_metadata_file(path)
            if not serial_in:
                err(f'Cannot find input .serial metadata associated'
                    f' with {path}')
        else:
            serial_in_path = serial_in

    # TODO: worry about usecols

    md_in = None
    if serial_in_path:
        md = load_metadata(serial_in_path,
                           preferred_serial_flavour=preferred_in_flavour)

    if serial_out:
        if serial_out == True:
            serial_out_path = find_associated_metadata_file(path)
            if not serial_out:
                err(f'Cannot find output .serial metadata associated'
                    f' with {path}')
        else:
            serial_out_path = serial_out

    if find_safe_null:
        kw['na_rep'] = find_safe_null_rep(df)

    if path:  # if None, just write the metadata
        df.to_csv(path, **kw)  # write the csv

    if serial_out_path:
        md_out = pandas_df_to_metadata(df, outpath=serial_out_path,
                                       flavours=flavours,
                                       **kw)

    d = Dummy()
    d.serial_out_path = serial_out_path
    d.out_path = path
    return d



