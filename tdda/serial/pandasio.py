import datetime
import os
import re
import sys

from collections import namedtuple

import numpy as np
import pandas as pd

from tdda.serial.constants import TDDASERIAL
from tdda.serial.csvw import CSVWMetadata
from tdda.serial.metadata import (
    DateFormat,
    Defaults,
    FieldMetadata,
    FieldType,
    SerialMetadata,
    VERBOSITY,
    TDDASerialError
)
from tdda.serial.reader import (
    get_metadata_for_reader,
    get_metadata_for_writer,
    set_delimiter_from_path
)
from tdda.serial.utils import (
    find_associated_metadata_file, get_backend, OG_BACKEND, choose_md_path,
    PYTHON_TEMPLATES, fill_template
)
from tdda.utils import nvl, error, warn, listify, delistify, Dummy
from tdda.pd.utils import first_non_null, is_string_col, find_safe_null_rep
from tdda.referencetest.pddates import infer_date_format

DATETIME_RE = re.compile(r'^datetime[0-9]+\[[a-z]+(,?)(.*)\]$')
DTYPE_RE = re.compile(r'^([A-Za-z])([0-9]+)?(\[[a-z]+(,?)(.*)\])$')

FIELDTYPE_TO_PANDAS_OLD_DTYPE = {
    'bool': 'object',
    'int': None,
    'string': 'object',
    'number': 'float',
    'float': 'float',
    'datetime': 'datetime',  # not passed to Pandas
    'date': 'date',          # not passed to Pandas
}


FIELDTYPE_TO_PANDAS_NULLABLE_DTYPE = {
    'bool': 'boolean',
    'int': 'Int64',
    'string': 'string',
    'number': 'Float64',
    'float': 'Float64',
    'datetime': 'datetime',  # not passed to Pandas
    'date': 'date',          # not passed to Pandas
}


FIELDTYPE_TO_PYARROW_DTYPE = {
    'bool': 'bool[pyarrow]',
    'int': 'int64[pyarrow]',
    'string': 'string[pyarrow]',  # same as string
    'number': 'double[pyarrow]',
    'float': 'double[pyarrow]',
    'datetime': 'timestamp[ns][pyarrow]',  # is actually read as datetime64[ns]
    'date': 'date64[pyarrow]',
}


