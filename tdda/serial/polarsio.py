import copy
import os
from collections import Counter, namedtuple

import polars as pl

from tdda.serial.metadata import (
    DateFormat,
    Defaults,
    FieldMetadata,
    FieldType,
    VERBOSITY,
    SerialMetadata,
    TDDASerialError,
    serial_format_to_strftime,
)

POLARS_QUOTE_STYLE_TO_SERIAL = {
    'necessary': 'QUOTE_MINIMAL',
    'always': 'QUOTE_ALL',
    'non_numeric': 'QUOTE_NONNUMERIC',
    'never': 'QUOTE_NONE',
}
from tdda.serial.reader import (
    get_metadata_for_reader,
    get_metadata_for_writer,
    set_delimiter_from_path,
)
from tdda.serial.utils import choose_md_path
from tdda.serial.utils import (
    PYTHON_TEMPLATES,
    fill_template,
    format_template_args,
    DataFrameWithMetadata,
)

from tdda.serial.dateutils import infer_date_format_from_strings
from tdda.serial.constants import TDDASERIAL
from tdda.utils import delistify, listify, warn, nvl


class POLARS:
    read_key = 'polars.read_csv'
    write_key = 'polars.DataFrame.write_csv'


POLARS_DTYPES = [
    'Decimal',
    'Float32',
    'Float64',
    'Int8',
    'Int16',
    'Int32',
    'Int64',
    'Int128',
    'UInt8',
    'UInt16',
    'UInt32',
    'UInt64',
    'Date',
    'Datetime',
    'Duration',
    'Time',
    'String',
    'Categorical',
    'Enum',
    'Utf8',
    'Binary',
    'Boolean',
    # Null
    'Object',
    'Unknown',
    'Array',
    'List',
    'Field',
    'Struct',
]


POLARS_DTYPE_MAP = {k: eval(f'pl.{k}') for k in POLARS_DTYPES}

POLARS_REV_DTYPES = [(v, k) for k, v in POLARS_DTYPE_MAP.items()]


FIELDTYPE_TO_POLARS_DTYPE = {
    'bool': pl.Boolean,
    'int': pl.Int64,
    'string': pl.String,
    'number': pl.Float64,
    'float': pl.Float64,
    'datetime': pl.Datetime,
    'date': pl.Datetime,
    'time': pl.Time,
    'datatime_tz': pl.Datetime,
    'iso8601': pl.Datetime,
}

GEN_PY = 'Generate Python with .py target and --to pl.r to see required post-processing.'


def pl_dtype_to_str(t):
    return str(t).split('.')[-1] if t else str(t)


def str_to_pl_dtype(s):
    for t, st in POLARS_REV_DTYPES:
        if s == st:
            return t
    return s


def polars_dtype_to_fieldtype(dtype):
    """Convert a polars dtype to a FieldType constant.

    Args:
        dtype: A polars dtype (e.g. pl.Int64, pl.Date, pl.Datetime).

    Returns:
        A FieldType value if recognised, or None.
    """
    base = dtype.base_type() if hasattr(dtype, 'base_type') else dtype
    if base in (pl.Int8, pl.Int16, pl.Int32, pl.Int64,
                pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64):
        return FieldType.INT
    elif base in (pl.Float32, pl.Float64):
        return FieldType.FLOAT
    elif base is pl.Boolean:
        return FieldType.BOOL
    elif base in (pl.String, pl.Utf8, pl.Categorical, pl.Enum):
        return FieldType.STRING
    elif base is pl.Date:
        return FieldType.DATE
    elif base is pl.Datetime:
        if hasattr(dtype, 'time_zone') and dtype.time_zone:
            return FieldType.DATETIME_WITH_TIMEZONE
        return FieldType.DATETIME
    elif base is pl.Time:
        return FieldType.TIME
    else:
        return None


