# -*- coding: utf-8 -*-

"""
checkfiles.py: comparison mechanism for text files

Source repository: http://github.com/tdda/tdda

License: MIT

Copyright (c) Stochastic Solutions Limited 2016-2022
"""

import json
import os
import re
import shutil
import sys
import tempfile

from collections import namedtuple

from rich.table import Table

FailureDiffs = namedtuple('FailureDiffs', 'failures diffs')

FieldDiff = namedtuple('FieldDiff', 'actual expected')

ColDiff = namedtuple('ColDiff', 'mask n')
DiffCounts = namedtuple('DiffCounts', 'rowdiffs n')


class BaseComparison(object):
    """
    Common base class for different implementations of comparisons.
    """
    def __init__(self, print_fn=None, verbose=True, tmp_dir=None):
        """
        Constructor for an instance of the BaseComparison class.

        The optional print_fn parameter is a function to be used to
        display information while comparison operations are running.
        If specified, it should be a function with the same signature
        as python's builtin print fsunction.
        """
        self.print_fn = print_fn
        self.verbose = verbose
        self.tmp_dir = tmp_dir or tempfile.gettempdir()

    def info(self, msgs, s):
        """
        Add an item to the list of messages, and also display it immediately
        if verbose is set.
        """
        if s is not None:
            msgs.append(s)
            if self.verbose and self.print_fn:
                self.print_fn(s)

    @staticmethod
    def compare_with(actual, expected, qualifier=None, binary=False,
                     custom_diff_cmd=''):
        qualifier = '' if not qualifier else (qualifier + ' ')
        f = lambda p: os.path.normpath(os.path.abspath(p))
        if os.path.exists(expected):
#            if binary:
#                return None
#            else:
                msg = 'Compare %swith:\n    %s %s %s\n'
                cmd = custom_diff_cmd or diffcmd()
        else:
            msg = 'Initialize %sfrom actual content with:\n    %s %s %s'
            cmd = copycmd()
        return msg % (qualifier, cmd, f(actual), f(expected))

    def tmp_path_for(self, path, prefix='actual-'):
        return os.path.join(self.tmp_dir, prefix + os.path.basename(path))

    def field_types_differ(self, diffs, c, actual_dtype, ref_dtype):
        """
        Record the fact that there is type difference between matched
        dataframe columns.
        """
        msg = ('Wrong column type for field %s actual: %s; expected: %s)'
               % (c, actual_dtype, ref_dtype))
        self.info(diffs, msg)
        diffs.df.field_types[c] = FieldDiff(actual_dtype, ref_dtype)

    def extra_columns_found(self, diffs, extra_cols, df):
        """
        Record the fact that there are extra columns df that aren't
        present in ref_df
        """
        if extra_cols:
            ordered = [
                c for (i, c) in sorted(
                    (df_col_pos(c, df), c)
                    for c in extra_cols)
            ]
            self.info(diffs, 'Extra columns: %s' % list(ordered))
            for c in ordered:
                diffs.df.extra[c] = df[c].dtype

    def missing_columns_detected(self, diffs, missing_cols, ref_df):
        """
        Record the fact that there are columns ref_df that aren't
        present in df
        """
        if missing_cols:
            ordered = [
                c for (i, c) in sorted(
                    (df_col_pos(c, ref_df), c)
                    for c in missing_cols)
            ]
            self.info(diffs, 'Missing columns: %s' % list(ordered))
            for c in ordered:
                diffs.df.extra[c] = ref_df[c].dtype

    def different_column_structure(self, diffs):
            self.failure(
                diffs,
                'Data frames have different column structure.',
            )

    def different_column_orders(self, diffs, df, ref_df):
        self.info(diffs,
           'Different column ordering between data frames.\n'
           f'  Actual ordering: {" ".join(list(df))}\n'
           f'Expected ordering: {" ".join(list(ref_df))}')
        diffs.df.actual_order = list(df)
        diffs.df.expected_order = list(ref_df)

    def different_numbers_of_rows(self, diffs, na, nr):
            self.failure(
                diffs, 'Data frames have different numbers of rows.',
            )
            self.info(
                diffs, f'Actual records: {na:,}; Expected records: {nr:,}'
            )
            same = False



