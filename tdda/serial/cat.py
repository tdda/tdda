# -*- coding: utf-8 -*-

"""
tdda cat/head/tail/sample — display rows from a dataset as a rich table.
"""

import os
import random
import re
import sys
import textwrap
import argparse

import pandas as pd
import polars as pl

from io import StringIO

from rich.console import Console
from rich.table import Table

from tdda.serial.ls import load_dataset, summary_line, reader_line
from tdda.utils import error, globlike_match, stdout_console


COMMAND_DEFAULTS = {
    'cat':    dict(default_n=None, default_tail=False, default_random=False),
    'head':   dict(default_n=20,   default_tail=False, default_random=False),
    'tail':   dict(default_n=20,   default_tail=True,  default_random=False),
    'sample': dict(default_n=20,   default_tail=False, default_random=True),
}

USAGES = {
    'cat': """
tdda cat [N | -N | +N] [--fields FIELDS] [--xfields FIELDS]
         [-r N [--seed SEED]] [--pandas | --polars] [--backend BACKEND]
         INPUT [FIELD ...]

Display all rows from a dataset as a rich table.

  N or -N    First N rows
  +N         Last N rows

Fields to display may be given as positional arguments after INPUT,
or via --fields (or both).  Wildcards are supported (quote in shell).
""",
    'head': """
tdda head [N] [--fields FIELDS] [--xfields FIELDS]
          [--pandas | --polars] [--backend BACKEND]
          INPUT [FIELD ...]

Display the first N rows (default 20) of a dataset.

Fields to display may be given as positional arguments after INPUT,
or via --fields (or both).  Wildcards are supported (quote in shell).
""",
    'tail': """
tdda tail [N] [--fields FIELDS] [--xfields FIELDS]
          [--pandas | --polars] [--backend BACKEND]
          INPUT [FIELD ...]

Display the last N rows (default 20) of a dataset.

Fields to display may be given as positional arguments after INPUT,
or via --fields (or both).  Wildcards are supported (quote in shell).
""",
    'sample': """
tdda sample [N] [--seed SEED] [--fields FIELDS] [--xfields FIELDS]
            [--pandas | --polars] [--backend BACKEND]
            INPUT [FIELD ...]

Display N random rows (default 20) from a dataset.

Fields to display may be given as positional arguments after INPUT,
or via --fields (or both).  Wildcards are supported (quote in shell).
""",
}


_NULLS = ('None', 'NaT', 'nan', '<NA>', 'null')
_SHORT_HEADER_FLOOR = 4


def plain_value(v):
    s = str(v)
    return '∅' if s in _NULLS else s


def format_value(v):
    s = str(v)
    return '[dim]∅[/dim]' if s in _NULLS else s


def df_to_string(df, short=None):
    """Return a plain-text string representation of df as a rich table."""
    table = cat_table(df, None, None, None, None, short=short)
    if table is None:
        return ''
    buf = StringIO()
    console = Console(file=buf, no_color=True, highlight=False)
    console.print(table)
    return buf.getvalue()


def cat_table(df, data_path, md_path, engine, reader, title=None, short=None):
    """Build a rich Table of df rows and return it; print header lines.

    short: None = normal; 's' = wrap headers at punctuation; 'S' = wrap anywhere
    """
    if hasattr(df, 'columns') and hasattr(df.columns, 'tolist'):
        fields = df.columns.tolist()
        is_polars = False
    else:
        fields = list(df.columns)
        is_polars = True

    n_records = len(df)
    n_fields = len(fields)

    if data_path is not None:
        summary = summary_line(data_path, n_records, n_fields, engine)
        if title:
            summary = '%s  [%s]' % (summary, title)
        stdout_console.print(summary)
        rline = reader_line(reader, md_path)
        if rline:
            print(rline)

    if n_records == 0:
        return None

    if is_polars:
        plain_rows = [
            [plain_value(df[f][i]) for f in fields]
            for i in range(n_records)
        ]
        display_rows = [
            [format_value(df[f][i]) for f in fields]
            for i in range(n_records)
        ]
    else:
        plain_rows = [
            [plain_value(df[f].iloc[i]) for f in fields]
            for i in range(n_records)
        ]
        display_rows = [
            [format_value(df[f].iloc[i]) for f in fields]
            for i in range(n_records)
        ]

    # Width from data only in short mode; otherwise include header width.
    if short:
        widths = [_SHORT_HEADER_FLOOR] * len(fields)
    else:
        widths = [len(f) for f in fields]
    for row in plain_rows:
        for i, val in enumerate(row):
            widths[i] = max(widths[i], len(val))

    # Build multiline headers; adjust widths to fit longest header line.
    if short == 's':
        headers = []
        for i, f in enumerate(fields):
            # Split at punctuation and lowercase→uppercase transitions
            tmp = re.sub(r'([a-z])([A-Z])', r'\1\n\2', f)
            tmp = re.sub(r'[_.\-]', '\n', tmp)
            segs = [s for s in tmp.split('\n') if s]
            # Greedily pack segments onto lines at data width
            target = widths[i]
            lines, cur = [], ''
            for seg in segs:
                if not cur:
                    cur = seg
                elif len(cur) + 1 + len(seg) <= target:
                    cur += ' ' + seg
                else:
                    lines.append(cur)
                    cur = seg
            if cur:
                lines.append(cur)
            headers.append('\n'.join(lines))
            widths[i] = max(widths[i], max(len(l) for l in lines))
    elif short == 'S':
        headers = []
        for i, f in enumerate(fields):
            w = widths[i]
            lines = textwrap.wrap(f, width=max(w, 1), break_long_words=True)
            headers.append('\n'.join(lines))
    else:
        headers = list(fields)

    table_width = sum(widths) + len(widths) * 3 + 1
    table = Table(width=table_width)
    for h, w in zip(headers, widths):
        table.add_column(h, justify='right', min_width=w, no_wrap=True)
    for row in display_rows:
        table.add_row(*row)

    return table