def polars_col_to_field_metadata(
    field, fieldtype=None, fmt=None, date_fmt=None
):
    """Return a FieldMetadata object for a polars Series.

    Args:
        field (pl.Series): The column to describe.
        fieldtype (str): Optional FieldType override; inferred from
            dtype if not given.
        fmt (str): Optional format string for the field.
        date_fmt (str): Format for date/datetime fields if fmt is
            not set; a named format or strftime string.

    Returns:
        FieldMetadata describing the column.
    """
    if not fieldtype:
        fieldtype = polars_dtype_to_fieldtype(field.dtype)
    if not fmt and date_fmt:
        if fieldtype in (
            FieldType.DATE,
            FieldType.DATETIME,
            FieldType.DATETIME_WITH_TIMEZONE,
        ):
            fmt = date_fmt
    return FieldMetadata(field.name, fieldtype, format=fmt)



def polars_write_to_read_params(df, warner=None, **kw):
    """Convert polars write_csv kwargs to read_csv kwargs for the same file.

    Args:
        df (pl.DataFrame): The DataFrame that was written.
        warner: Optional callable for issuing warnings.
        **kw: The kwargs that were passed to write_csv.

    Returns:
        Dict of kwargs suitable for polars.read_csv to read back the
        file that was written.
    """
    d = {}
    sep = kw.get('separator', Defaults.DELIMITER)
    if sep != Defaults.DELIMITER:
        d['separator'] = sep
    qc = kw.get('quote_char', Defaults.QUOTE_CHAR)
    if qc != Defaults.QUOTE_CHAR:
        d['quote_char'] = qc
    null = kw.get('null_value')
    if null is not None:
        d['null_values'] = null
    if kw.get('include_header') is False:
        d['has_header'] = False
    schema = {}
    for col in df.columns:
        dtype = df[col].dtype
        ft = polars_dtype_to_fieldtype(dtype)
        if ft in (FieldType.DATE, FieldType.DATETIME,
                  FieldType.DATETIME_WITH_TIMEZONE):
            schema[col] = dtype
    if schema:
        d['schema_overrides'] = schema
    return d


def polars_df_to_metadata(df, outpath=None, flavour=None, **kw):
    """Create SerialMetadata for a DataFrame being written with polars.

    Args:
        df (pl.DataFrame): Source of field names and type information.
        outpath (str): Path to write metadata to; if None, not written
            but the SerialMetadata object is still returned.
        flavour (str or list): Metadata flavour(s) to include. Defaults
            to ``tdda.serial``.
        **kw: Parameters that were passed to write_csv.

    Returns:
        SerialMetadata describing the DataFrame.
    """
    date_fmt = kw.get('date_format')
    datetime_fmt = kw.get('datetime_format')
    DATE_TYPES = (
        FieldType.DATE, FieldType.DATETIME,
        FieldType.DATETIME_WITH_TIMEZONE, FieldType.TIME,
        FieldType.ISO8601,
    )
    fields = []
    for c in df.columns:
        col = df[c]
        ft = polars_dtype_to_fieldtype(col.dtype)
        if ft == FieldType.DATE:
            fmt = date_fmt
        elif ft in (FieldType.DATETIME, FieldType.DATETIME_WITH_TIMEZONE):
            fmt = datetime_fmt
        else:
            fmt = None
        fields.append(FieldMetadata(c, ft, format=fmt))

    flavours = listify(flavour)
    if not flavours:
        flavours = [TDDASERIAL.key]

    if TDDASERIAL.key in flavours:
        has_dates = any(f.fieldtype in DATE_TYPES for f in fields)
        polars_quote_style = kw.get('quote_style', 'necessary')
        md = SerialMetadata(
            fields,
            delimiter=kw.get('separator', Defaults.DELIMITER),
            quote_char=kw.get('quote_char', Defaults.QUOTE_CHAR),
            quoting=POLARS_QUOTE_STYLE_TO_SERIAL.get(
                polars_quote_style, 'QUOTE_MINIMAL'
            ),
            null_indicator=kw.get('null_value',
                                  delistify(Defaults.NULL_INDICATOR)),
            header_row_count=0 if kw.get('include_header') is False else 1,
            date_format=date_fmt or (
                DateFormat.ISO8601_UNSPECIFIED if has_dates else None
            ),
            datetime_format=datetime_fmt,
        )
    else:
        md = SerialMetadata()

    if POLARS.write_key in flavours:
        md.libs[POLARS.write_key] = {k: repr(v) for k, v in kw.items()}

    if POLARS.read_key in flavours:
        md.libs[POLARS.read_key] = polars_write_to_read_params(df, **kw)

    if outpath:
        md.write(outpath)

    return md