class Diffs:
    """
    Class for representing a list of differences
    resulting from applying comparisons to a set of pairs of actual/expected
    objects. Objects can be strings or dataframes, which may be come
    from files on disk or simply been in memory.

    The 'messages' are a stream of message-strings, whereas the
    'reconstructions' are a list of one-per-comparison objects.

    It doesn't (currently) try to tie up the messages to individual
    comparison operations.

    When the objects are dataframes, the .df field contains a DDiffs
    object with structured information on the dataframe differences.
    """
    def __init__(self, lines=None):
        self.lines = lines or []
        self.reconstructions = []
        self.df = DataFrameDiffs()  # only used for DataFrames

    def append(self, line):
        self.lines.append(line)

    def add_reconstruction(self, r):
        self.reconstructions.append(r)

    def message(self):
        return '\n'.join(self.lines)

    def __repr__(self):
        # representation of a Diffs object is just its lines; used in tests.
        return repr(self.lines)

    def __eq__(self, other):
        # comparison between a Diffs object and a list of messages just
        # compares the lines part of the diffs; used in tests.
        if isinstance(other, Diffs):
            return self.lines == other.lines
        elif type(other) is list:
            return self.lines == other
        else:
            return False

    def __iter__(self):
        # iterating over a Diffs object is the same as iterating over
        # its internal messages; used in tests.
        return iter(self.lines)

    __str__ = message


class SameStructureDDiff:
    """
    Container for information about differences betwee data frames
    with the same structure.
    """
    def __init__(self, shape, diff_df, row_counts, n_vals, n_cols, n_rows):
        self.shape = shape
        self.n_diff_values = n_vals
        self.n_diff_cols = n_cols
        self.n_diff_rows = n_rows
        self.diff_df = diff_df            # keyed on common column name
        self.row_diff_counts = row_counts # count of diffs on each row

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
        for c in self.diff_df:
            n = self.diff_df[c].sum()
            lines.append(f'  {n:10,}: {c}')

        return '\n'.join(lines)

    def details_table(self, df, ref_df, target_rows=10):
        n = min(target_rows, self.n_diff_rows)
        cols = list(self.diff_df)
        m = len(cols)
#        if self.n_diff_rows <= n:
        if True:
            # Extract small dataframes with diffs  n x m
            L = df[cols][self.row_diff_counts.rowdiffs > 0].head(n)
            R = ref_df[cols][self.row_diff_counts.rowdiffs > 0].head(n)
            indexes = [str(v) for v in L.index.to_list()]
            rows = []
            plain_rows = []
            for r in range(n):
                l_vals = [py_val(L.iat[r, c]) for c in range(m)]
                r_vals = [py_val(R.iat[r, c]) for c in range(m)]
                lstr = [
                    str(left) if left == right else f'[red]{left}[/red]'
                    for (left, right) in zip(l_vals, r_vals)
                ]
                rstr = [
                    str(right) if left == right else f'[green]{right}[/green]'
                    for (left, right) in zip(l_vals, r_vals)
                ]
                rows.append([indexes[r]] + lstr)
                rows.append([indexes[r]] + rstr)
                plstr = [
                    str(left) for left in l_vals
                ]
                prstr = [
                    str(right) for right in r_vals
                ]
                plain_rows.append([indexes[r]] + plstr)
                plain_rows.append([indexes[r]] + prstr)
            term_width = shutil.get_terminal_size((80, 20))[0]
            widths = [
                max(len(row[i]) for row in plain_rows)
                for i in range(m + 1)
            ]
            col_space = sum(widths)
            table_width = col_space + m * 2
            header_width = sum(len(name) for name in cols)
            truncate = table_width > term_width and header_width > col_space
            index_head = 'index'
            if truncate:
                if widths[0] < 3:
                    index_head = ''
                elif widths[0] < 5:
                    index_head = 'idx'

            truncated = ', cols truncated' if table_width > term_width else ''
            s = '' if n == 1 else 's'
            rows_desc = (
                'all rows'
                 if self.n_diff_rows <= n
                 else f'First {n:,} row{s}'
            )
            title = f'Value Differences ({rows_desc}{truncated})'
            table = Table(
                title=title,
                title_style='bold'
            )
            table.add_column(index_head, justify='right')
            for i, col in enumerate(cols, 1):
                table.add_column(col, justify='right',
                                 max_width=widths[i] if truncate else None)
            for row in rows:
                table.add_row(*row)
            return table
        else:
            pass
            # find ones with most diffs (n=target-rows)
            # see which cols are covered
            # For the ones not covered
            # Find the first one
            # Get the indexes for all those
            # Show them