def slice_df(df, n, tail=False):
    if n is None:
        return df
    if tail:
        return df[-n:]
    return df[:n]


def random_sample(df, n, seed, is_polars):
    """Return n random rows from df, using seed (printed if auto-generated)."""
    if seed is None:
        seed = random.randint(0, 2**31 - 1)
        print('Random seed: %d' % seed)
    n = min(abs(n), len(df))
    if is_polars:
        return df.sample(n=n, seed=seed)
    return df.sample(n=n, random_state=seed)


def _parse_field_list(raw):
    """Split a field spec on commas and whitespace, returning a flat list."""
    return [f for f in re.split(r'[\s,]+', raw) if f]


def select_fields(df, fields, xfields, all_fields, is_polars):
    """Filter df columns by --fields and --xfields patterns."""
    keep = all_fields
    if fields:
        patterns = _parse_field_list(fields)
        seen = set()
        ordered = []
        for p in patterns:
            for f in globlike_match([p], all_fields):
                if f not in seen:
                    seen.add(f)
                    ordered.append(f)
        keep = ordered
    if xfields:
        patterns = _parse_field_list(xfields)
        exclude = set(globlike_match(patterns, all_fields))
        keep = [f for f in keep if f not in exclude]
    if keep == all_fields:
        return df
    if is_polars:
        return df.select(keep)
    return df[keep]


def parse_n_arg(argv):
    """Extract optional N / -N / +N from argv, return (n, tail, remaining)."""
    remaining = []
    n = None
    tail = False
    skip_next = False
    for arg in argv:
        if skip_next:
            remaining.append(arg)
            skip_next = False
        elif arg in ('-r', '--random', '--seed'):
            remaining.append(arg)
            skip_next = True
        elif arg.startswith('+') and arg[1:].isdigit():
            n = int(arg[1:])
            tail = True
        elif arg.startswith('-') and arg[1:].isdigit():
            n = int(arg[1:])
            tail = False
        elif arg.isdigit():
            n = int(arg)
            tail = False
        else:
            remaining.append(arg)
    return n, tail, remaining


def cat_main(argv, command='cat'):
    defaults = COMMAND_DEFAULTS[command]
    default_n = defaults['default_n']
    default_tail = defaults['default_tail']
    default_random = defaults['default_random']

    n, tail, argv = parse_n_arg(argv)
    if default_tail:
        tail = not tail  # tdda tail reverses the sign convention

    parser = argparse.ArgumentParser(
        prog='tdda %s' % command,
        description=USAGES[command].strip().splitlines()[0],
        add_help=False,
    )
    parser.add_argument('-h', '-?', '--help', action='store_true')
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
    parser.add_argument(
        '--fields', dest='fields', default=None,
        metavar='FIELDS',
        help='Show only these fields (comma or space-separated, wildcards ok)',
    )
    parser.add_argument(
        '--xfields', dest='xfields', default=None,
        metavar='FIELDS',
        help='Exclude these fields (comma or space-separated, wildcards ok)',
    )
    parser.add_argument(
        '-s', dest='short', action='store_const', const='s', default=None,
        help='Wrap headers at punctuation (_.-); column width from data only',
    )
    parser.add_argument(
        '-S', dest='short', action='store_const', const='S',
        help='Wrap headers anywhere; column width from data only',
    )
    parser.add_argument(
        '-r', '--random', dest='random', type=int, default=None,
        metavar='N',
        help='Show N random rows',
    )
    parser.add_argument(
        '--seed', dest='seed', type=int, default=None,
        help='Random seed (default: auto-generated and printed)',
    )
    parser.add_argument('input', nargs='?', help='Dataset path')
    parser.add_argument('pos_fields', nargs='*', help='Fields to display')

    flags = parser.parse_args(argv)

    if flags.help or not flags.input:
        print(USAGES[command])
        sys.exit(0 if flags.help else 1)

    if flags.pos_fields:
        extra = ','.join(flags.pos_fields)
        flags.fields = (flags.fields + ',' + extra) if flags.fields else extra

    if flags.polars and flags.pandas:
        error('Cannot specify both --pandas and --polars')

    df, engine, data_path, md_path, reader = load_dataset(
        flags.input,
        polars=flags.polars,
        backend=flags.backend,
    )

    is_polars = engine == 'Polars'
    all_fields = list(df.columns)

    use_random = default_random or flags.random is not None
    if use_random:
        rand_n = flags.random if flags.random is not None else (
            n if n is not None else default_n
        )
        df = random_sample(df, rand_n, flags.seed, is_polars)
    else:
        effective_n = n if n is not None else default_n
        df = slice_df(df, effective_n, tail=tail)

    if flags.fields or flags.xfields:
        df = select_fields(
            df, flags.fields, flags.xfields, all_fields, is_polars
        )

    table = cat_table(df, data_path, md_path, engine, reader, short=flags.short)
    if table is not None:
        stdout_console.print(table)


def head_main(argv):
    cat_main(argv, command='head')


def tail_main(argv):
    cat_main(argv, command='tail')


def sample_main(argv):
    cat_main(argv, command='sample')