WriteInfo = namedtuple('WriteInfo', 'path md_outpath md_inpath kw')


def polars_to_csv(
    df,
    path=None,
    md_inpath=None,
    md_outpath=None,
    auto_md_inpath=False,
    auto_md_outpath=False,
    flavour=None,
    preferred_in_flavour=None,
    include_data_path_in_md=None,
    warner=None,
    **kw_overrides,
):
    """Write a Polars DataFrame to a CSV file, optionally using metadata.

    Args:
        df (pl.DataFrame): The DataFrame to write.
        path (str): Path to write the CSV data to.
        md_inpath (str): Optional path to a .serial (or CSVW) metadata
            file to use when writing the CSV.
        md_outpath (str or bool): Optional path to write a .serial
            metadata file describing the format used. If True, the
            .serial path is derived from the data path.
        auto_md_inpath (bool): If True, find the input metadata path
            automatically from filename conventions.
        auto_md_outpath (bool): If True, choose the output metadata
            path automatically.
        flavour (str or list): Flavour(s) to include in the written
            .serial file. By default only 'tdda.serial' is included.
        preferred_in_flavour (str): If multiple formats are available
            in the .serial file, prefer this one.
        include_data_path_in_md: If set, include the data path in the
            output metadata.
        warner: Optional callable for issuing warnings.
        **kw_overrides: Passed directly to write_csv, overriding any
            values derived from md_inpath.

    Returns:
        WriteInfo namedtuple with attributes path, md_outpath,
        md_inpath, and kw (the write_csv kwargs used).
    """
    Warn = nvl(warner, warn)
    md_in, path, md_inpath = get_metadata_for_writer(
        path=path,
        md_path=md_inpath,
        find_md=auto_md_inpath,
        preferred=preferred_in_flavour or POLARS.write_key,
    )

    if md_in:
        kw = serial_to_polars_write_csv_args(md_in, warner=Warn)
    else:
        kw = {}
    kw.update(kw_overrides)

    if path:
        df.write_csv(path, **kw)

    if auto_md_outpath and not md_outpath:
        md_outpath = choose_md_path(path, flavour)
    if md_outpath:
        polars_df_to_metadata(
            df, outpath=md_outpath, flavour=flavour, **kw
        )

    return WriteInfo(path, md_outpath, md_inpath, kw)


def serial_to_polars_read_csv_args(
    md,
    warner=None,
    serializable=False,
    map_other_bools_to_string=False,
    backend=None,
):
    """Convert SerialMetadata to keyword arguments for polars.read_csv.

    Args:
        md (SerialMetadata): Metadata describing the CSV file format.
        warner: Optional callable for issuing warnings.
        serializable (bool): If True, return only JSON-serializable
            values (e.g. dtype repr strings instead of Polars types).
        map_other_bools_to_string (bool): If True, boolean fields
            whose metadata specifies non-true/false values are mapped
            to string type.
        backend: Unused; accepted for API consistency with the pandas
            equivalent.

    Returns:
        Dict of keyword arguments suitable for passing to
        polars.read_csv.
    """
    kw, _, _r = serial_to_polars_read_csv_args_and_postproc(
        md,
        warner=warner,
        serializable=serializable,
        map_other_bools_to_string=map_other_bools_to_string,
    )
    return kw


POLARS_QUOTE_STYLE = {
    'QUOTE_ALL': 'always',
    'QUOTE_MINIMAL': 'necessary',
    'QUOTE_NONNUMERIC': 'non_numeric',
    'QUOTE_NONE': 'never',
    'QUOTE_NOTNULL': 'always',
    'QUOTE_STRINGS': 'non_numeric',
    'QUOTE_STRINGS_ONLY': 'non_numeric',
}


