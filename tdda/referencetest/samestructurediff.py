import re
import sys

from itertools import chain

from rich.table import Table

from tdda.state import get_config
from tdda.utils import Dummy, nvl
from tdda.abstractdf import (
    col_names,
    get_diffs_df_with_cols_and_index,
    get_diffs_df_with_cols,
    df_to_lists,
    get_scalar_eq,
    isnull_fn,
)

ROW_NUM_HEADER = '#'
HASH_DIFF_KEY = '#'

QualifiedTypeRE = re.compile('^([A-Za-z0-9]+)+.*$')


class SameStructureDDiff:
    """
    Container for information about differences betwee data frames
    with the same structure.
    """
    def __init__(self, shape, diff_df, row_counts, n_vals, n_cols, n_rows,
                 key=None, colour=None, config=None):
        self.shape = shape
        self.n_diff_values = n_vals
        self.n_diff_cols = n_cols
        self.n_diff_rows = n_rows
        self.key = key
        self.diff_df = diff_df             # keyed on common column name
        self.row_diff_counts = row_counts  # count of diffs on each row
        self.config = config or get_config()

    def __str__(self):
        lines = [
            'Difference summary: ',
            'DataFrames have same structure, but different values.',
        ]
        tot_vals = self.shape[0] * self.shape[1]
        prop_diffs = 100 * self.n_diff_values / tot_vals
        lines.extend([
            f'Total number of different values: {self.n_diff_values:,}'
            f' of {tot_vals:,} ({prop_diffs:.2f}%).',

            f'Total number of rows with differences: {self.n_diff_rows:,}',
            f'Total number of columns with differences: {self.n_diff_cols:,}:',
        ])
        for c in col_names(self.diff_df):
            n = self.diff_df[c].sum()
            lines.append(f'  {n:10,}: {c}')

        return '\n'.join(lines)

    def details(self, df, ref_df, target_rows=None):
        target_rows = nvl(target_rows, self.n_diff_rows)
        n = min(target_rows, self.n_diff_rows)
        cols = col_names(self.diff_df)
        m = len(cols)
        C = self.config.referencetest
        vertical = nvl(C.vertical, False)
        prefix = vertical and (C.mono or C.bw)
        if self.n_diff_rows > 0:  # <= n:
            # Extract small dataframes with diffs  n x m
            if self.key:
                L = get_diffs_df_with_cols(
                    df, cols, self.row_diff_counts.rowdiffs, n
                )
            else:
                L, indexes = get_diffs_df_with_cols_and_index(
                    df, cols, self.row_diff_counts.rowdiffs, n
                )
            R = get_diffs_df_with_cols(
                ref_df, cols, self.row_diff_counts.rowdiffs, n
            )
            plain_rows = []
            L_table, R_table = df_to_lists(L), df_to_lists(R)
            for r in range(n):
                l_vals = L_table[r]
                r_vals = R_table[r]
                if vertical:
                    if self.key:
                        plain_rows.append(l_vals)
                        plain_rows.append(r_vals)
                    else:
                        plain_rows.append([indexes[r]] + l_vals)
                        plain_rows.append([indexes[r]] + r_vals)
                else:
                    if self.key:
                        plain_rows.append(
                            [indexes[r]]
                            + list(chain(*([L, R]
                                   for L, R in zip(l_vals, r_vals))))
                        )
                    else:
                        plain_rows.append(
                            [indexes[r]]
                            + list(chain(*([L, R]
                                 for L, R in zip(l_vals, r_vals))))
                    )

            index_header = [] if self.key else [ROW_NUM_HEADER]

            s = '' if n == 1 else 's'
            rows_desc = (
                'all rows with differences'
                 if self.n_diff_rows <= n
                 else f'First {n:,} row{s} with differences'
            )
            title = f'Value Differences ({rows_desc})'
            return Dummy(title=title, cols=index_header + cols,
                         rows=plain_rows)
        else:
            return None

    def details_table(self, df, ref_df, target_rows=None):
        eq = get_scalar_eq(df)
        target_rows = nvl(target_rows, self.n_diff_rows)
        n = min(target_rows, self.n_diff_rows)
        cols = col_names(self.diff_df)
        col0isKey = cols and cols[0] == HASH_DIFF_KEY
        m = len(cols)
        C = self.config.referencetest
        vertical = nvl(C.vertical, False)
        prefix = vertical and (C.mono or C.bw)
        isnull = isnull_fn(df)
        if self.n_diff_rows > 0:  # <= n:
            # Extract small dataframes with diffs  n x m
            if self.key:
                L = get_diffs_df_with_cols(
                    df, cols, self.row_diff_counts.rowdiffs, n
                )
            else:
                L, row_indexes = get_diffs_df_with_cols_and_index(
                    df, cols, self.row_diff_counts.rowdiffs, n
                )
            R = get_diffs_df_with_cols(
                ref_df, cols, self.row_diff_counts.rowdiffs, n
            )

            pL, pR = C.stripped_prefixes(pre=' ' if vertical else '')
            if not self.key:
                indexes = [
                    C.common(v, dim_if_not_bw=True) for v in row_indexes
                ]
                pl_indexes = [
                    C.common(v, plain=True) for v in row_indexes
                ]
            rows, plain_rows = [], []
            L_table, R_table = df_to_lists(L), df_to_lists(R)
            for r in range(n):
                l_vals = L_table[r]
                r_vals = R_table[r]
                if col0isKey and isnull(l_vals[0]):  # left row missing
                    plstr = lstr = [''] * len(l_vals)
                else:
                    lstr = [
                        C.common(left) if eq(left, right)
                                       else C.left_diff(left, prefix)
                        for (left, right) in zip(l_vals, r_vals)
                    ]
                    plstr = [
                        C.left_annotated(left, prefix) for left in l_vals
                    ]
                if col0isKey and isnull(r_vals[0]):  # right row missing
                    prstr = rstr = [''] * len(l_vals)
                else:
                    rstr = [
                        C.common(right) if eq(left, right)
                                        else C.right_diff(right, prefix)
                        for (left, right) in zip(l_vals, r_vals)
                    ]
                    prstr = [
                        C.right_annotated(right, prefix) for right in r_vals
                    ]
                if vertical:
                    if not self.key:
                        rows.append([f'{indexes[r]}{pL}'] + lstr)
                        rows.append([f'{indexes[r]}{pR}'] + rstr)
                        plain_rows.append([f'{pl_indexes[r]}{pL}'] + plstr)
                        plain_rows.append([f'{pl_indexes[r]}{pR}'] + prstr)
                else:
                    if self.key:
                        rows.append(
                            list(chain(*([L, R]
                                   for L, R in zip(lstr, rstr))))
                        )
                        plain_rows.append(
                            list(chain(*([L, R]
                                   for L, R in zip(plstr, prstr))))
                        )
                    else:
                        rows.append(
                            [pl_indexes[r]]
                            + list(chain(*([L, R]
                                   for L, R in zip(lstr, rstr))))
                        )
                        plain_rows.append(
                            [pl_indexes[r]]
                            + list(chain(*([L, R]
                                   for L, R in zip(plstr, prstr))))
                        )
            type_headers = []
            index_head = '' if self.key else ROW_NUM_HEADER
            if vertical:
                n_table_cols = len(plain_rows[0])
                widths = [
                    max(len(row[i]) for row in plain_rows)
                    for i in range(n_table_cols)
                ]
                for i, col in enumerate(cols):
                    tL, tR = type_header(L[col]), type_header(R[col])
                    type_headers.append(f'{tL}\n{tR}')
                    widths[1 + i] = max(widths[1 + i],
                                        len(cols[i]),
                                        len(tL),
                                        len(tR))
                widths[0] = max(widths[0], len(index_head))
                col_space = sum(widths)
                table_width = col_space + (n_table_cols) * 3
                header_width = sum(len(name) for name in cols)
            else:
                n_table_cols = len(plain_rows[0])
                widths = [
                    max(len(row[i]) for row in plain_rows)
                    for i in range(n_table_cols)
                ]
                for i, col in enumerate(cols):
                    tL, tR = type_header(L[col]), type_header(R[col])
                    type_headers.extend([tL, tR])
                    widths[i * 2] = max(widths[i * 2],
                                            len(cols[i]),
                                            len(pL),
                                            len(tL))
                    widths[1 + i * 2] = max(widths[1 + i * 2],
                                            len(cols[i]),
                                            len(pR),
                                            len(tR))
                widths[0] = max(widths[0], len(index_head))
                col_space = sum(widths)
                table_width = col_space + (n_table_cols) * 3
                header_width = sum(len(name) for name in cols)

            s = '' if n == 1 else 's'
            rows_desc = (
                'all rows with differences'
                 if self.n_diff_rows <= n
                 else f'First {n:,} row{s} with differences'
            )
            title = f'Value Differences ({rows_desc})'
            table = Table(
                title=title,
                title_style='bold',
                width=table_width,
            )
            if self.key:
                if vertical:
                    index_head += f'\n{pL}\n{pR}'
                else:
                    index_head += '\n '
            if not self.key:
                table.add_column(index_head, justify='right', no_wrap=True)
            for i, col in enumerate(cols):
                if vertical:
                    tH = type_headers[i]
                    table.add_column('\n'.join((col, tH)),
                                     justify='right',
                                     min_width=widths[i + 1])
                else:
                    (tL, tR) = type_headers[2 * i:2 * i + 2]
                    table.add_column('\n'.join((col, tL, pL)), justify='right',
                                     min_width=widths[2 * i])
                    table.add_column('\n'.join((col, tR, pR)), justify='right',
                                     min_width=widths[2 * i + 1])
            for row in rows:
                table.add_row(*row)
            return table
        else:
            return None
            # find ones with most diffs (n=target-rows)
            # see which cols are covered
            # For the ones not covered
            # Find the first one
            # Get the indexes for all those
            # Show them


def type_header(col, suffix=''):
    t = str(col.dtype)
    m = re.match(QualifiedTypeRE, t)
    if m:
        t = m.group(1)
    return f'{t}{suffix}'


def is_synthetic(name):
    """
    Checks whether the join key is synthetic, i.e. a row number
    used when no join is specified/found.

    For the moment, just checks whether the name is '#'
    """
    return name == ROW_NUM_HEADER
