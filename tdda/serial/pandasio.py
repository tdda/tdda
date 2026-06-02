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
    TDDASerialError,
    NAMED_FORMAT_TO_STRFTIME,
    STRFTIME_TO_NAMED_FORMAT,
    ISO8601_NAMED_FORMATS,
    UNSPECIFIED_NAMED_FORMATS,
    ALL_NAMED_FORMATS,
    serial_format_to_strftime,
)
from tdda.serial.reader import (
    get_metadata_for_reader,
    get_metadata_for_writer,
    set_delimiter_from_path,
)
from tdda.serial.utils import (
    find_associated_metadata_file,
    get_backend,
    OG_BACKEND,
    choose_md_path,
    PYTHON_TEMPLATES,
    fill_template,
    DataFrameWithMetadata,
)
from tdda.utils import nvl, error, warn, listify, delistify, is_sequence, Dummy
from tdda.pd.utils import first_non_null, is_string_col, find_safe_null_rep
from tdda.referencetest.pddates import infer_date_format

DATETIME_RE = re.compile(r'^datetime[0-9]+\[[a-z]+(,?)(.*)\]$')
DTYPE_RE = re.compile(r'^([A-Za-z])([0-9]+)?(\[[a-z]+(,?)(.*)\])$')

PANDAS_ISO8601 = 'ISO8601'

FIELDTYPE_TO_PANDAS_OLD_DTYPE = {
    'bool': 'object',
    'int': None,
    'string': 'object',
    'number': 'float',
    'float': 'float',
    'datetime': 'datetime',  # not passed to Pandas
    'date': 'date',  # not passed to Pandas
}


FIELDTYPE_TO_PANDAS_NULLABLE_DTYPE = {
    'bool': 'boolean',
    'int': 'Int64',
    'string': 'string',
    'number': 'Float64',
    'float': 'Float64',
    'datetime': 'datetime',  # not passed to Pandas
    'date': 'date',  # not passed to Pandas
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


WriteInfo = namedtuple('WriteInfo', 'path md_outpath md_inpath kw')


class PANDAS:
    read_key = 'pandas.read_csv'
    write_key = 'pandas.DataFrame.to_csv'


def csvw_to_pandas_kwargs(spec, extensions=False):
    """Return ``pandas.read_csv`` kwargs that implement a CSVW spec.

    Args:
        spec (str or dict): Path to a CSVW file (.json or .csvw), or
            a dict of the form returned by json.load on one.
        extensions (bool): If True, accept tdda CSVW extensions.

    Returns:
        Dict of keyword arguments for ``pandas.read_csv``.
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
    """Convert SerialMetadata to keyword arguments for pandas.read_csv.

    Args:
        md (SerialMetadata): Metadata describing the CSV file format.
        backend (str): Pandas dtype backend, e.g. 'numpy_nullable' or
            'pyarrow'.
        warner: Optional callable for issuing warnings.
        config: Optional tdda configuration object.

    Returns:
        Dict of keyword arguments suitable for passing to
        pandas.read_csv.
    """
    Warn = nvl(warner, warn)
    backend = get_backend(backend, config)
    if PANDAS.read_key in md.libs:
        return md.libs[PANDAS.read_key]
    kw = to_common_pandas_rw_args(md)
    date_fields = {
        f.name: f
        for f in md.fields
        if f.fieldtype and f.fieldtype.startswith('date')
    }
    dtypes = {
        f.name: serial_type_to_pandas_dtype(f.fieldtype, backend)
        for f in md.fields
    }
    kw['dtype'] = {
        name: dtype
        for name, dtype in dtypes.items()
        if name not in date_fields and dtype is not None
    } or None
    dfmt = nvl(md.date_format, md.datetime_format)
    dtfmt = nvl(md.datetime_format, md.date_format)
    if any(v.format for v in date_fields.values()) or dfmt:
        kw['date_format'] = {
            name: to_pandas_date_format(
                f.format or (dfmt if f.fieldtype == 'date' else dtfmt)
            )
            for name, f in date_fields.items()
        }
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
                print(
                    f'*** Warning: Boolean specification {b} not understood; ignoring'
                )
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
        if fmd.fieldtype and fmd.fieldtype.lower().startswith('bool'):
            trues.update(fmd.true_values or md.true_values or [])
            falses.update(fmd.false_values or md.false_values or [])
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
            'If they are really present, you may have to read as strings.'
        )
    if dtypes:
        kw['dtype'] = dtypes
    if date_formats:
        kw['date_format'] = date_formats
        kw['parse_dates'] = date_fields
    return kw


def serial_to_pandas_write_csv_args(
    md, backend=None, config=None, warner=None
):
    backend = get_backend(backend, config)
    if PANDAS.write_key in md.libs:
        return md.libs[PANDAS.write_key]

    kw = to_common_pandas_rw_args(md)
    kw['date_format'] = to_pandas_date_format(
        md.single_date_format(), for_write=True
    )

    null = md.single_null_indicator()
    if null is not None:
        kw['na_rep'] = null

    if md.header_row_count == 0:
        kw['header'] = False

    if md.stutter_quotes in (True, False):
        kw['doublequote'] = md.stutter_quotes

    kw['na_rep'] = md.single_null_indicator()

    # Possibly map to csv names
    # Possibly check for nulls in string fields
    return kw


def pandas_read_csv_to_serial(params, backend=None, warner=None, config=None):
    """Convert a ``pandas.read_csv`` parameter dict to tdda.serial parameters.

    Typically used with a ``'pandas.read_csv'`` block from a ``.serial``
    file. Returns a dict of general SerialMetadata kwargs (including a
    ``fields`` entry with FieldMetadata dicts where applicable).
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
                    name,
                    fieldtype=type_,
                    format=fmt,
                    true_values=true_values,
                    false_values=false_values,
                )
            )

    if not has_names:
        # Names were not provided as list.
        # Need to turn fields into dictionary so as not to assume
        # it is complete
        fields = {field.name: field for field in fields}
    if fields:
        kw['fields'] = fields
    return kw


