import inspect

import numpy as np
import pandas as pd
import polars as pl

from tdda.pdutils import pandas_types_match
from tdda.plutils import polars_types_match
from tdda.state import get_config
from tdda.utils import TDDAError, nvl, error, debug

from tdda.serial import csv_to_pandas, csv_to_polars


def col_names(df):
    if is_pandas_df(df):
        return list(df)
    elif is_polars_df(df):
        return df.columns
    else:
        error('Not a known kind of DataFrame.')


def is_pandas_df(df):
    if isinstance(df, pd.DataFrame):
        return True
    elif isinstance(df, pl.DataFrame):
        return False
    raise ValueError(f'{df} is not a Python or Polars DataFrame')


def is_pandas_series(df):
    if isinstance(df, pd.Series):
        return True
    elif isinstance(df, pl.Series):
        return False
    raise ValueError(f'{df} is not a Python or Polars Series')


def is_pandas_obj(o):
    if isinstance(o, pd.DataFrame) or isinstance(o, pd.Series):
        return True
    elif isinstance(o, pl.DataFrame) or isinstance(o, pl.Series):
        return False
    raise ValueError(f'{o} is not a Python or Polars DataFrame or Series')


def is_polars_df(df):
    return not (is_pandas_df(df))


def col_types_match(L, R, level=None):
    f = pandas_types_match if is_pandas_series(L) else polars_types_match
    return f(L.dtype, R.dtype, level)


def lib(o):
    """
    Returns pd or pl according to whether o is a pandas or polars object
    """
    if isinstance(o, pd.DataFrame) or isinstance(o, pd.Series):
        return pd
    elif isinstance(o, pl.DataFrame) or isinstance(o, pl.Series):
        return pl
    raise ValueError(f'{o} is not a Python or Polars DataFrame or Series')


def df_type(df):
    if isinstance(df, pd.DataFrame):
        return 'pandas'
    if isinstance(df, pl.DataFrame):
        return 'polars'
    raise TDDAError('Not a known kind of data frame.')


def bool_type(o):
    return pd.BooleanDtype() if is_pandas_obj(o) else pl.Boolean


def int_type(o):
    return int if is_pandas_obj(o) else pl.Int64


def cast_col_to_int(c):
    return c.astype(int) if is_pandas_series(c) else c.cast(pl.Int64)


def df_rename_cols(df, mapping):
    if is_pandas_df(df):
        return df.rename(mapping, axis=1)
    else:
        return df.rename(mapping)


def df_definite(df, engine):
    """
    Force data frame df to use the nominated data-frame engine.
    """
    dft = df_type(df)
    if dft == engine:
        return df
    elif engine == 'pandas' and dft == 'polars':
        return df.to_pandas()
    elif engine == 'polars' and dft == 'pandas':
        return pl.from_pandas(df)
    else:
        error(f'Cannot convert {dft} data frame to {engine}.')


def specialize(df, fn, *args, **kwargs):
    f = eval(f'{df_type(df)}_{fn}')
    return f(*args, **kwargs)


def index_col(is_pandas, n, start=0):
    if is_pandas:
        return pd.Series(np.arange(start, start + n), dtype='Int64')
    else:
        return pl.Series(np.arange(start, start + n), dtype=pl.Int64)


def get_diffs_df_with_cols_and_index(df, *args, **kwargs):
    return specialize(
        df,
        inspect.stack()[0][3],  # this function's name
        df,
        *args,
        **kwargs,
    )


def polars_get_diffs_df_with_cols_and_index(df, cols, rowdiffs, n, key=None):
    idx = '_tdda_idx_'
    nc = '_tdda_nc_'
    out_df = (
        df.with_row_index(idx)
        .with_columns(rowdiffs.alias(nc))
        .filter(pl.col('_tdda_nc_') > 0)
        .select(cols + [idx])
        .head(n)
    )
    return out_df.select(cols), out_df[idx].to_list()


def pandas_get_diffs_df_with_cols_and_index(df, cols, rowdiffs, n, key=None):
    if key is None:
        out_df = get_diffs_df_with_cols(df, cols, rowdiffs, n)
        return out_df, out_df.index.to_list()
    else:
        cols = cols if key is None else [c for c in cols if c != key]
        out_df = get_diffs_df_with_cols(df, cols, rowdiffs, n)
        return out_df, out_df[key].to_list()


def get_diffs_df_with_cols(df, *args, **kwargs):
    return specialize(
        df,
        inspect.stack()[0][3],  # this function's name
        df,
        *args,
        **kwargs,
    )


def polars_get_diffs_df_with_cols(df, cols, rowdiffs, n):
    nc = '_tdda_nc_'
    delta = len(df) - len(rowdiffs)
    if delta > len(rowdiffs):
        rowdiffs = concat_series(
            [rowdiffs, pl.Series(np.ones(delta, dtype=bool))]
        )
    return (
        df.with_columns(rowdiffs.alias(nc))
        .filter(pl.col('_tdda_nc_') > 0)
        .select(cols)
        .head(n)
    )