FIELDTYPE_MAP_MAP = {
    OG_BACKEND: FIELDTYPE_TO_PANDAS_OLD_DTYPE,
    'numpy_nullable': FIELDTYPE_TO_PANDAS_NULLABLE_DTYPE,
    'pyarrow': FIELDTYPE_TO_PYARROW_DTYPE,
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


DataFrameWithMetadata = namedtuple('DataFrameWithMetadata', 'df md')
WriteInfo = namedtuple('WriteInfo', 'path md_outpath md_inpath kw')


class PANDAS:
    read_key = 'pandas.read_csv'
    write_key = 'pandas.DataFrame.to_csv'


def csvw_to_pandas_kwargs(spec, extensions=False):
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
    kw = serial_to_pandas_read_csv_args(md)
    return kw


def to_common_pandas_rw_args(md):
    kw = {}
    if md.delimiter:
        kw['sep'] = md.delimiter

    if md.encoding:
        kw['encoding'] = md.encoding

    if md.escape_char:
        kw['escapechar'] = md.escape_char

    if md.quote_char:
        kw['quotechar'] = md.quote_char

    if md.stutter_quotes in (True, False):
        kw['doublequote'] = md.stutter_quotes

    return kw


def serial_type_to_pandas_dtype(fieldtype, backend=None, config=None):
    type_map = FIELDTYPE_MAP_MAP[get_backend(backend, config)]
    return type_map.get(fieldtype)


def serial_to_pandas_read_csv_args(md, backend=None, warner=None, config=None):
    Warn = nvl(warner, warn)
    backend = get_backend(backend, config)
    if PANDAS.read_key in md.libs:
        return md.libs[PANDAS.read_key]
    kw = to_common_pandas_rw_args(md)
    date_fields = {
        f.name: f for f in md.fields
                if f.fieldtype and f.fieldtype.startswith('date')
    }
    dtypes = {
        f.name: serial_type_to_pandas_dtype(f.fieldtype, backend)
        for f in md.fields
    }
    kw['dtype'] = {
        name: dtype
        for name, dtype in dtypes.items()
        if name not in date_fields
        and dtype is not None
    } or None
    dfmt = md.date_format
    if any(v.format for v in date_fields) or dfmt:
        kw['date_format'] = {name: to_pandas_date_format(f.format or dfmt)
                             for name, f in date_fields.items()}
    if date_fields:
        kw['parse_dates'] = list(date_fields)

    if any(v.altnames for v in md.fields):
        kw['names'] = [v.name for v in md.fields]
        kw['header'] = 0

    if md.header_row_count == 0:
        kw['header'] = None

    if md.null_indicator is not None:
        kw['na_values'] = delistify(md.null_indicator)
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
                kw['true_values'] = sorted(list(trues))
                kw['false_values'] = sorted(list(falses))
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
    if any(f.name != f.csvname for f in md.fields):
        kw['names'] = [f.name for f in md.fields]
        kw['header'] = 0
    if trues:
        kw['true_values'] = sorted(list(trues))
    if falses:
        kw['false_values'] = sorted(list(falses))

    if (
        (trues or falses)
        and backend == 'pyarrow'
        and any(v == 'bool[pyarrow]' for v in dtypes.values())
   ):
        Warn(
           'PyArrow backend does not understand alternate booleans.\n'
           'If they are really present, you may have to read as strings.')
    if dtypes:
        kw['dtype'] = dtypes
    if date_formats:
        kw['date_format'] = date_formats
        kw['parse_dates'] = date_fields
    return kw


def serial_to_pandas_write_csv_args(md, backend=None, config=None):
    backend = get_backend(backend, config)
    if PANDAS.write_key in md.libs:
        return md.libs[PANDAS.write_key]

    kw = to_common_pandas_rw_args(md)
    kw['date_format'] = to_pandas_date_format(md.single_date_format())

    date_fields = [f for f in md.fields if f.fieldtype.startswith('date')]
    if date_fields:
        kw['parse_dates'] = list(date_fields)

    null = md.single_null_indicator()
    if null is not None:
        kw['na_rep'] = null

    if md.header_row_count == 0:
        kw['header'] = None
    elif md.header_row_count == 1:
        kw['header'] = 0

    if md.stutter_quotes in (True, False):
        kw['doublequote'] = md.stutter_quotes

    kw['na_rep'] = md.single_null_indicator()

    # Possibly map to csv names
    # Possibly check for nulls in string fields
    return kw


def pandas_read_csv_to_serial(params, backend=None, warner=None, config=None):
    """
    Given a dictionary of pandas.read_csv parameters
    (usually from a 'pandas.read_csv' block in a .serial file),
    Construct the equivalent tdda.serial parameters, so far as possible
    and return these as a pair of dicts---the first with the general
    parameters and the second with the FieldMetadata dictionaries
    """
    Warn = nvl(warner, warn)
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
            Warn(f'Value of {header} for header not recognized. Ignoring.')
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
    backend = get_backend(backend, config)
    for name in names:
        type_ = fmt = None
        if isinstance(dtypes, dict):
            dtype = dtypes.get(name)
            if dtype:
                type_ = pandas_dtype_to_fieldtype(dtype)
        if isinstance(formats, dict):
            date_format = formats.get(name)
            if date_format:
                fmt, type_ = pandas_date_format_to_serial(date_format)
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


def pandas_dtype_to_fieldtype(dtype, col=None):
    """
    Converts a pandas dtype to a serial.base.FieldType

    Args:

        dtype   is the pandas datatype to be converted.
                It can be provided as the actual dtype (df[col].dtype)
                or as the string version of that (str(df[col].dtype)).

        col     (Optional) the column of values (a pd.Series, typically)

        backend:  Preferred backend for pandas

    Returns:

        The fieldtype (a value from FieldType) if recognized,
        or None if no recognized dtype is found.
    """
    dt = str(dtype) if type(dtype) is not str else dtype
    dtl = dt.lower()
    if dtl.startswith('int') or dtl.startswith('uint'):
        return FieldType.INT
    elif dtl.startswith('float'):
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


def pandas_write_to_read_params(df, warner=None, **kw):
    Warn = nvl(warner, warn)
    date_format = kw.get('date_format', 'ISO8601')
    d = {
        'encoding': kw.get('encoding', Defaults.ENCODING),
        'delimiter': kw.get('sep', Defaults.DELIMITER),
        'quotechar': kw.get('quotechar', Defaults.QUOTE_CHAR),
        'escapechar': kw.get('escapechar', Defaults.ESCAPE_CHAR),
        'na_values': delistify(kw.get('na_rep', Defaults.NULL_INDICATOR)),
        'keep_default_na': False,  # because we're specifying na_rep
        'header': None if kw.get('header') == False else 0,
        'date_format': date_format,
    }
    idx = kw.get('index')
    if idx is None or idx == True:
        d['index_col'] = 0       # Use column 0 and index
    else:
        d['index_col'] = None   # Do not use any column as index
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
            Warn(f'Unhandled pandas dtype "{t}"')
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


def pandas_df_to_metadata(df, outpath=None, flavour=None, **kw):
    """
    Create SerialMetadata for writing DataFrame df from pandas.

    Args:
        df     the DataFrame used to get field name and type information

        outpath   path to which to write the metadata.
                  If None, not written.
                  Always returned.

        flavour: the flavour or flavours to include.
                 Can be a string (for a single flavour) or a list
                 If no flavours are provided, this will write the tdda.serial.

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

    flavours = listify(flavour)
    if not flavours:
        flavours = [TDDASERIAL.key]  # , PANDAS.write_key, PANDAS.read_key]
    if TDDASERIAL.key in flavours:
        md = SerialMetadata(
                   fields,
                   # path=path,
                   encoding=kw.get('encoding', Defaults.ENCODING),
                   delimiter=kw.get('sep', Defaults.DELIMITER),
                   quote_char=kw.get('quotechar', Defaults.QUOTE_CHAR),
                   escape_char=kw.get('escapechar', Defaults.ESCAPE_CHAR),
                   null_indicator=kw.get('na_rep',
                       delistify(Defaults.NULL_INDICATOR)),
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
                                 fmt=None, backend=None):
    """
    Produces a FieldMetadata object for the pandas series provided
    in field.

    Args:

        field: a pandas series

        fieldtype:         Optional fieldtype to use. Must be compatible
                           with the data in the field if validate is True

        fmt:               Optional format informaiton for the field

        backend:           Preferred pandas backend

    Returns:

        FieldMetadata object for the field

    """
    if fieldtype:
        fieldtype = fieldtype
    else:
        fieldtype = pandas_dtype_to_fieldtype(field.dtype, col=field)

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


def pandas_date_format_to_serial(fmt):
    if fmt == 'ISO8601':
        return DateFormat.ISO8601_UNSPECIFIED, FieldType.ISO8601
    else:
        return fmt



def csv_to_pandas(path=None, md_path=None, md_file_type=None,
                  find_md=False, backend=None,
                  upgrade_types=True, upgrade_possible_ints=False,
                  return_md=False, table_number=None, use_table_name=False,
                  preferred=None, verbosity=VERBOSITY,
                  infer_datetime_formats=False, warner=None,
                  config=None, **kw):
    """
    Load the data from a CSV file into a Pandas DataFrame use pandas.read_csv
    and extra metadata.

    Args:

       path     The path to the data file (usually CSV) to be read.
                If this is None, the md_path must be set and contain
                the path to the data.

       md_path   The optional path to the associated metadata file.

                 If path is None, this must be set and contain the
                 path to the data (CSV file).

                 If path is not None, the path in the metadata file
                 is ignored.

                 If md_path is None, path must not be None.
                 In this case, if findmd is set to True, this function
                 will try to find an associated metadata file and use
                 that if possible, and will raise an error if it cannot
                 be found.

       md_file_type   Optional specification of the kind of metadata file.
                      Should be one of
                          'tdda.serial'
                          'csvw'
                          'frictionless'

       find_md   If this is set to True, the library will try to find
                 associated metadata based on filename conventions.
                 This should not be set if md_path is provided.
                 If associated metadata cannot be found, an error
                 will be raised when this is set.

       nullable  Set to False to use traditional Pandas
                 non-nullable types for floats etc.

       upgrade_types   If True (the default), this will upgrade
                       some columns read_csv will create as object
                       (dtype object) to stricter types.

       upgrade_possible_ints   If True (not the default), any float
                               columns with nulls but with no fractional
                               components will be upgraded to Ints.

       return_md     If true, returns DataFrame and metadata (as tuple)

       table_number  If set, use the specified table number (indexed
                     from zero) in the metadata

       preferred  Normally, if tdda.serial metadata is used,
                  csv_to_pandas will use the panda.read_csv metadata flavour
                  if present. This can be set to 'tdda.serial'
                  or 'csvw' to override that.

       verbosity   For metadata Reader

       **kw     These keyword arguments are passed to pandas.read_csv,
                and can be used to override values from the
                metadata file.
    """
    md, path, md_path = get_metadata_for_reader(
         path=path, md_path=md_path, md_file_type=md_file_type,
         find_md=find_md, table_number=table_number,
         use_table_name=use_table_name,
         preferred=preferred or 'pandas.read_csv',
         verbosity=verbosity
    )
    backend = get_backend(backend, config)
    if md:
        md_kw = serial_to_pandas_read_csv_args(md, backend=backend,
                                               warner=warner)
    if md and kw:
        md_kw.update(kw)
        kw = md_kw
    elif md:
        kw = md_kw
    else:
        if not 'backend' in kw:
            backend = get_backend(backend, config)
            if backend and backend != OG_BACKEND:
                kw['dtype_backend'] = backend

    kw = set_delimiter_from_path(kw, path, 'sep')

    df = pd.read_csv(path, **kw)
    specified_types = kw.get('dtype')
    dates = []
    if upgrade_types and specified_types:
        dfmt = kw.get('date_format')
        if isinstance(dfmt, dict):
            dates = list(dfmt.keys())
            # should be using these!
        for k in df:
            if df[k].dtype == np.dtype('O'):
                specified_type = specified_types.get(k)
                try:
                    if specified_type:
                        df[k] = df[k].astype(specified_type)
                    elif k in dates:
                        df[k] = df[k].astype('datetime64[ns]')
                except ValueError:  # probably time-zone aware date
                    pass

    if upgrade_possible_ints:
        for k in df:
            if not k in (specified_types or []):
                poss_upgrade_to_int(df, k)

    if infer_datetime_formats:
        df = infer_dates(df, specified_types)
    return DataFrameWithMetadata(df, md) if return_md else df


def serial_to_pandas_read_csv_python(md, backend=None, warner=None,
                                     config=None):
    backend = get_backend(backend, config)
    kw = serial_to_pandas_read_csv_args(md, backend=backend, warner=warner)
        # if 'dtype_backend' not in kw:
        #     backend = get_backend(backend)
        #     if backend != OG_BACKEND:
        #        kw = {'dtype_backend': backend}
    if not md and 'backend' not in kw:
        backend = get_backend(backend)
        if backend and backend != OG_BACKEND:
            kw['dtype_backend'] = backend
    return fill_template(PYTHON_TEMPLATES.PANDAS_READ, kw)


def pandas_to_csv(df, path=None,
                  md_inpath=None,
                  md_outpath=None,
                  auto_md_inpath=False,
                  auto_md_outpath=False,
                  flavour=None,
                  preferred_in_flavour=None,
                  in_table_number=None,
                  find_safe_null=False,
                  warner=None,
                  **kw_overrides):
    """
    Write pandas dataframe provided to flat file to the path or buffer
    provided with options to use a tdda serial file to specify the format
    or to write a companion .serial file.

    Args:
        df: the dataframe to write

    path_or_buf: the path, path object, or buf for writing

    md_inpath:  An optional tdda serial (or csvw) file to write
                alongside the CSV data.

    md_outpath: An optional tdda serial file to write with the
                format used.
                This can be a path or True.
                If True, the .serial path will be the
                path for the data with the extension swapped to .serial.

    auto_md_inpath: If true, will choose the inpath for metadata
                    automatically

    auto_md_outpath: If true, will choose the outpath for metadata
                     automatically

    flavour:   By default, the .serial file will include only tdda.serial.
               Either a single flavour (as a string)
               or a list of flavours can be provided.

    preferred_in_flavour: If there are multiple formats available
                          in the tdda.serial file, by default it will
                          use the first available of:
                             pandas.DataFrame.to_csv
                             pandas.read_csv
                             tdda.serial
                          failing which, anything it can find.

                          If a preferred_flavour is specified,
                          that will be used if available.

    find_safe_null: If true, a null representation will be chosen
                    that is safe for this data (not present in any
                    string column).

    **kw_overrides: keyword parameters are passed straight to DataFrame.to_csv.
          Any specified here override those generated be reading
          in_mdpath. It is usually better not to mix
          in_mdpath and **overrides, as it is easy to generate
          incompatibilities. Any na_rep specified as an override
          will be replaced if find_safe_null is set and the nominated
          null indicator is not, in fact safe. (A warning is issued.)

    Returns:
        Object with:
            .md_out_path    (if written, else None)
            .out_path       (path data written to, if any)
            .md_inpath      (the path from which metadata for writing was read)
            .to_csv_kwargs  (the keyword args used to write the CSV file)
    """
    Warn = nvl(warner, warn)
    md_in, path, md_inpath = get_metadata_for_writer(
         path=path, md_path=md_inpath,
         find_md=auto_md_inpath,
         preferred=preferred_in_flavour or 'pandas.write_csv'
    )

    if md_in:
        kw = serial_to_pandas_write_csv_args(md_in)
    else:
        kw = {}
    if not kw.get('index'):
        kw['index'] = False

    if find_safe_null:
        spec = kw_overrides.get('na_rep')
        null = find_safe_null_rep(df, preferred=overrides.get('na_rep'))
        kw['na_rep'] = null
        if specified_null is not None and spec != null:
            Warn(f'Specified null rep "{spec}" was not safe. '
                 f'Using "{null}".\n(Safe null rep was requested.)')


    kw.update(kw_overrides)  # overrides passed in

    if path:  # if None, just write the metadata
        df.to_csv(path, **kw)  # write the csv

    if auto_md_outpath and not md_outpath:
        md_outpath = choose_md_path(path, flavour)
    if md_outpath:
        md_out = pandas_df_to_metadata(df, outpath=md_outpath,
                                       flavour=flavour,
                                       **kw)

    return WriteInfo(path, md_outpath, md_inpath, kw)


def poss_upgrade_to_int(df, name):
    field = df[name]
    if str(field.dtype).lower().startswith('float'):
        n_nulls = sum(field.isnull())
        if n_nulls > 0:
            # Could be float as result of nulls
            int_col = field.astype(pd.Int64Dtype())
            n_same = sum(int_col.dropna() == field.dropna())
            if n_same + n_nulls == field.shape[0]:
                # no floats have fractional parts
                df[name] = int_col
        else:
            int_col = field.astype('int')
            n_same = sum(int_col== field)
            if n_same == field.shape[0]:
                # no floats have fractional parts
                df[name] = int_col


def infer_dates(df, specified_types=None):
    colnames = df.columns.tolist()
    for c in colnames:
        spec = (specified_types or {}).get(c)
        if is_string_col(df[c]) and spec not in ('string', 'object'):
            fmt = infer_date_format(df[c])
            if fmt:
                try:
                    datecol = pd.to_datetime(df[c], format=fmt)
                    if datecol.dtype == np.dtype('datetime64[ns]'):
                        df[c] = datecol
                except Exception as e:
                    pass
    # ndf = pd.DataFrame()
    # for c in colnames:
    #     ndf[c] = df[c]
    # return ndf
    return df


def pandas_read_df(path, backend=None, config=None, **kw):
    """
    Reads a pandas data frame from parquet or csv, as the extension suggests.
    Prefers nullable types.
    """
    _, ext = os.path.splitext(path)
    if ext == '.csv':
        return csv_to_pandas(path, backend=backend, config=config, **kw)
    elif ext == '.parquet':
        # return pd.read_parquet(path, use_nullable_dtype=True)
        backend = get_backend(backend, config)
        if backend == OG_BACKEND:
            return pd.read_parquet(path)
        else:
            return pd.read_parquet(path, dtype_backend=backend)
    else:
        raise TDDASerialError(f'Unexpected extension {ext} in {path}.')


def pandas_write_df(df, path, **kw):
    """
    Writes a pandas data frame as parquet or csv, as the extension suggests.
    Does not write the index.
    """
    _, ext = os.path.splitext(path)
    if 'index' not in kw:
        kw = kw.copy()
        kw['index'] = None
    if ext == '.csv':
        df.to_csv(path, **kw)
    elif ext == '.parquet':
        df.to_parquet(path, **kw)
    else:
        raise TDDASerialError(f'Unexpected extension {ext} in {path}.')