def serial_to_polars_write_csv_args(md, backend=None, warner=None, **kw):
    if POLARS.write_key in md.libs:
        return md.libs[POLARS.write_key]

    Warn = nvl(warner, warn)
    out = {}
    if md.delimiter:
        out['separator'] = md.delimiter

    if md.quote_char:
        out['quote_char'] = md.quote_char

    if md.header_row_count == 0:
        out['include_header'] = False

    null = md.single_null_indicator(warner=Warn)
    if null is not None:
        out['null_value'] = null

    date_fields = [f for f in md.fields if f.fieldtype == 'date']
    datetime_fields = [f for f in md.fields if f.fieldtype == 'datetime']
    global_fmt = md.date_format

    if date_fields:
        fmts = Counter(
            f.format or global_fmt or DateFormat.ISO8601_DATE
            for f in date_fields
        )
        if len(fmts) == 1:
            out['date_format'] = serial_format_to_strftime(list(fmts)[0])
        else:
            Warn('Multiple date formats for date fields; using ISO 8601.')
            out['date_format'] = '%Y-%m-%d'

    if datetime_fields:
        fmts = Counter(
            f.format or md.datetime_format or global_fmt
            or DateFormat.ISO8601_DATETIME
            for f in datetime_fields
        )
        if len(fmts) == 1:
            out['datetime_format'] = serial_format_to_strftime(list(fmts)[0])
        else:
            Warn('Multiple datetime formats; using ISO 8601.')
            out['datetime_format'] = '%Y-%m-%dT%H:%M:%S'

    if md.quoting:
        style = POLARS_QUOTE_STYLE.get(md.quoting)
        if style:
            out['quote_style'] = style

    return out