def pandas_get_diffs_df_with_cols(df, cols, rowdiffs, n):
    delta = len(df) - len(rowdiffs)
    if delta > 0:
        rowdiffs = concat_series(
            [rowdiffs, pd.Series(np.ones(delta, dtype=bool))]
        ).reset_index(drop=True)
    elif delta < 0:
        rowdiffs = rowdiffs[: len(df)]
    return df[cols][rowdiffs > 0].head(n)


def df_to_lists(df, *args, **kwargs):
    return specialize(
        df,
        inspect.stack()[0][3],  # this function's name
        df,
        *args,
        **kwargs,
    )


def polars_df_to_lists(df, n=None):
    return extend_table(df.rows(), df.shape[1], n)


def pandas_df_to_lists(df, n=None):
    L = [df[c].to_list() for c in df]
    return extend_table(list(map(list, zip(*L))), df.shape[1], n)


def extend_table(table, ncols, target=None):
    if target is not None and len(table) < target:
        table.extend([([''] * ncols) for i in range(target - len(table))])
    return table


def all_fields_except(exclusions):
    """
    Helper function, for using with *check_data*, *check_types* and
    *check_order* parameters to assertion functions for Pandas DataFrames.

    It returns the names of all of the fields in the DataFrame being
    checked, apart from the ones given.

    *exclusions* is a list of field names.
    """
    return lambda df: sorted(set(col_names(df)) - set(exclusions))


def csv_to_dataframe(
    path=None,
    md_path=None,
    md_file_type=None,
    find_md=False,
    backend=None,
    engine=None,
    infer_datetime_formats=False,
    config=None,
):
    """
    Load a csv file to a DataFrame of a type (Pandas or Polars)
    determined by engine or config.
    """
    config = get_config(config)
    engine = config.get('engine', engine)
    if engine == 'polars':
        return csv_to_polars(
            path=path,
            md_path=md_path,
            md_file_type=md_file_type,
            find_md=find_md,
            infer_datetime_format=infer_datetime_formats,
        )
    elif engine == 'pandas':
        return csv_to_pandas(
            path=path,
            md_path=md_path,
            md_file_type=md_file_type,
            find_md=find_md,
            backend=backend,
            infer_datetime_formats=infer_datetime_formats,
        )
    else:
        error(f'Unknown DateFrame engine: {engine}.')


def get_scalar_eq(df):
    """
    Return scalar equal function for df
    """
    return pd_scalar_eq if df_type(df) == 'pandas' else pl_scalar_eq


def isnull_fn(df):
    return pd.isnull if df_type(df) == 'pandas' else lambda x: x is None


def isnull_col(c):
    return c.isnull() if is_pandas_series(c) else c.is_null()


def fillnull_col(c, v):
    return c.fillna(v) if is_pandas_series(c) else c.fill_null(True)


def pd_scalar_eq(L, R):
    if pd.isnull(L):
        return pd.isnull(R)
    elif pd.isnull(R):
        return False
    else:
        return L == R


def pl_scalar_eq(L, R):
    return L == R


def df_sort(df, keys):
    if df_type(df) == 'pandas':
        return df.sort_values(keys).reset_index(drop=True)
    else:
        return df.sort(keys)


def df_group_count(df, keys):
    return (
        df.groupby(keys).count().reset_index()
        if df_type(df) == 'pandas'
        else df.group_by(keys).len()
    )


def calc_nunique(col):
    return col.nunique() if is_pandas_series(col) else col.n_unique()


def get_engine_and_backend(engine=None, backend=None, config=None):
    config = get_config(config)
    return config.get('engine', engine), config.get('pandas_backend', backend)


def filter_fields(df, fields=None, xfields=None):
    """
    Return version of df containing only fields in fields (if provided)
    and not including fields in xfields (if provided).

    Will be the original dataframe if unchanged.
    """
    if fields:
        keep = [f for f in df if f in set(fields)]
        if len(keep) < len(list(df)):
            df = df[keep]

    if xfields:
        subset = [f for f in df if f not in set(xfields)]
        if len(subset) < len(list(df)):
            df = df[subset]
    return df


def find_non_fields(df, fields):
    """
    Return any fields in the list/collection fields that are not in df
    """
    return [
        f for f in list(df) if f not in set(fields).intersection(set(df))
    ]


def df_add_named_col_with_values(df, name, values):
    if is_pandas_df(df):
        df[name] = values
        return df
    else:
        return df.with_columns(pl.Series(name, values))


def df_join(left, right, keyL, keyR=None, how='outer', suffix='__r', **kw):
    keyR = nvl(keyR, keyL)
    if is_pandas_df(left):
        return left.merge(
            right,
            left_on=keyL,
            right_on=keyR,
            how=how,
            suffixes=('', suffix),
            **kw,
        )
    else:
        how = 'full' if how == 'outer' else how
        return left.join(
            right,
            left_on=keyL,
            right_on=keyR,
            how=how,
            suffix=suffix,
            coalesce=True,  # return key even if only in right
            **kw,
        )


def concat_series(series):
    if is_pandas_series(series[0]):
        return pd.concat(series).reset_index(drop=True)
    else:
        return pl.concat(series)


def df_len_diff(L, R, absolute=False):
    n = len(L) - len(R)
    return abs(n) if absolute else n