def pandas_dtype_to_fieldtype(dtype, col=None):
    """Convert a pandas dtype to a ``FieldType`` constant.

    Args:
        dtype: The pandas dtype, as a dtype object or its string
            representation (e.g. ``str(df[col].dtype)``).
        col (pd.Series): Optional column of values; used to inspect
            actual Python types when dtype is ``object``.

    Returns:
        A ``FieldType`` value if recognized, or ``None``.
    """
    dt = str(dtype) if type(dtype) is not str else dtype
    dtl = dt.lower()
    if dtl.startswith('int') or dtl.startswith('uint'):
        return FieldType.INT
    elif dtl.startswith('float'):
        return FieldType.FLOAT
    elif dt.startswith('str'):
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
    date_format = kw.get('date_format', PANDAS_ISO8601)
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
        d['index_col'] = 0  # Use column 0 and index
    else:
        d['index_col'] = None  # Do not use any column as index
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
        elif t not in ('object', 'str'):
            Warn(f'Unhandled pandas dtype "{t}"')
        if t in ('object', 'str'):
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
    """Create SerialMetadata for a DataFrame being written with pandas.

    Args:
        df (pd.DataFrame): Source of field names and type information.
        outpath (str): Path to write metadata to; if None, not written
            but the SerialMetadata object is still returned.
        flavour (str or list): Metadata flavour(s) to include. Defaults
            to ``tdda.serial``.
        **kw: Parameters that will be passed to ``df.to_csv``.

    Returns:
        SerialMetadata: Metadata object describing the DataFrame.
    """
    fields = [pandas_col_to_field_metadata(df[c]) for c in df]
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
            null_indicator=kw.get(
                'na_rep', delistify(Defaults.NULL_INDICATOR)
            ),
            header_row_count=header_row_count,
            date_format=kw.get(
                'date_format',
                DateFormat.ISO8601_UNSPECIFIED
                if any(
                    f.fieldtype
                    in (
                        FieldType.DATE,
                        FieldType.DATETIME,
                        FieldType.DATETIME_WITH_TIMEZONE,
                        FieldType.TIME,
                        FieldType.ISO8601,
                    )
                    for f in fields
                )
                else None,
            ),
        )
    else:
        md = SerialMetadata()

    if PANDAS.write_key in flavours:
        # literally the parameters passed in
        lib_params = {k: repr(v) for k, v in kw.items()}
        md.libs[PANDAS.write_key] = lib_params

    if PANDAS.read_key in flavours:
        lib_params = pandas_write_to_read_params(df, **kw)
        md.libs[PANDAS.read_key] = lib_params

    if outpath:
        md.write(outpath)

    return md


