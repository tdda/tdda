import re
import sys

from itertools import chain

from rich.table import Table

from tdda.utils import Dummy, nvl, debug
from tdda.abstractdf import (
    col_names,
    get_diffs_df_with_cols_and_index,
    get_diffs_df_with_cols,
    df_to_lists,
    get_scalar_eq,
    isnull_fn,
)

QualifiedTypeRE = re.compile('^([A-Za-z0-9]+)+.*$')

ROW_NUM_HEADER = '#'
HASH_DIFF_KEY = '#'


class SameStructureDDiff:
    """
    Container for information about differences between data frames
    with the same column structure.
    """

    def __init__(
        self,
        shape,
        diff_df,
        row_counts,
        n_vals,
        n_cols,
        n_rows,
        row_delta,
        config,
        key=None,
        idx=None,
        colour=None,
    ):
        self.shape = shape
        self.n_diff_values = n_vals
        self.n_diff_cols = n_cols
        self.n_diff_rows = n_rows
        self.row_delta = row_delta
        self.key = key
        self.idx = idx
        self.diff_df = diff_df  # keyed on common column name
        self.row_diff_counts = row_counts  # count of diffs on each row
        self.config = config

    def __str__(self):
        lines = [
            'Difference summary: ',
            'DataFrames have same structure, but different values.',
        ]
        tot_vals = self.shape[0] * self.shape[1]
        prop_diffs = 100 * self.n_diff_values / tot_vals
        lines.extend(
            [
                f'Total number of different values: {self.n_diff_values:,}'
                f' of {tot_vals:,} ({prop_diffs:.2f}%).',
                f'Total number of rows with differences: {self.n_diff_rows:,}',
                f'Total number of columns with differences: {self.n_diff_cols:,}:',
            ]
        )
        absdelta = abs(self.row_delta)
        for c in col_names(self.diff_df):
            n = self.diff_df[c].sum() + absdelta
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
                            + list(
                                chain(
                                    *([L, R] for L, R in zip(l_vals, r_vals))
                                )
                            )
                        )
                    else:
                        plain_rows.append(
                            [indexes[r]]
                            + list(
                                chain(
                                    *([L, R] for L, R in zip(l_vals, r_vals))
                                )
                            )
                        )

            index_header = [] if self.key else [ROW_NUM_HEADER]

            s = '' if n == 1 else 's'
            rows_desc = (
                'all rows with differences'
                if self.n_diff_rows <= n
                else f'First {n:,} row{s} with differences'
            )
            title = f'Value Differences ({rows_desc})'
            return Dummy(
                title=title, cols=index_header + cols, rows=plain_rows
            )
        else:
            return None

    def details_table(self, df, ref_df, target_rows=None):
        C = self.config.referencetest
        vertical = nvl(C.vertical, False)
        eq = get_scalar_eq(df)
        target_rows = nvl(target_rows, self.n_diff_rows)
        n = min(target_rows, self.n_diff_rows)
        cols = col_names(self.diff_df)
        nc = len(cols)
        prefix = (C.mono or C.bw) if vertical else ''
        isnull = isnull_fn(df)
        rows_delta = len(df) - len(ref_df)
        nL, nR = len(df), len(ref_df)
        delta = nL - nR
        if delta or self.idx is not None:
            blanks = [''] * nc
        if self.n_diff_rows == 0:
            return None

        key_vals = None
        # Extract small dataframes with diffs  n x m
        if self.key or delta < 0:
            L = get_diffs_df_with_cols(
                df, cols, self.row_diff_counts.rowdiffs, n
            )
        else:
            L, row_indexes = get_diffs_df_with_cols_and_index(
                df, cols, self.row_diff_counts.rowdiffs, n
            )
        if self.key:
            D = ref_df if delta < 0 else df
            key_vals = get_diffs_df_with_cols(
                D, self.key, self.row_diff_counts.rowdiffs, n
            )
        if delta < 0 and not self.key:
            R, row_indexes = get_diffs_df_with_cols_and_index(
                ref_df, cols, self.row_diff_counts.rowdiffs, n
            )
        else:
            R = get_diffs_df_with_cols(
                ref_df, cols, self.row_diff_counts.rowdiffs, n
            )
        LI = RI = None
        if self.idx:
            LI = df_to_lists(
                get_diffs_df_with_cols(
                    df, [self.idx], self.row_diff_counts.rowdiffs, n
                ),
                n,
            )
            RI = df_to_lists(
                get_diffs_df_with_cols(
                    ref_df, [self.idx], self.row_diff_counts.rowdiffs, n
                ),
                n,
            )
        pL, pR = C.stripped_prefixes(pre=' ' if vertical else '')
        N = min(self.n_diff_rows, target_rows)
        K_table = df_to_lists(key_vals, N) if key_vals is not None else None
        if self.key:
            indexes = [[str(k) for k in k_vals] for k_vals in K_table]
            pl_indexes = [[str(k) for k in k_vals] for k_vals in K_table]
        else:
            indexes = [[C.common(v, dim_if_not_bw=True)] for v in row_indexes]
            pl_indexes = [[C.common(v, plain=True)] for v in row_indexes]
        rows, plain_rows = [], []
        # N = min(self.n_diff_rows, target_rows)
        L_table, R_table = df_to_lists(L, N), df_to_lists(R, N)
        nK = len(key_vals) if key_vals is not None else 0
        nlt, nrt = len(L_table), len(R_table)
        isnull = isnull_fn(df)
        for r in range(n):
            if self.idx is not None:
                left_missing = isnull(LI[r][0])
                right_missing = isnull(RI[r][0])
            else:
                left_missing, right_missing = nlt <= r, nrt <= r
            k_vals = K_table[r] if self.key else []
            l_vals = blanks if left_missing else L_table[r]
            r_vals = blanks if right_missing else R_table[r]
            if left_missing:
                plstr = lstr = [''] * len(l_vals)
            else:
                lstr = [
                    C.left_diff(left, prefix)
                    if right_missing or not eq(left, right)
                    else C.common(left)
                    for (left, right) in zip(l_vals, r_vals)
                ]
                plstr = [C.left_annotated(left, prefix) for left in l_vals]
            if right_missing:
                prstr = rstr = [''] * len(l_vals)
            else:
                rstr = [
                    C.right_diff(right, prefix)
                    if left_missing or not eq(left, right)
                    else C.common(right)
                    for (left, right) in zip(l_vals, r_vals)
                ]
                prstr = [C.right_annotated(right, prefix) for right in r_vals]

            if vertical:
                rows.append([f'{indexes[r][0]}{pL}'] + lstr)
                rows.append([f'{indexes[r][0]}{pR}'] + rstr)
                plain_rows.append([f'{pl_indexes[r][0]}{pL}'] + plstr)
                plain_rows.append([f'{pl_indexes[r][0]}{pR}'] + prstr)
            else:
                rows.append(
                    pl_indexes[r]
                    + list(chain(*([L, R] for L, R in zip(lstr, rstr))))
                )
                plain_rows.append(
                    pl_indexes[r]
                    + list(chain(*([L, R] for L, R in zip(plstr, prstr))))
                )

        type_headers = []
        index_headers = self.key or [ROW_NUM_HEADER]

        n_table_cols = len(plain_rows[0])
        widths = [
            max(len(row[i]) for row in plain_rows) for i in range(n_table_cols)
        ]

        nih = len(index_headers)
        for i in range(len(index_headers)):
            widths[i] = max(widths[i], len(index_headers[i]))
        for i, col in enumerate(cols):
            tL, tR = type_header(L[col]), type_header(R[col])
            if vertical:
                type_headers.append(f'{tL}\n{tR}')
                widths[nih + i] = max(
                    widths[nih + i], len(cols[i]), len(tL), len(tR)
                )
            else:
                type_headers.extend([tL, tR])
                widths[nih + i * 2] = max(
                    widths[nih + i * 2], len(cols[i]), len(pL), len(tL)
                )
                widths[nih + 1 + i * 2] = max(
                    widths[nih + 1 + i * 2], len(cols[i]), len(pR), len(tR)
                )

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
        for k in index_headers:
            table.add_column(f'{k}\n\n', justify='right', no_wrap=True)
        for i, col in enumerate(cols):
            if vertical:
                tH = type_headers[i]
                table.add_column(
                    '\n'.join((col, tH)),
                    justify='right',
                    min_width=widths[i + 1],
                )
            else:
                (tL, tR) = type_headers[2 * i : 2 * i + 2]
                table.add_column(
                    '\n'.join((col, tL, pL)),
                    justify='right',
                    min_width=widths[nih + 2 * i],
                )
                table.add_column(
                    '\n'.join((col, tR, pR)),
                    justify='right',
                    min_width=widths[nih + 2 * i + 1],
                )
        for row in rows:
            table.add_row(*row)
        return table


def is_synthetic(name):
    """
    Checks whether the join key is synthetic, i.e. a row number
    used when no join is specified/found.

    For the moment, just checks whether the name is '#'
    """
    return name == ROW_NUM_HEADER


def type_header(col, suffix=''):
    t = str(col.dtype)
    m = re.match(QualifiedTypeRE, t)
    if m:
        t = m.group(1)
    return f'{t}{suffix}'
