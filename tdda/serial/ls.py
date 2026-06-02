# -*- coding: utf-8 -*-

"""
tdda ls — list fields in a dataset, optionally with type/min/max/null info.
"""

import os
import sys

import argparse

import pandas as pd
import polars as pl

from rich.table import Table

from tdda.serial.pandasio import csv_to_pandas
from tdda.serial.polarsio import csv_to_polars
from tdda.utils import cprint, error, handle_tilde, tdda_path_info, stdout_console


USAGE = """
tdda ls [--long] [--pandas | --polars] [--backend BACKEND] INPUT

Show fields in a dataset.

Without --long, prints a summary line and a right-aligned list of field names.
With --long, prints a summary line and a rich table with dtype, min, max, nulls.

INPUT may be:
  a .parquet file
  a .csv file (or .tsv, .psv, .txt)
  a .csv file with colon syntax to force metadata lookup (e.g. foo.csv:)
  a .csv file with explicit metadata path (e.g. foo.csv:foo.serial)
"""


def load_dataset(path, polars=False, backend=None):
    """Load dataset, returning (df, engine_label, data_path, md_path).

    md_path is the metadata file actually used, or None.
    """
    info = tdda_path_info(path)
    data_path = info.path
    ext = info.ext.lower()

    if not os.path.exists(handle_tilde(data_path)):
        error('File not found: %s' % data_path)

    if ext == '.parquet':
        if polars:
            df = pl.read_parquet(handle_tilde(data_path))
            engine = 'Polars'
        else:
            kw = {}
            if backend:
                kw['dtype_backend'] = backend
            df = pd.read_parquet(handle_tilde(data_path), **kw)
            engine = 'Pandas'
        return df, engine, data_path, None, None

    # Flat file — use csv_to_x with metadata awareness
    find_md = info.find_md
    md_path = info.md_path

    if polars:
        result = csv_to_polars(
            path=data_path,
            md_path=md_path,
            find_md=find_md,
            return_md=True,
        )
        engine = 'Polars'
        reader = 'tdda.serial.csv_to_polars'
    else:
        result = csv_to_pandas(
            path=data_path,
            md_path=md_path,
            find_md=find_md,
            backend=backend,
            return_md=True,
        )
        engine = 'Pandas'
        reader = 'tdda.serial.csv_to_pandas'

    df = result.df
    used_md_path = result.md.path if result.md else None
    return df, engine, data_path, used_md_path, reader


def summary_line(data_path, n_records, n_fields, engine):
    name = os.path.basename(data_path)
    return '%s: %s records; %s fields. [%s]' % (
        name,
        f'{n_records:,}',
        f'{n_fields:,}',
        engine,
    )


def reader_line(reader, md_path):
    if reader is None:
        return None
    if md_path:
        md_name = os.path.basename(md_path)
        return 'Read by %s with %s metadata' % (reader, md_name)
    return 'Read by %s with no external metadata' % reader


def ls_short(df, data_path, md_path, engine, reader):
    if hasattr(df, 'columns') and hasattr(df.columns, 'tolist'):
        fields = df.columns.tolist()           # pandas
    else:
        fields = df.columns                    # polars

    n_records = len(df)
    n_fields = len(fields)

    cprint(summary_line(data_path, n_records, n_fields, engine))
    rline = reader_line(reader, md_path)
    if rline:
        print(rline)
    if not fields:
        return

    width = max(len(f) for f in fields)
    for f in fields:
        print(f.rjust(width))


def ls_long(df, data_path, md_path, engine, reader):
    if hasattr(df, 'columns') and hasattr(df.columns, 'tolist'):
        fields = df.columns.tolist()           # pandas
        is_polars = False
    else:
        fields = list(df.columns)              # polars
        is_polars = True

    n_records = len(df)
    n_fields = len(fields)

    cprint(summary_line(data_path, n_records, n_fields, engine))
    rline = reader_line(reader, md_path)
    if rline:
        print(rline)

    rows = []
    for f in fields:
        col = df[f]
        dtype = str(col.dtype).split('(')[0]
        if is_polars:
            null_count = col.null_count()
            non_null = col.drop_nulls()
            if len(non_null) > 0:
                if col.dtype == pl.Categorical:
                    non_null = non_null.cast(pl.String)
                col_min = str(non_null.min())
                col_max = str(non_null.max())
            else:
                col_min = col_max = ''
        else:
            null_count = int(col.isna().sum())
            non_null = col.dropna()
            if len(non_null) > 0:
                if non_null.dtype.name == 'category':
                    non_null = non_null.astype(str)
                col_min = str(non_null.min())
                col_max = str(non_null.max())
            else:
                col_min = col_max = ''
        rows.append((f, dtype, col_min, col_max, str(null_count)))

    headers = ('Field', '%s dtype' % engine, 'Min', 'Max', 'Nulls')
    plain_rows = rows
    widths = [len(h) for h in headers]
    for row in plain_rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(val))

    table_width = sum(widths) + len(widths) * 3 + 1
    table = Table(width=table_width)
    justifications = ('right', 'left', 'right', 'right', 'right')
    for h, w, j in zip(headers, widths, justifications):
        table.add_column(h, justify=j, min_width=w, no_wrap=True)
    for row in rows:
        table.add_row(*row)

    stdout_console.print(table)


def ls_main(argv):
    parser = argparse.ArgumentParser(
        prog='tdda ls',
        description='List fields in a dataset',
        add_help=False,
    )
    parser.add_argument('-h', '-?', '--help', action='store_true')
    parser.add_argument(
        '-1', '--one-line', dest='one_line', action='store_true',
        help='List all field names on one line, space-separated',
    )
    parser.add_argument(
        '-l', '--long', action='store_true',
        help='Show dtype, min, max, and null count per field',
    )
    parser.add_argument(
        '--pandas', '--pd', dest='pandas', action='store_true',
        help='Use Pandas (default)',
    )
    parser.add_argument(
        '--polars', '--pl', dest='polars', action='store_true',
        help='Use Polars',
    )
    parser.add_argument(
        '--backend', '-B', dest='backend', default=None,
        help='Pandas backend: n (numpy_nullable), a (pyarrow), o (original)',
    )
    parser.add_argument('input', nargs='?', help='Dataset path')

    flags = parser.parse_args(argv)

    if flags.help or not flags.input:
        print(USAGE)
        sys.exit(0 if flags.help else 1)

    if flags.polars and flags.pandas:
        error('Cannot specify both --pandas and --polars')

    df, engine, data_path, md_path, reader = load_dataset(
        flags.input,
        polars=flags.polars,
        backend=flags.backend,
    )

    if flags.one_line:
        fields = (df.columns.tolist() if hasattr(df.columns, 'tolist')
                  else list(df.columns))
        print(' '.join(fields))
    elif flags.long:
        ls_long(df, data_path, md_path, engine, reader)
    else:
        ls_short(df, data_path, md_path, engine, reader)
