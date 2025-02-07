import os
import pandas as pd
from tdda.serial.reader import csv2pandas


def pandas_read_df(path):
    """
    Reads a pandas data frame from parquet or csv, as the extension suggests.
    Prefers nullable types.
    """
    _, ext = os.path.splitext(path)
    if ext == '.csv':
        return csv2pandas(path)
    elif ext == '.parquet':
        return pd.read_parquet(path)
    else:
        raise Exception(f'Unexpected extension {ext} in {path}.')


def pandas_write_df(df, path):
    """
    Writes a pandas data frame as parquet or csv, as the extension suggests.
    Does not write the index.
    """
    _, ext = os.path.splitext(path)
    if ext == '.csv':
        df.to_csv(path, index=None)
    elif ext == '.parquet':
        df.to_parquet(path, index=None)
    else:
        raise Exception(f'Unexpected extension {ext} in {path}.')

