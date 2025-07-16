import inspect

import pandas as pd
import polars as pl

from tdda.state import get_config
from tdda.utils import TDDAError, nvl, error

from tdda.serial import csv_to_pandas, csv_to_polars


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


def all_fields_except(exclusions):
    """
    Helper function, for using with *check_data*, *check_types* and
    *check_order* parameters to assertion functions for Pandas DataFrames.

    It returns the names of all of the fields in the DataFrame being
    checked, apart from the ones given.

    *exclusions* is a list of field names.
    """
    return lambda df: sorted(set(col_names(df)) - set(exclusions))


def csv_to_dataframe(path=None, md_path=None, md_file_type=None,
                     find_md=False, backend=None, engine=None,
                     infer_datetime_formats=False):
    """
    Load a csv file to a DataFrame of a type (Pandas or Polars)
    determined by engine or config.
    """
    config = get_config()
    engine = nvl(engine, config.engine)
    if engine == 'polars':
        return csv_to_polars(path=path, md_path=md_path,
                             md_file_type=md_file_type,
                             find_md=find_md,
                             infer_datetime_format=infer_datetime_format)
    elif engine == 'pandas':
        return csv_to_pandas(path=path, md_path=md_path,
                             md_file_type=md_file_type,
                             find_md=find_md, backend=backend,
                             infer_datetime_formats=infer_datetime_formats)
    else:
        error(f'Unknown DateFrame engine: {engine}.')

def get_sceq(df):
    """
    Return scale equal function for df
    """
    return pd_sceq if df_type(df) == 'pandas' else pl_sceq


def pd_sceq(L, R):
    if pd.isnull(L):
        return pd.isnull(R)
    elif pd.isnull(R):
        return False
    else:
        return L == R


def pl_sceq(L, R):
    return L == R


def calc_nunique(col):
    return col.nunique()


def get_engine_and_backend(engine=None, backend=None):
    config = get_config()
    return config.get('engine', engine), config.get('pandas_backend', backend)