def serial_to_polars_read_csv_args_and_postproc(
    md,
    warner=None,
    serializable=False,
    map_other_bools_to_string=False,
    backend=None,
    no_postproc_warnings=False,
):
    """Convert metadata to ``polars.read_csv`` kwargs plus post-processing info.

    Also returns post-processing instructions (type casts to apply after
    reading) and a column rename map. ``backend`` is unused; accepted
    for API consistency with the pandas equivalent.
    """
    Warn = nvl(warner, warn)
    f = pl_dtype_to_str if serializable else str_to_pl_dtype
    params = md.libs.get(POLARS.read_key)
    if params:
        for s in ('schema', 'schema_overrides'):
            o = params.get(s)
            if o:
                out = o.copy()
                for k, v in o.items():
                    d = POLARS_DTYPE_MAP.get(v, v)
                    if d:
                        out[k] = f(d)
                    else:
                        Warn(f'Polars type "{v}" not known.\n')
                params[s] = out
        return params, {}, {}

    kw = {}
    if md.delimiter:
        kw['separator'] = md.delimiter

    if md.quote_char:
        kw['quote_char'] = md.quote_char

    if md.escape_char:
        Warn(
            'Polars does not understand escape characters.\n'
            f'Ignoring escape value: {md.escape_char}\n'
        )

    if md.null_indicator is not None:
        # With QUOTE_MINIMAL or QUOTE_NONNUMERIC, polars distinguishes
        # bare empty cells (null) from quoted "" (empty string) by default,
        # so passing null_values would incorrectly convert "" to null too.
        polars_handles_nulls = (
            md.quoting in ('QUOTE_MINIMAL', 'QUOTE_NONNUMERIC')
        )
        if not polars_handles_nulls or md.null_indicator not in ('', ['']):
            kw['null_values'] = listify(md.null_indicator)

    if md.header_row_count == 0:
        kw['has_header'] = False

    if md.encoding:
        kw['encoding'] = md.encoding

    has_unknowns = False
    use_rename_postproc = False
    rename_map = {}

    if isinstance(md.fields, list):  # full schema
        raw_dtypes = {
            field.csvname: FIELDTYPE_TO_POLARS_DTYPE.get(field.fieldtype)
            for field in md.fields
        }
        has_unknowns = any(v is None for v in raw_dtypes.values())
        if has_unknowns:
            known = {k: f(v) for k, v in raw_dtypes.items() if v is not None}
            schema = known
            if known:
                kw['schema_overrides'] = schema
            use_rename_postproc = True
            rename_map = {
                fld.csvname: fld.name
                for fld in md.fields
                if fld.csvname != fld.name
            }
        else:
            schema = {k: f(v) for k, v in raw_dtypes.items()}
            if schema:
                kw['schema'] = schema
        fields = {field.name: field for field in md.fields}

    elif isinstance(md.fields, dict):  # partial schema
        schema = kw['schema_overrides'] = {
            field.csvname: f(
                FIELDTYPE_TO_POLARS_DTYPE.get(field.fieldtype, None)
            )
            for field in md.fields.values()
        }
        fields = md.fields
    else:
        fields = {}

    postproc = {}
    for field, fmd in fields.items():
        if fmd.fieldtype and fmd.fieldtype.startswith('date'):
            attr = (
                'datetime_format'
                if fmd.fieldtype.startswith('datetime')
                else 'date_format'
            )
            fmt = nvl(fmd.format, getattr(md, attr, None))
            strfmt = serial_format_to_strftime(fmt) if fmt else None
            if (
                fmt
                and not fmt.lower().startswith('iso')
                and not strfmt.startswith('%Y-%m-%d')
            ):
                # TODO: Second condition might be too loose
                schema[fmd.csvname] = f(pl.String)
                op = 'to_date' if fmd.fieldtype == 'date' else 'to_datetime'
                postproc[field] = {'op': op, 'format': strfmt}
                if not no_postproc_warnings:
                    Warn(
                        f'Field {field} date format {fmt} will not be '
                        f'understood by Polars read_csv.\n{GEN_PY}'
                    )
            # Possible fallback for no date format set.
            # But prevents unspecified iso formats from working.
            # So probably not good.
            # elif not fmt:
            # schema[field] = f(pl.String)
        if fmd.fieldtype and fmd.fieldtype.lower().startswith('bool'):
            trues = listify(fmd.true_values or md.true_values)
            falses = listify(fmd.false_values or md.false_values)
            if not trues and not falses and fmd.format and '|' in fmd.format:
                parts = fmd.format.split('|')
                if len(parts) == 2:
                    trues, falses = [parts[0]], [parts[1]]
                else:
                    Warn(
                        f'Boolean specification {fmd.format!r} for field'
                        f' {field} not understood; ignoring.\n'
                    )
            bads = ', '.join(
                v
                for v in (trues + falses)
                if v.lower() not in ('true', 'false')
            )
            if bads:
                schema[fmd.csvname] = f(pl.String)
                if map_other_bools_to_string:
                    if not no_postproc_warnings:
                        Warn(
                            f'Field {field} booleans {bads} will not be '
                            f'understood by Polars read_csv.\n'
                            f'Mapping to pl.String.'
                        )
                else:
                    postproc[field] = {
                        'op': 'bool_map',
                        'trues': trues,
                        'falses': falses,
                    }
                    if not no_postproc_warnings:
                        Warn(
                            f'Field {field} booleans {bads} will not be '
                            f'understood by Polars read_csv.\n{GEN_PY}'
                        )

    if not use_rename_postproc:
        if any(fld.name != fld.csvname for fld in md.fields):
            kw['new_columns'] = [fld.name for fld in md.fields]

    # 'missing_utf8_is_empty_string'
    # infer_schema
    # infer_schema_length
    # use_pyarrow
    # skip_rows, skip_lines
    # skip_rows_after_header
    # row_index_name
    # row_index_offset
    # eol_char,
    # raise_if_empty
    # decimal_comma
    # comment prefix

    # columns
    # new_columns
    # schema

    # try_parse_dates
    # sample_size
    # batch_size
    # rechunk
    # truncate_ragged_lines
    # glob

    return kw, postproc, rename_map


def polars_infer_dates(df, specified_types=None):
    """Try to parse string columns as dates, skipping explicitly typed ones."""
    exprs = []
    for name in df.columns:
        if df[name].dtype != pl.String:
            continue
        spec = (specified_types or {}).get(name)
        if spec in (pl.String, pl.Utf8):
            continue
        strings = df[name].drop_nulls().head(100).to_list()
        fmt = infer_date_format_from_strings(strings)
        if fmt is None:
            continue
        try:
            if '%H' in fmt:
                exprs.append(
                    pl.col(name).str.to_datetime(format=fmt, strict=False)
                )
            else:
                exprs.append(
                    pl.col(name).str.to_date(format=fmt, strict=False)
                )
        except Exception:
            pass
    if exprs:
        df = df.with_columns(exprs)
    return df


