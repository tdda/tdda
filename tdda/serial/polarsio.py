import polars as pl

from tdda.utils import warn

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
    params = md.libs.get('polars.read_csv')
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