def pandas_col_to_field_metadata(
    field, fieldtype=None, fmt=None, date_fmt=None, backend=None
):
    """Return a ``FieldMetadata`` object for a pandas Series.

    Args:
        field (pd.Series): The column to describe.
        fieldtype (str): Optional ``FieldType`` override; inferred from
            dtype if not given.
        fmt (str): Optional format string for the field.
        date_fmt (str): Format for date/datetime fields if ``fmt`` is
            not set; a named format or strftime string.
        backend: Preferred pandas backend (unused, for API consistency).

    Returns:
        FieldMetadata: Metadata object for the column.
    """
    if fieldtype:
        fieldtype = fieldtype
    else:
        fieldtype = pandas_dtype_to_fieldtype(field.dtype, col=field)

    if not fmt and date_fmt:
        if fieldtype in (
            FieldType.DATE,
            FieldType.DATETIME,
            FieldType.DATETIME_WITH_TIMEZONE,
        ):
            fmt = date_fmt
    return FieldMetadata(field.name, fieldtype, format=fmt)


def item(v):
    return v.item() if hasattr(v, 'item') else v


def yn2bool(v):
    """Convert a Y/N string to True, False, or None."""
    return (
        None
        if pd.isnull(v)
        else True
        if v.lower().startswith('y')
        else False
        if v.lower().startswith('n')
        else None
    )


def to_pandas_date_format(v, for_write=False):
    """Convert a tdda.serial format string to a pandas ``date_format`` value.

    Named ISO8601 formats return ``'ISO8601'`` on read (pandas accepts
    any ISO variant) and the canonical strftime on write. Euro/US
    named formats return their canonical strftime for both read and
    write. Unspecified generic formats (``eu``, ``us``) raise
    ``NotImplementedError``. Raw strftime strings pass through
    unchanged.
    """
    if v is None:
        return None
    if v in ISO8601_NAMED_FORMATS and not for_write:
        return PANDAS_ISO8601
    strftime = serial_format_to_strftime(v)
    if (
        not for_write
        and STRFTIME_TO_NAMED_FORMAT.get(strftime) in ISO8601_NAMED_FORMATS
    ):
        return PANDAS_ISO8601
    return strftime


def pandas_date_format_to_serial(fmt):
    if fmt == PANDAS_ISO8601:
        return DateFormat.ISO8601_UNSPECIFIED
    else:
        return fmt


def csv_to_pandas(
    path=None,
    md_path=None,
    md_file_type=None,
    find_md=False,
    backend=None,
    upgrade_types=True,
    upgrade_possible_ints=False,
    return_md=False,
    table_number=None,
    use_table_name=False,
    preferred=None,
    verbosity=VERBOSITY,
    infer_datetime_formats=False,
    warner=None,
    config=None,
    **kw,
):
    """Load a CSV file into a Pandas DataFrame using metadata for type guidance.

    Args:
        path (str): Path to the data file (usually CSV) to be read.
            If None, md_path must be set and contain the path to the
            data. Can contain ':' to trigger metadata search.
        md_path (str): Optional path to the associated metadata file.
            If path is None, this must be set and contain the path to
            the data (CSV file). If path is not None, the path in the
            metadata file is ignored. If md_path is None, path must not
            be None. In this case, if find_md is set to True, this
            function will try to find an associated metadata file and
            use that if possible, and will raise an error if it cannot
            be found.
        md_file_type (str): Optional specification of the kind of
            metadata file. One of 'tdda.serial', 'csvw',
            'frictionless'.
        find_md (bool): If True, the library will try to find
            associated metadata based on filename conventions.
            Should not be set if md_path is provided. If associated
            metadata cannot be found, an error will be raised.
        upgrade_types (bool): If True (the default), upgrade some
            object-dtype columns to stricter types.
        upgrade_possible_ints (bool): If True (not the default),
            upgrade float columns with nulls but no fractional
            components to nullable Int types.
        return_md (bool): If True, returns a (DataFrame, metadata)
            tuple instead of just the DataFrame.
        table_number (int): If set, use the nth table (indexed from
            zero) from a multi-table metadata file.
        preferred (str): Override the metadata flavour used. By
            default csv_to_pandas uses the pandas.read_csv flavour if
            present. Can be set to 'tdda.serial' or 'csvw'.
        verbosity (int): Controls warning output for the metadata
            reader.
        **kw: Passed directly to pandas.read_csv, overriding any
            values derived from the metadata file.

    Returns:
        DataFrame, or (DataFrame, metadata) tuple if return_md is True.
    """
    md, path, md_path = get_metadata_for_reader(
        path=path,
        md_path=md_path,
        md_file_type=md_file_type,
        find_md=find_md,
        table_number=table_number,
        use_table_name=use_table_name,
        preferred=preferred or 'pandas.read_csv',
        verbosity=verbosity,
    )
    if md is not None and md.path is None and md_path is not None:
        md.path = md_path
    backend = get_backend(backend, config)
    if md:
        md_kw = serial_to_pandas_read_csv_args(
            md, backend=backend, warner=warner
        )
    if md and kw:
        md_kw.update(kw)
        kw = md_kw
    elif md:
        kw = md_kw
    else:
        kw.setdefault('encoding', 'utf-8')
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
            if is_string_col(df[k]):
                specified_type = specified_types.get(k)
                try:
                    if specified_type:
                        df[k] = df[k].astype(specified_type)
                    elif k in dates:
                        try:
                            df[k] = df[k].astype('datetime64[ns]')
                        except (ValueError, TypeError):
                            try:
                                df[k] = pd.to_datetime(df[k])
                            except Exception:
                                df[k] = pd.to_datetime(df[k], utc=True)
                except ValueError:  # probably time-zone aware date
                    pass

    if upgrade_possible_ints:
        for k in df:
            if not k in (specified_types or []):
                poss_upgrade_to_int(df, k)

    if infer_datetime_formats:
        df = infer_dates(df, specified_types)
    return DataFrameWithMetadata(df, md) if return_md else df