def csv_to_polars(
    path=None,
    md_path=None,
    md_file_type=None,
    find_md=False,
    upgrade_types=True,
    upgrade_possible_ints=False,
    return_md=False,
    table_number=None,
    use_table_name=False,
    preferred=None,
    map_other_bools_to_string=False,
    include_data_path_in_md=None,
    verbosity=VERBOSITY,
    warner=None,
    infer_datetime_formats=False,
    **kw,
):
    """Load a CSV file into a Polars DataFrame using metadata for type guidance.

    Args:
        path (str): Path to the data file (usually CSV) to be read.
            If None, md_path must be set and contain the path to the
            data.
        md_path (str): Optional path to the associated metadata file.
            If path is None, this must be set and contain the path to
            the data (CSV file). If path is not None, the path in the
            metadata file is ignored. If md_path is None, path must
            not be None. In this case, if find_md is set to True, this
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
            default csv_to_polars uses the polars.read_csv flavour if
            present. Can be set to 'tdda.serial' or 'csvw'.
        map_other_bools_to_string (bool): If True, boolean fields
            whose metadata specifies non-true/false values are read
            as strings. Default: False.
        include_data_path_in_md: If None, the path is not set in
            tdda.serial metadata. If set to any truthy value, the
            path to the datafile is included. For csvw and
            frictionless, None causes a url/path to be written.
        verbosity (int): Controls warning output for the metadata
            reader.
        **kw: Passed directly to polars.read_csv, overriding any
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
        preferred=preferred or 'polars.read_csv',
        verbosity=verbosity,
    )
    if md is not None and md.path is None and md_path is not None:
        md.path = md_path

    Warn = warner or (warn if verbosity else lambda *a, **kw: None)
    postproc = {}
    rename_map = {}
    if md:
        md_kw, postproc, rename_map = (
            serial_to_polars_read_csv_args_and_postproc(
                md,
                warner=Warn,
                map_other_bools_to_string=map_other_bools_to_string,
                no_postproc_warnings=True,
            )
        )
    if md and kw:
        md_kw.update(kw)
        kw = md_kw
    elif md:
        kw = md_kw

    kw = set_delimiter_from_path(kw, path, 'separator')
    if infer_datetime_formats:
        kw.setdefault('try_parse_dates', True)
    df = pl.read_csv(path, **kw)
    if rename_map:
        rename_map = {k: v for k, v in rename_map.items() if k in df.columns}
    if rename_map:
        df = df.rename(rename_map)
    for name, info in postproc.items():
        try:
            if info['op'] == 'to_date':
                expr = pl.col(name).str.to_date(format=info['format'])
            elif info['op'] == 'bool_map':
                mapping = {v: 1 for v in info['trues']}
                mapping.update({v: 0 for v in info['falses']})
                expr = pl.col(name).replace_strict(mapping).cast(pl.Boolean)
            else:
                expr = pl.col(name).str.to_datetime(format=info['format'])
            df = df.with_columns(expr)
        except Exception:
            pass  # format was wrong; field stays as string
    if infer_datetime_formats:
        df = polars_infer_dates(df, specified_types=kw.get('schema'))
    return DataFrameWithMetadata(df, md) if return_md else df


def as_polars_serial_lib_args(kw):
    out = copy.deepcopy(kw)
    dtypes = kw.get('schema')
    if dtypes:
        out['schema'] = {k: repr(v) for k, v in dtypes.items()}
    dtypes = kw.get('schema_overrides')
    if dtypes:
        out['schema_overrides'] = {k: repr(v) for k, v in dtypes.items()}
    return out


def serial_to_polars_write_csv_python(
    md, backend=None, warner=None, **kw
):
    Warn = nvl(warner, warn)
    bool_fields = [
        f for f in md.fields
        if f.fieldtype == 'bool'
        and (f.format or f.true_values or f.false_values)
    ]
    if bool_fields or md.true_values or md.false_values:
        Warn(
            'Boolean formats cannot be expressed in'
            ' polars.DataFrame.write_csv;'
            ' booleans will be written as true/false.'
        )
    if md.encoding and md.encoding.lower().replace('-', '') not in (
        'utf8', 'utf8bom'
    ):
        Warn(
            f'polars.DataFrame.write_csv does not support'
            f' encoding {md.encoding!r}; output will be UTF-8.'
        )
    kw = serial_to_polars_write_csv_args(md, warner=Warn)
    kw = {k: v for k, v in kw.items() if v is not None}

    time_tokens = ('%H', '%M', '%S', '%f', '%3f', '%6f', '%9f')
    date_fmt = kw.get('date_format', '')
    if date_fmt and any(t in date_fmt for t in time_tokens):
        date_cols = [f.name for f in md.fields if f.fieldtype == 'date']
        if 'datetime_format' not in kw:
            kw['datetime_format'] = date_fmt
        del kw['date_format']
        cast_lines = ''.join(
            f'        pl.col({c!r}).cast(pl.Datetime),\n'
            for c in date_cols
        )
        args = format_template_args(kw)
        return (
            PYTHON_TEMPLATES.POLARS_WRITE_WITH_CAST % (cast_lines, args)
        ).lstrip()

    return fill_template(PYTHON_TEMPLATES.POLARS_WRITE, kw)


def polars_read_df(path, nullable=False, **kw):
    """Read a Polars DataFrame from a CSV or Parquet file by extension."""
    _, ext = os.path.splitext(path)
    if ext == '.csv':
        return csv_to_polars(path, **kw)
    elif ext == '.parquet':
        # return pd.read_parquet(path, use_nullable_dtype=True)
        return pl.read_parquet(path)
    else:
        raise TDDASerialError(f'Unexpected extension {ext} in {path}.')


def polars_write_df(df, path):
    """Write a Polars DataFrame to CSV or Parquet, determined by extension."""
    _, ext = os.path.splitext(path)
    if ext == '.csv':
        df.write_csv(path)
    elif ext == '.parquet':
        df.write_parquet(path)
    else:
        raise TDDASerialError(f'Unexpected extension {ext} in {path}.')


def serial_to_polars_read_csv_python(md, backend=None, warner=None, **kw):
    """Return ``polars.read_csv`` kwargs for use in plain Python CSV reading."""
    csv_kw, postproc, rename_map = serial_to_polars_read_csv_args_and_postproc(
        md, warner=warner, no_postproc_warnings=True
    )
    if kw:
        csv_kw.update(kw)
    args = format_template_args(
        csv_kw, flavour='polars', dtypes=FIELDTYPE_TO_POLARS_DTYPE
    )
    if not postproc and not rename_map:
        return (PYTHON_TEMPLATES.POLARS_READ % args).lstrip()
    postproc_lines = []
    if rename_map:
        entries = ['    rename_map = {']
        for k, v in rename_map.items():
            entries.append(f'        {k!r}: {v!r},')
        entries.extend(
            [
                '    }',
                '    rename_map = '
                '{k: v for k, v in rename_map.items() if k in df.columns}',
                '    if rename_map:',
                '        df = df.rename(rename_map)',
            ]
        )
        postproc_lines.extend(entries)
    if postproc:
        exprs = '\n'.join(
            (
                f'        pl.col({name!r})'
                f'.replace_strict({{{", ".join(f"{v!r}: 1" for v in info["trues"])}'
                f', {", ".join(f"{v!r}: 0" for v in info["falses"])}}})'
                f'.cast(pl.Boolean),'
            )
            if info['op'] == 'bool_map'
            else f'        pl.col({name!r}).str.{info["op"]}'
            f'(format={info["format"]!r}),'
            for name, info in postproc.items()
        )
        postproc_lines.append(f'    df = df.with_columns([\n{exprs}\n    ])')
    postproc_block = '\n'.join(postproc_lines)
    return (
        PYTHON_TEMPLATES.POLARS_READ_POSTPROC % (args, postproc_block)
    ).lstrip()
