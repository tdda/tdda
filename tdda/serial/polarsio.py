import copy
import os

import polars as pl

from tdda.serial.metadata import (
    VERBOSITY,
    SerialMetadata,
    TDDASerialError,
    serial_format_to_strftime,
)
from tdda.serial.reader import get_metadata_for_reader, set_delimiter_from_path
from tdda.serial.utils import (
    PYTHON_TEMPLATES,
    fill_template,
    format_template_args,
    DataFrameWithMetadata,
)

from tdda.utils import listify, warn, nvl


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

    out = {}
    if md.delimiter:
        out['separator'] = md.delimiter

    if md.quote_char:
        out['quote_char'] = md.quote_char

    if md.header_row_count == 0:
        out['include_header'] = False

    null = md.single_null_indicator()
    if null is not None:
        out['null_value'] = null

    if md.date_format:
        out['date_format'] = serial_format_to_strftime(md.date_format)

    if md.datetime_format:
        out['datetime_format'] = serial_format_to_strftime(md.datetime_format)

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
        kw['null_values'] = listify(md.null_indicator)  # Can do per field

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
            trues = listify(fmd.true_values)
            falses = listify(fmd.false_values)
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
