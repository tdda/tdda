import polars as pl


def polars_col_to_tdda_type(col):
    """
    Returns the TDDA type of a Polars column.

    Basic TDDA types are one of 'bool', 'int', 'real', 'string' or 'date'.
    Returns 'null' for all-null columns, 'other' if unrecognized.
    """
    dtype = col.dtype
    if dtype == pl.Boolean:
        return 'bool'
    if dtype.is_integer():
        return 'int'
    if dtype.is_float():
        return 'real'
    if dtype in (pl.String, pl.Categorical):
        return 'string'
    if dtype == pl.Date or isinstance(dtype, pl.Datetime):
        return 'date'
    if dtype == pl.Null:
        return 'null'
    return 'other'
