import inspect

import pandas as pd
import polars as pl

def col_names(df):
    if is_pandas_df(df):
        return list(df)
    elif is_polars_df(df):
        return df.columns
    else:
        error('Not a known kind of DataFrame.')


def is_pandas_df(df):
    return isinstance(df, pd.DataFrame)


def is_polars_df(df):
    return isinstance(df, pl.DataFrame)


def df_type(df):
    if isinstance(df, pd.DataFrame):
        return 'pandas'
    if isinstance(df, pl.DataFrame):
        return 'polars'
    raise TDDAError('Not a known kind of data frame.')


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
        error(f'Cannot convert {rft} data frame to {engine}.')


def specialize(df, fn, *args, **kwargs):
    f = eval(f'{df_type(df)}_{fn}')
    return f(*args, **kwargs)


def get_diffs_df_with_cols_and_index(df, *args, **kwargs):
    return specialize(df, inspect.stack()[0][3],  # this function's name
                      df, *args, **kwargs)


def polars_get_diffs_df_with_cols_and_index(df, cols, rowdiffs, n):
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


def pandas_get_diffs_df_with_cols_and_index(df, cols, rowdiffs, n):
    out_df = get_diffs_df_with_cols(df, cols, rowdiffs, n)
    return out_df, out_df.index.to_list()


def get_diffs_df_with_cols(df, *args, **kwargs):
    return specialize(df, inspect.stack()[0][3],  # this function's name
                      df, *args, **kwargs)


def polars_get_diffs_df_with_cols(df, cols, rowdiffs, n):
    nc = '_tdda_nc_'
    return (
        df.with_columns(rowdiffs.alias(nc))
          .filter(pl.col('_tdda_nc_') > 0)
          .select(cols)
          .head(n)
    )

def pandas_get_diffs_df_with_cols(df, cols, rowdiffs, n):
    return df[cols][rowdiffs > 0].head(n)


def df_to_lists(df, *args, **kwargs):
    return specialize(df, inspect.stack()[0][3],  # this function's name
                      df, *args, **kwargs)

def polars_df_to_lists(df):
    return df.rows()

def pandas_df_to_lists(df):
    L = [df[c].to_list() for c in df]
    return list(map(list, zip(*L)))



