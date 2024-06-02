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
import sys
import tempfile

from collections import namedtuple

FailureDiffs = namedtuple('FailureDiffs', 'failures diffs')

FieldDiff = namedtuple('FieldDiff', 'actual expected')

ColDiff = namedtuple('ColDiff', 'mask n')


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
        as python's builtin print function.
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
        if os.path.exists(expected):
            if binary:
                return None
            else:
                msg = 'Compare %swith:\n    %s %s %s\n'
                cmd = custom_diff_cmd or diffcmd()
        else:
            msg = 'Initialize %sfrom actual content with:\n    %s %s %s'
            cmd = copycmd()
        return msg % (qualifier, cmd, actual, expected)

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



class Diffs(object):
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
    def __init__(self, diff_masks, row_counts, n_vals, n_cols, n_rows):
        self.n_diff_values = n_vals
        self.n_diff_cols = n_cols
        self.n_diff_rows = n_rows
        self.diff_masks = diff_masks      # keyed on common column name
        self.row_diff_counts = row_counts # mask for rows with any differences



class DataFrameDiffs:
    def __init__(self):
        self.field_types = {}      # keyed on name; value is FieldDiff
        self.missing = {}          # keyed on name: value is dtype
        self.extra = {}            # keyed on name: value is dtype
        self.actual_order = []     # list of field names
        self.expected_order = []   # list of field names
        self.actual_length = None
        self.expected_length = None

        self.diff = None           # SameStructureDDiff


    @property
    def different_structure(self):
        return any((self.field_types, self.missing, self.extra,
                    self.actual_order, self.expected_order,
                    self.actual_length is not None,
                    self.expected_length is not None))

    def __str__(self):
        s = ',\n'.join(f'    {k}: {v}' for k, v in self.__dict__.items())
        return f'DataFrameDiffs(\n{s}\n)'


def diffcmd():
    return 'fc' if os.name and os.name != 'posix' else 'diff'


def copycmd():
    return 'copy' if os.name and os.name != 'posix' else 'cp'


def df_col_pos(c, df):
    try:
        return list(df).index(c)
    except ValueError:
        return None