def serial_to_pandas_read_csv_python(
    md, backend=None, warner=None, config=None
):
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


def pandas_to_csv(
    df,
    path=None,
    md_inpath=None,
    md_outpath=None,
    auto_md_inpath=False,
    auto_md_outpath=False,
    flavour=None,
    preferred_in_flavour=None,
    in_table_number=None,
    find_safe_null=False,
    include_data_path_in_md=None,
    warner=None,
    **kw_overrides,
):
    """Write a Pandas DataFrame to a CSV file, optionally using metadata.

    Args:
        df (DataFrame): The DataFrame to write.
        path (str): Path to write the CSV data to.
        md_inpath (str): Optional path to a .serial (or CSVW) metadata
            file to use when writing the CSV.
        md_outpath (str or bool): Optional path to write a .serial
            metadata file describing the format used. If True, the
            .serial path is derived from the data path by swapping the
            extension.
        auto_md_inpath (bool): If True, find the input metadata path
            automatically from filename conventions.
        auto_md_outpath (bool): If True, choose the output metadata
            path automatically.
        flavour (str or list): Flavour(s) to include in the written
            .serial file. By default only 'tdda.serial' is included.
        preferred_in_flavour (str): If multiple formats are available
            in the .serial file, use this one. By default, uses the
            first available of: pandas.DataFrame.to_csv,
            pandas.read_csv, tdda.serial, or anything it can find.
        find_safe_null (bool): If True, choose a null representation
            that is safe for this data (not present in any string
            column).
        include_data_path_in_md: If None, the path is not set in
            tdda.serial metadata. If set to any truthy value, the
            path to the datafile is included. For csvw and
            frictionless, None causes a url/path to be written.
        **kw_overrides: Passed directly to DataFrame.to_csv,
            overriding any values derived from md_inpath. It is
            usually better not to mix md_inpath and overrides as it
            is easy to generate incompatibilities. Any na_rep
            specified here will be replaced if find_safe_null is set
            and the nominated null indicator is not safe (a warning
            is issued).

    Returns:
        Object with attributes:
            .md_out_path: path metadata was written to, or None.
            .out_path: path data was written to, or None.
            .md_inpath: path from which write metadata was read.
            .to_csv_kwargs: keyword args used to write the CSV.
    """
    Warn = nvl(warner, warn)
    md_in, path, md_inpath = get_metadata_for_writer(
        path=path,
        md_path=md_inpath,
        find_md=auto_md_inpath,
        preferred=preferred_in_flavour or 'pandas.write_csv',
    )

    if md_in:
        kw = serial_to_pandas_write_csv_args(md_in)
    else:
        kw = {}
    if not kw.get('index'):
        kw['index'] = False

    if find_safe_null:
        spec = kw_overrides.get('na_rep')
        null = find_safe_null_rep(df, preferred=kw_overrides.get('na_rep'))
        kw['na_rep'] = null
        if spec is not None and spec != null:
            Warn(
                f'Specified null rep "{spec}" was not safe. '
                f'Using "{null}".\n(Safe null rep was requested.)'
            )

    kw.update(kw_overrides)  # overrides passed in

    if path:  # if None, just write the metadata
        df.to_csv(path, **kw)  # write the csv

    if auto_md_outpath and not md_outpath:
        md_outpath = choose_md_path(path, flavour)
    if md_outpath:
        md_out = pandas_df_to_metadata(
            df, outpath=md_outpath, flavour=flavour, **kw
        )

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
            n_same = sum(int_col == field)
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
                    if str(datecol.dtype).startswith('datetime64'):
                        df[c] = datecol
                except Exception:
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
