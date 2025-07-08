import copy
import os

import polars as pl

from tdda.serial.metadata import VERBOSITY, SerialMetadata
from tdda.serial.reader import get_metadata_for_reader
from tdda.serial.utils import PYTHON_TEMPLATES, fill_template

from tdda.utils import listify, warn, nvl

class POLARS:
    read_key = 'polars.read_csv'
    write_key = 'polars.DataFrame.to_csv'


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


POLARS_DTYPE_MAP = {
    k: eval(f'pl.{k}')
    for k in POLARS_DTYPES
}


POLARS_DTYPE_MAP = {
    k: eval(f'pl.{k}')
    for k in POLARS_DTYPES
}


FIELDTYPE_TO_POLARS_DTYPE = {
    'bool': pl.Boolean,
    'int': pl.Int64,
    'string': pl.String,
    'number': pl.Float64,
    'float': pl.Float64,
    'datetime': pl.Datetime,
    'date': pl.Datetime,
}


def pl_dtype_to_str(t):
    return str(t).split('.')[-1] if t else str(t)


def serial_to_polars_read_csv_args(md, warner=None, serializable=False,
                                   map_other_bools_to_string=False,
                                   backend=None):
    """
    Convert metadata to dictionary of keyword arguments for Polars.

    backend: not used by Polars
    """
    Warn = nvl(warner, warn)
    f = pl_dtype_to_str if serializable else lambda x: x
    params = md.libs.get(POLARS.read_key)
    if params:
        o = params.get('schema_overrides')
        if o:
            for k, v in o.items():
                dtype = f(POLARS_DTYPE_MAP.get(v))
                if dtype:
                    o[k] = dtype
                else:
                    Warn(f'Polars type "{dtype}" not known.\n')
        return params

    kw = {}
    if md.delimiter:
        kw['separator'] = md.delimiter

    if md.quote_char:
        kw['quote_char'] = md.quote_char

    if md.escape_char:
        Warn('Polars does not understand escape characters.\n'
             f'Ignoring escape value: {md.escape_char}\n')

    if md.null_indicator is not None:
        kw['null_values'] = listify(md.null_indicator)  # Can do per field

    if md.header_row_count == 0:
        kw['has_header'] = False

    if md.encoding:
        kw['encoding'] = md.encoding

    if isinstance(md.fields, list):    # full schema
        schema = kw['schema'] = {
            field.name: f(FIELDTYPE_TO_POLARS_DTYPE.get(field.fieldtype, None))
            for field in md.fields
        }
        fields = {
            field.name: field
            for field in md.fields
        }

    elif isinstance(md.fields, dict):  # partial schema
        schema = kw['schema_overrides'] = {
            field.name: f(FIELDTYPE_TO_POLARS_DTYPE.get(field.fieldtype, None))
            for field in md.fields.values()
        }
        fields = md.fields
    else:
        fields = {}

    booleans = [
        f.format
        for f in md.fields
        if getattr(f, 'format', None) and f.fieldtype == 'bool'
    ]
    bool_str_fields = []
    if booleans:
        for b in booleans:
            parts = b.split('|')
            if len(parts) == 2:
                trues.add(parts[0])
                falses.add(parts[1])
            else:
                Warn(f'*** Warning: Boolean specification {b} not understood;'
                       ' ignoring.\n')
            non_pl_bools = ', '.join(
                [v for c in true_values if v.lower() != 'true']
                + [v for c in true_values if v.lower() != 'false']
            )
            bool_str_fields = [f.name for f in fields if f.fieldtype == 'bool']
            if non_pl_bools and bool_fields:
                if map_other_bools_to_string:
                    flist = ','.join(bool_str_fields)
                    m = f'Mapping to String: {flist}'
                else:
                    bool_str_fields = []
                    m = ('If they actually occur in the file, fields '
                         'will need to be set to string.\n'
                         '(Use map_other_bools_to_string=True.)')
                Warn('Polars will not understand '
                     f'the following boolean values:\n {non_pl_bools}.\n{m}\n')

    for field, fmd in fields.items():
        if fmd.fieldtype.startswith('date'):
            if fmd.format and not fmd.format.lower().startswith('iso'):
                schema[field] = f(pl.String)
                Warn(f'Field {field} date format {fmd.format} will not be '
                      'understood by Polars.\nSetting to pl.String.')
        if fmd.fieldtype.lower().startswith('bool'):
            bads = ', '.join(v for v in (listify(fmd.true_values)
                                + listify(fmd.false_values))
                          if v.lower not in ['true', 'false'])
                   # What if swapped?
            if any(bads):
                start = (f'Field {field} booleans {bads} will not be '
                          'understood by Polars.')
                param = 'map_other_bools_to_string=True'
                if map_other_bools_to_string:
                    Warn(f'{start}\nSetting to pl.String ({param}).\n')
                    schema[field] = f(pl.String)
                else:
                    Warn(f'{start}\nIf they are present, '
                          f'you may need to set them to pl.String.\n'
                          f'(Use {param}.)\n')

    if any(f.name != f.csvname for f in md.fields):
        kw['new_columns'] = [f.name for f in md.fields]


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

    return kw


