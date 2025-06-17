import polars as pl

from tdda.serial.base import VERBOSITY
from tdda.utils import warn

class POLARSS:
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


FIELDTYPE_TO_PANDAS_DTYPE = {
    'bool': pl.Boolean,
    'int': pl.Int64,
    'string': pl.String,
    'number': pl.Float64,
    'float': pl.Float64,
    'datetime': pl.Datetime,
    'date': pl.Datetime,
}


def to_polars_read_csv_args(md):
    params = md.libs.get(POLARS.read_key)
    if params:
        o = params.get('schema_overrides')
        if o:
            for k, v in o.items():
                dtype = POLARS_DTYPE_MAP.get(v)
                if dtype:
                    o[k] = dtype
                else:
                    warn(f'Polars type "{dtype}" not known')
        return params

    kw = {}

    if md.delimiter:
        kw['separator'] = md.delimiter

    if md.quote_char:
        kw['quote_char'] = md.quote_char

    if md.escape_char:
        warn('Polars does not understand escape characters.\n'
             f'Ignoring escape value: {md.escape_char}')

    if md.null_indicators is not None:
        kw['null_values'] = listify(md.null_indicators)  # Can do per field

    if header_row_count == 0:
        kw['has_header'] = False


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


def csv_to_polars(path=None, mdpath=None, md_file_type=None, findmd=False,
                  upgrade_types=True, upgrade_possible_ints=False,
                  return_md=False, table_number=None, use_table_name=False,
                  preferred=None, verbosity=VERBOSITY,
                  **kw):
    """
    Load the data from a CSV file into a Pandas DataFrame use pandas.read_csv
    and extra metadata.

    Args:

       path     The path to the data file (usually CSV) to be read.
                If this is None, the mdpath must be set and contain
                the path to the data.

       mdpath   The optional path to the associated metadata file.

                If path is None, this must be set and contain the
                path to the data (CSV file).

                If path is not None, the path in the metadata file
                is ignored.

                If mdpath is None, path must not be None.
                In this case, if findmd is set to True, this function
                will try to find an associated metadata file and use
                that if possible, and will raise an error if it cannot
                be found.

       md_file_type   Optional specification of the kind of metadata file.
                      Should be one of
                          'tdda.serial'
                          'csvw'
                          'frictionless'

       findmd   If this is set to True, the library will try to find
                associated metadata based on filename conventions.
                This should not be set if mdpath is provided.
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

       verbosity   For metadata reader

       **kw     These keyword arguments are passed to pandas.read_csv,
                and can be used to override values from the
                metadata file.
    """
    md, path, mdpath = get_metadata_for_reader(
         path=path, mdpath=mdpath, md_file_type=md_file_type,
         findmd=findmd, table_number=table_number,
         use_table_name=use_table_name,
         preferred=preferred or 'polars.read_csv',
         verbosity=verbosity
     )
    if md:
        md_kw = to_polars_read_csv_args(md)
    if md and kw:
        md_kw.update(kw)
        kw = md_kw
    elif md:
        kw = md_kw
    df = pl.read_csv(path, **kw)
    return DataFrameWithMetadata(df, md) if return_md else df