class DataFrameDiffs:
    def __init__(self, leftname='actual', rightname='expected',
                 verbose=False):
        self.leftname = leftname
        self.rightname = rightname
        self.field_types = {}      # keyed on name; value is FieldDiff
        self.missing = {}          # keyed on name: value is dtype
        self.extra = {}            # keyed on name: value is dtype
        self.actual_order = []     # list of field names
        self.expected_order = []   # list of field names
        self.actual_length = None
        self.expected_length = None
        self.type_matching = 'exact'
        self.verbose = verbose

        self.diff = None           # SameStructureDDiff


    @property
    def different_structure(self):
        return any((self.field_types, self.missing, self.extra,
                    self.actual_order, self.expected_order,
                    self.actual_length is not None,
                    self.expected_length is not None))

    def __str__(self):
        msgs = []
        n = len(self.rightname) - len(self.leftname)
        lpad = ' ' * (n if n > 0 else 0)
        rpad = ' ' * (-n if n < 0 else 0)
        lname = self.leftname
        rname = self.rightname

        if self.field_types:
            msgs.append('Field types differ')
            for c, v in self.field_types.items():
                msgs.append(
                    f'  {c}: {lname} {v.actual}; {rname} {v.expected}'
                )
            msgs.append('')
        elif self.verbose:
            msgs.append(
                f'All Field types: match at level {self.typematching}.'
            )

        if self.extra or self.missing:
            if self.extra:
                msgs.append(f'Unexpected fields in {lname}:')
                for c in extras:
                    msgs.append(f'  {c}')
            if self.extra:
                msgs.append(f'Fields missing from {lname}:')
                for c in missing:
                    msgs.append(f'  {c}')
        elif self.verbose:
            msgs.append('Same fields in both dataframes.')

        if self.actual_order or self.expected_order:  # could be and; should
                                                      # both be empty or full
            msgs.append('Different field orders.')
            L = ', '.join(self.actual_order)
            R = ', '.join(self.expected_order)
            msgs.append(f'  {lpad}{lname}: {L}')
            msgs.append(f'  {rpad}{rname}: {R}')
        elif self.verbose:
            msgs.append('Field order is same.')

        if self.actual_length or self.expected_length:  # could be and; should
                                                        # both be empty or full
            delta = self.actual_length - self.expected_length
            desc = 'more' if delta > 0 else 'fewer'
            delta = abs(delta)
            s = '' if delta == 1 else 's'
            msgs.append(f'{lname} has {delta:,} {desc} row{s} than {rname}')
            msgs.append(f'  {lname}: {self.actual_length}')
            msgs.append(f'  {rname}: {self.expected_length}')
        elif self.verbose:
            msgs.append('Dataframes have same length')

        if self.diff:
            msgs.append(str(self.diff))

        return'\n'.join(msgs)

def diffcmd():
    return 'fc' if os.name and os.name != 'posix' else 'diff'


def copycmd():
    return 'copy' if os.name and os.name != 'posix' else 'cp'


def df_col_pos(c, df):
    try:
        return list(df).index(c)
    except ValueError:
        return None


def py_val(x):
    try:
        return x.item()
    except AttributeError:
        return x
