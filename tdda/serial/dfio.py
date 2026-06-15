import os

import polars as pl

from tdda.serial.pandasio import pandas_read_df, pandas_write_df
from tdda.serial.polarsio import polars_read_df, polars_write_df
from tdda.state import get_config


def read_df(
    path,
    engine=None,
    backend=None,
    md_path=None,
    find_md=False,
    config=None,
    **kw,
):
    """Read a DataFrame from a CSV or Parquet file.

    Dispatches to pandas or polars based on engine, falling back to config.

    Args:
        path (str): Path to CSV or Parquet file.
        engine (str): 'pandas' or 'polars'. If None, read from config.
        backend (str): Pandas backend ('numpy_nullable', 'pyarrow', etc.).
        md_path (str): Optional path to associated serial metadata file.
        find_md (bool): If True, search for metadata file automatically.
        config: Optional config object or path.

    Returns:
        A pandas or polars DataFrame.
    """
    config = get_config(config)
    if engine is None:
        engine = config.get('engine', 'pandas')
    if engine == 'polars':
        return polars_read_df(path, md_path=md_path, find_md=find_md, **kw)
    else:
        return pandas_read_df(
            path, backend=backend, config=config,
            md_path=md_path, find_md=find_md, **kw
        )


def write_df(df, path, **kw):
    """Write a DataFrame to a CSV or Parquet file.

    Dispatches to pandas or polars based on the type of df.
    Non-parquet extensions are treated as CSV.

    Args:
        df: A pandas or polars DataFrame.
        path (str): Destination path. Extension determines format.
    """
    _, ext = os.path.splitext(path)
    if ext.lower() == '.parquet':
        if not isinstance(df, pl.DataFrame):
            pandas_write_df(df, path, **kw)
        else:
            polars_write_df(df, path, **kw)
    else:
        if not isinstance(df, pl.DataFrame):
            df.to_csv(path, **kw)
        else:
            df.write_csv(path)