def csv_to_polars(path=None, md_path=None, md_file_type=None, find_md=False,
                  upgrade_types=True, upgrade_possible_ints=False,
                  return_md=False, table_number=None, use_table_name=False,
                  preferred=None, map_other_bools_to_string=False,
                  verbosity=VERBOSITY, warner=None,
                  infer_datetime_formats=False, **kw):
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
                In this case, if find_md is set to True, this function
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
                If assocaited metadata cannot be found, an error
                will be raised when this is set.

       upgrade_types   If True (the default), this will upgrade
                       some columns read_csv will create as object
                       (dtype object) to stricter types.

       upgrade_possible_ints   If True (not the default), any float
                               columns with nulls but with no fractional
                               components will be upgraded to Ints.

       return_md   If true, returns DataFrame and metadata (as tuple)

       table_number  If set, use the specified table number (indexed
                     from zero) in the metadata

       preferred  Normally, if tdda.serial metadata is used,
                  csv_to_polars will use the polars.read_csv metadata flavour
                  if present. This can be set to 'tdda.serial'
                  or 'csvw' to override that.

       map_other_bools_to_string   If True, when metadata specifies
                                   non-true/false values as bools
                                   the boolean fields are read as strings.
                                   Default: False

       verbosity   For metadata reader

       **kw     These keyword arguments are passed to pandas.read_csv,
                and can be used to override values from the
                metadata file.
    """
    md, path, md_path = get_metadata_for_reader(
         path=path, md_path=md_path, md_file_type=md_file_type,
         find_md=find_md, table_number=table_number,
         use_table_name=use_table_name,
         preferred=preferred or 'polars.read_csv',
         verbosity=verbosity,
     )
    if md:
        md_kw = serial_to_polars_read_csv_args(
            md,
            warner=warner,
            map_other_bools_to_string=map_other_bools_to_string,
        )
    if md and kw:
        md_kw.update(kw)
        kw = md_kw
    elif md:
        kw = md_kw

    df = pl.read_csv(path, **kw)
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
    """
    Reads a pandas data frame from parquet or csv, as the extension suggests.
    Prefers nullable types.
    """
    _, ext = os.path.splitext(path)
    if ext == '.csv':
        return csv_to_polars(path, **kw)
    elif ext == '.parquet':
        # return pd.read_parquet(path, use_nullable_dtype=True)
        return pl.read_parquet(path)
    else:
        raise TDDASerialError(f'Unexpected extension {ext} in {path}.')


def polars_write_df(df, path):
    """
    Writes a pandas data frame as parquet or csv, as the extension suggests.
    Does not write the index.
    """
    _, ext = os.path.splitext(path)
    if ext == '.csv':
        df.write_csv(path)
    elif ext == '.parquet':
        df.write_parquet(path)
    else:
        raise TDDASerialError(f'Unexpected extension {ext} in {path}.')


def serial_to_polars_read_csv_python(md, backend=None, warner=None):
    """
    backend is not used for polars.
    """
    kw = serial_to_polars_read_csv_args(md, backend=backend, warner=warner)
    return fill_template(PYTHON_TEMPLATES.POLARS_READ, kw,
                         flavour='polars',
                         dtypes=FIELDTYPE_TO_POLARS_DTYPE)
