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

import pandas as pd
import polars as pl

from collections import namedtuple
from itertools import chain

from rich.table import Table

from tdda.state import get_config
from tdda.utils import Dummy, nvl, error
from tdda.utils import debug
from tdda.abstractdf import (
    all_fields_except,
    is_pandas_df,
    is_polars_df,
    df_type,
    col_names,
    get_diffs_df_with_cols_and_index,
    get_diffs_df_with_cols,
    df_to_lists,
    get_sceq,
)

FieldDiff = namedtuple('FieldDiff', 'actual expected')

ColDiff = namedtuple('ColDiff', 'mask n')
DiffCounts = namedtuple('DiffCounts', 'rowdiffs n')

QualifiedTypeRE = re.compile('^([A-Za-z0-9]+)+.*$')

DEFAULT_DIFF_ROWS = 10

ESC_MAP = str.maketrans({
    '\\': r'\\',
    ' ': r'\ ',
    "'": r'\'',
})
TDDA_DIFF = 'tdda diff'

class FailureDiffs:
    """
    Container for Information about comparison failures.

    Args:

        failures: Number of failures.
                  Can also be accessed (read) as .count.

        diffs: Diffs object, with descriptions of failures
               Can also be accessed (read) as .descriptions.

    Failures diffs objects have a boolean value of True if there
    are failures (differences) and False if not.
    """
    def __init__(self, failures, diffs):
         self.failures = failures
         self.diffs = diffs

    @property
    def count(self):
        return self.failures

    @property
    def description(self):
        return self.diffs

    def __str__(self):
        msg = '\n'.join(self.diffs)
        return f'Number of Differences: {self.failures}\n{msg}'

    def __bool__(self):
        return self.failures > 0

    def __iter__(self):
        """Make iterable to allow it to be assigned to a pair (2-tuple)"""
        return (x for x in (self.failures, self.diffs))

    def __eq__(self, other):
        return self.failures == other.failures and self.diffs == other.diffs

    @property
    def pair(self):
        return (self.failures, self.diffs)

    def details(self, df, ref_df):
        dfd = getattr(self.diffs, 'dfd', None)
        diff = getattr(dfd, 'diff', None)
        return diff.details(df, ref_df) if diff else None


class DiffState:
    """
    Container for DataFrame differences state
    """
    def __init__(self, actual_nrows, ref_nrows, common_cols,
                 wrong_types=None, extra_cols=None, missing_cols=None,
                 out_of_order=False, n_diff_values=0):
        self.actual_nrows = actual_nrows
        self.ref_nrows = ref_nrows
        self.common_cols = common_cols
        self.wrong_types = nvl(wrong_types, [])  # where type checking applied
        self.extra_cols = nvl(extra_cols, [])    # where specified
        self.missing_cols = nvl(missing_cols, [])  # where specified
        self.out_of_order = out_of_order         # if specified
        self.n_diff_values = n_diff_values       # Only when not 'quick'
                                                 # if there are structure
                                                 # differences

    @property
    def same_nrows(self):
        return self.actual_nrows == self.ref_nrows

    @property
    def diff_nrows(self):
        return self.actual_nrows != self.ref_nrows

    @property
    def different(self):
        return bool(
            self.diff_nrows
            or self.n_diff_values
            or self.wrong_types
            or self.extra_cols
            or self.missing_cols
            or self.out_of_order
        )

    @property
    def same(self):
        return not self.different

    @property
    def different_ignoring_types(self):
        return bool(
            self.diff_nrows
            or self.n_diff_values
            or self.extra_cols
            or self.missing_cols
            or self.out_of_order
        )

    @property
    def same_ignoring_types(self):
        return not self.different_ignoring_types



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

    def check_dataframe(
        self,
        df,
        ref_df,
        actual_path=None,
        expected_path=None,
        check_data=None,
        check_types=None,
        check_order=None,
        check_extra_cols=True,
        sortby=None,
        condition=None,
        precision=None,
        msgs=None,
        type_matching=None,
        create_temporaries=True,
        fuzzy_nulls=False,
        engine=None,
        backend=None,
        key=None,
        quick=True
    ):
        """
        Compare two DataFrames.
        Details of dataframe differences abstracted,
        mostly with static methods on subclasses.

        Args:

            *df*
                            Actual dataframe
            *ref_df*
                            Expected dataframe
            *actual_path*
                            Path for file where actual dataframe originated,
                            used for error messages.
            *expected_path*
                            Path for file where expected dataframe originated,
                            used for error messages.
            *check_types*
                            Option to specify fields to use to compare types.
            *check_order*
                            Option to specify fields to use to compare field
                            order.
            *check_data*
                            Option to specify fields to use to compare cell
                            values.
            *check_extra_cols*
                            If set to False, columns present in df but not
                            ref_df are ignored
            *sortby*
                            Option to specify fields to sort by before
                            comparing.
            *condition*
                            Filter to be applied to datasets before comparing.
                            It can be ``None``, or can be a function that takes
                            a DataFrame as its single parameter and returns
                            a vector of booleans (to specify which rows should
                            be compared).
            *precision*
                            Number of decimal places to compare float values.
            *msgs*
                            Optional Diffs object.

            *type_matching* 'strict', 'medium', 'permissive'/'loose'.
                            None is same as strict.

            *create_temporaries*  If True (the default), if the check fails,
                                  the actual result in the dataframe will be
                                  written to disk (usually as parquet).

            *fuzzy_nulls* Ordinarily, nulls and empty strings are
                          considered not equal (fuzzy_nulls=False
                          or any falsy value).

                          If set to 'object', where either column
                          in a comparison is of type object, and the
                          other is object or string, those
                          nulls will be mapped to the empty string
                          on both sides so that '' == None (in effect).

                          If set to True (or 1), this will also be
                          done for string columns as well as object columns.

            *quick*  If True (the default), the main goal of the function
                     is quickly to identify whether the actual and
                     references DataFrames are the same. In thus case,
                     information about differences is returned, but once
                     (for example) a column is found to have the wrong
                     type, or to be missing, unexpected, or out of place,
                     the function returns with no more comparison.

                     When quick is False, the function tries a little
                     harder to find detailed differences even when
                     types are not exactly the same etc.

            *engine* preferred engine if data frames use different engines

            *key*    key field (or list of fields) to use as join key
                     If this is not provided, the rows are assumed
                     to be aligned.

        Returns:

            A FailureDiffs named tuple with:
              .failures     the number of failures
              .diffs        a Diffs object with information about
                            the failures
        All of the 'Option' parameters can be of any of the following:

            - ``None`` (to apply that kind of comparison to all fields)
            - ``False`` (to skip that kind of comparison completely)
            - a list of field names
            - a function taking a dataframe as its single parameter, and
              returning a list of field names to use.
        """
        diffs = msgs  # better name

        self.actual_path = actual_path
        self.expected_path = expected_path

        type_matching = type_matching or 'strict'
        diffs = nvl(diffs, Diffs())
        self.precision = nvl(precision, 7)
        self.fuzzy_nulls = fuzzy_nulls
        if bool(fuzzy_nulls) and not fuzzy_nulls in (True, 'object'):
            error(f'fuzzy_nulls value {fuzzy_nulls} unknown. '
                  ' Should be True, False or "object"')

        check_types = self.resolve_option_flag(check_types, ref_df)
        check_extra_cols = self.resolve_option_flag(check_extra_cols, df)

        df_names = col_names(df)
        rf_names = col_names(ref_df)
        common_cols = list(set(df_names).intersection(set(rf_names)))

        # Check whether they have the same number of records
        state = DiffState(len(df), len(ref_df), common_cols)

        # 1. Convert category fields to string fields

        df = self._replace_cats(df)
        ref_df = self._replace_cats(ref_df)

        # 2. Make initial set of missing columns

        missing_cols = set(rf_names) - set(df_names)

        # 3. Check types of fields, where type checking is used.
        #    Also mark any fields not present in df that are
        #    supposed to be type checked as missing.

        for c in check_types:
            if c not in col_names(df):
                missing_cols.add(c)
            elif not (
                self._types_match(df[c].dtype, ref_df[c].dtype, type_matching)
            ):
                state.wrong_types.append((c, df[c].dtype, ref_df[c].dtype))

        # 4. Sort the missing columns
        state.missing_cols = sorted(missing_cols)

        # 5. Find any cols in df not in ref_df
        if check_extra_cols:
            state.extra_cols = sorted(set(df_names) - set(rf_names))

        # 6. If checking order, do it now
        if check_order != False and not missing_cols:
            check_order = self.resolve_option_flag(check_order, ref_df)
            order1 = [c for c in df_names if c in check_order]
            order2 = [c for c in rf_names if c in check_order and c in df_names]
            state.out_of_order = order1 != order2

        if not state.same:
            # Log problems with the column structure
            self.different_column_structure(diffs)
            self.missing_columns_detected(diffs, state.missing_cols, ref_df)
            self.extra_columns_found(diffs, state.extra_cols, df)
            if state.wrong_types:
                for c, dtype, ref_dtype in state.wrong_types:
                    self.field_types_differ(diffs, c, dtype, ref_dtype)
            if state.out_of_order:
                self.different_column_orders(diffs, df, ref_df)

        # Now move onto records.
        # If sortby is specified, both DataFrames need to be
        # sorted.
        #
        # Could also do a join here.
        #
        if sortby:
            sortby = self.resolve_option_flag(sortby, ref_df)
            if any([c in sortby for c in state.missing_cols]):
                self.info('Cannot sort on missing columns')
            else:
                self._sort_df(df, sortby)
                self._sort_df(ref_df, sortby)

        # If a condition is specifed, apply it to both DataFrames
        if condition:
            df = self._apply_condition(df, condition)
            ref_df = self._apply_condition(ref_df, condition)
            state.actual_nrows = len(df)
            state.ref_nrows = len(ref_df)

        if state.diff_nrows:
            # Log if not
            self.different_numbers_of_rows(diffs, state.actual_nrows,
                                           state.ref_nrows)

        cols = state.common_cols
        if not quick or state.same_ignoring_types:
            check_data = self.resolve_option_flag(check_data, ref_df)
            if check_data:
                cols = [c for c in check_data if c in state.common_cols]
                state.n_diff_values = self.same_structure_ddiff(df[cols],
                                                                ref_df[cols],
                                                                diffs,
                                                                key=key)
        switches = []
        nc = len(cols)
        nL = len(list(df))
        if check_data and nc < nL:
            if nc < nL - nc:
                switches.append('--fields \'%s\'' % escaped_list(cols))
            else:
                rest = [f for f in df_names
                        if f in set(df_names) - set(cols)]
                switches.append('--xfields \'%s\'' % escaped_list(rest))
        config = get_config
        switches.append(f'--{type_matching}')
        if not state.same and create_temporaries:
            self.write_temporaries(df, ref_df, diffs, switches=switches)
        return FailureDiffs(failures=0 if state.same else 1, diffs=diffs)


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
                     custom_diff_cmd='', switches=None):
        qualifier = '' if not qualifier else (qualifier + ' ')
        f = lambda p: os.path.normpath(os.path.abspath(p))
        if os.path.exists(expected):
#            if binary:
#                return None
#            else:
                msg = 'Compare %swith:\n    %s %s %s%s\n'
                cmd = custom_diff_cmd or diffcmd()
                suffix = ' '.join([''] + switches) if switches else ''
        else:
            suffix = ''
            msg = 'Initialize %sfrom actual content with:\n    %s %s %s%s'
            cmd = copycmd()
        return msg % (qualifier, cmd, f(actual), f(expected), suffix)

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
        diffs.dfd.field_types[c] = FieldDiff(actual_dtype, ref_dtype)

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
                diffs.dfd.extra[c] = df[c].dtype

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
                diffs.dfd.extra[c] = ref_df[c].dtype

    def different_column_structure(self, diffs):
            self.failure(
                diffs,
                'Data frames have different column structure.',
            )

    def different_column_orders(self, diffs, df, ref_df):
        self.info(diffs,
           'Different column ordering between data frames.\n'
           f'  Actual ordering: {" ".join(col_names(df))}\n'
           f'Expected ordering: {" ".join(col_names(ref_df))}')
        diffs.dfd.actual_order = col_names(df)
        diffs.dfd.expected_order = col_names(ref_df)

    def different_numbers_of_rows(self, diffs, na, nr):
            self.failure(
                diffs, 'Data frames have different numbers of rows.',
            )
            self.info(
                diffs, f'Actual records: {na:,}; Expected records: {nr:,}'
            )
            same = False

    @classmethod
    def resolve_option_flag(self, flag, df):
        """
        Method to resolve an option flag, which may be any of:

           ``None`` or ``True``:
                    use all columns in the dataframe
           ``False``:
                    use no columns
           list of columns
                    use these columns
           function returning a list of columns
        """
        if flag is None or flag is True:
            return col_names(df)
        elif flag is False:
            return []
        elif hasattr(flag, '__call__'):
            return flag(df)
        else:
            return flag

    def _write_reference_dataframe(
        self, df, path, writer=None, **kwargs
    ):
        """
        Function for saving a Pandas DataFrame to a CSV file.
        Used when regenerating DataFrame reference results.
        """
        ext = os.path.splitext(path)[1].lower()
        if ext == '.parquet':
            self.write_parquet(df, path)
        else:
            self.write_csv(df, path, writer, **kwargs)
        if self.verbose:
            print(f'*** Written {path}.')

    def write_temporaries(self, actual, expected, msgs, switches=None):
        differ = tdda_differ = None
        actual_path = self.actual_path
        expected_path = self.expected_path
        if actual_path and expected_path:
            commonname = os.path.split(actual_path)[1]
            differ = self.compare_with(actual_path, expected_path)
            tdda_differ = self.compare_with(actual_path, expected_path,
                                            custom_diff_cmd=TDDA_DIFF,
                                            switches=switches)
        else:
            if actual_path:
                commonname = os.path.split(actual_path)[1]
            elif expected_path:
                commonname = os.path.split(expected_path)[1]
            else:
                commonname = self.get_temp_filename()
            if expected is not None and not expected_path:
                # no expected file, so write it
                tmpExpectedPath = os.path.join(
                    self.tmp_dir, 'expected-' + commonname
                )
                expected_path = tmpExpectedPath
                self._write_reference_dataframe(expected, tmpExpectedPath)
                if actual_path:
                    differ = self.compare_with(actual_path, tmpExpectedPath)
                    tdda_differ = self.compare_with(
                        actual_path, tmpExpectedPath,
                        custom_diff_cmd=TDDA_DIFF,
                        switches=switches)
            if actual is not None and not actual_path:
                # no actual file, so write it
                tmpActualPath = os.path.join(
                    self.tmp_dir, 'actual-' + commonname
                )
                self._write_reference_dataframe(actual, tmpActualPath)
                if expected_path:
                    differ = self.compare_with(tmpActualPath, expected_path)
                    tdda_differ = self.compare_with(
                        tmpActualPath, expected_path,
                        custom_diff_cmd=TDDA_DIFF, switches=switches)

        if differ:
            self.info(msgs, differ)
        if tdda_differ:
            self.info(msgs, tdda_differ)

    def failure(self, msgs, s):
        """
        Add a failure to the list of messages, and also display it immediately
        if verbose is set. Also provide information about the two files
        involved.
        """
        if self.actual_path and self.expected_path:
            self.info(
                msgs,
                self.compare_with(
                    os.path.normpath(self.actual_path), self.expected_path
                ),
            )
        elif self.expected_path:
            self.info(msgs, 'Expected file %s' % self.expected_path)
        elif self.actual_path:
            self.info(msgs, 'Actual file %s'
                          % os.path.normpath(self.actual_path))
        self.info(msgs, s)

    def check_serialized_dataframe(
        self,
        actual_path,
        expected_path,
        loader=None,
        check_data=None,
        check_types=None,
        check_order=None,
        condition=None,
        sortby=None,
        precision=6,
        type_matching=None,
        msgs=None,
        **kwargs,
    ):
        r"""
        Checks two data frames on disk files are the same,
        by comparing them as dataframes.

        Args:

            *actual_path*
                            Pathname for actual CSV/Parquet file.
            *expected_path*
                            Pathname for expected CSV/Parquet file.
            *loader*
                            A function to use to read a CSV file to obtain
                            a pandas dataframe. If None, then a default CSV
                            loader is used, which takes the same parameters
                            as the standard pandas pd.read_csv() function.

            *check_data*
                            Option to specify fields to use to compare cell
                            values.
            *check_types*
                            Option to specify fields to use to compare types.

            *check_order*
                            Option to specify fields to use to compare field
                            order.

            *condition*
                            Filter to be applied to datasets before comparing.
                            It can be ``None``, or can be a function that takes
                            a DataFrame as its single parameter and returns
                            a vector of booleans (to specify which rows should
                            be compared).
            *sortby*
                            Option to specify fields to sort by before
                            comparing.
            *precision*
                            Number of decimal places to compare float values.
            *msgs*
                            Optional Diffs object.

            *\*\*kwargs*
                            Any additional named parameters are passed straight
                            through to the loader function.

        The other parameters are the same as those used by
        :py:mod:`check_dataframe`.
        Returns a tuple (failures, msgs), containing the number of failures,
        and a Diffs object containing error messages.
        """
        ref_df = self.load_serialized_dataframe(
            expected_path, loader=loader, **kwargs
        )
        df = self.load_serialized_dataframe(
            actual_path, loader=loader, **kwargs
        )
        return self.check_dataframe(
            df,
            ref_df,
            actual_path=actual_path,
            expected_path=expected_path,
            check_data=check_data,
            check_types=check_types,
            check_order=check_order,
            condition=condition,
            sortby=sortby,
            precision=precision,
            type_matching=type_matching,
            msgs=msgs,
        )

    check_csv_file = check_serialized_dataframe

    def check_serialized_dataframes(
        self,
        actual_paths,
        expected_paths,
        check_data=None,
        check_types=None,
        check_order=None,
        condition=None,
        sortby=None,
        type_matching=None,
        msgs=None,
        **kwargs,
    ):
        r"""
        Wrapper around the check_serialized_dataframes() method,
        used to compare collections of serialized data frames on disk
        against reference counterparts

            *actual_paths*
                            List of pathnames for actual serialized data frames
            *expected_paths*
                            List of pathnames for expected serialized
                            data frames.
            *loader*
                            A function to use to read a CSV file to obtain
                            a pandas dataframe. If None, then a default CSV
                            loader is used, which takes the same parameters
                            as the standard pandas pd.read_csv() function.
            *\*\*kwargs*
                            Any additional named parameters are passed straight
                            through to the loader function.

            *check_data*
                            Option to specify fields to use to compare cell
                            values.
            *check_types*
                            Option to specify fields to use to compare types.

            *check_order*
                            Option to specify fields to use to compare field
                            order.

            *condition*
                            Filter to be applied to datasets before comparing.
                            It can be ``None``, or can be a function that takes
                            a DataFrame as its single parameter and returns
                            a vector of booleans (to specify which rows should
                            be compared).
            *sortby*
                            Option to specify fields to sort by before
                            comparing.
            *precision*
                            Number of decimal places to compare float values.
            *msgs*
                            Optional Diffs object.

        The other parameters are the same as those used by
        :py:mod:`check_dataframe`.
        Returns a tuple (failures, msgs), containing the number of failures,
        and a list of error messages.

        Returns a tuple (failures, msgs), containing the number of failures,
        and a Diffs object containing error messages.

        Note that this function compares ALL of the pairs of actual/expected
        files, and if there are any differences, then the number of failures
        returned reflects the total number of differences found across all
        of the files, and the msgs returned contains the error messages
        accumulated across all of those comparisons. In other words, it
        doesn't stop as soon as it hits the first error, it continues through
        right to the end.
        """
        if msgs is None:
            msgs = Diffs()
        failures = 0
        for actual_path, expected_path in zip(actual_paths, expected_paths):
            try:
                r = self.check_serialized_dataframe(
                    actual_path,
                    expected_path,
                    check_data=check_data,
                    check_types=check_types,
                    check_order=check_order,
                    sortby=sortby,
                    type_matching=type_matching,
                    condition=condition,
                    msgs=msgs,
                    **kwargs,
                )
                (n, msgs) = r
                failures += n
            except Exception as e:
                self.info(
                    msgs,
                    'Error comparing %s and %s (%s %s)'
                    % (
                        os.path.normpath(actual_path),
                        expected_path,
                        e.__class__.__name__,
                        str(e),
                    ),
                )
                failures += 1
        return (failures, msgs)

    check_csv_files = check_serialized_dataframes

    def load_csv(self, csvfile, loader=None, **kwargs):
        """
        Function for constructing a pandas dataframe from a CSV file.
        """
        # if not os.path.exists(csvfile):
        #     parts = csvfile.split(':')
        #     if csvfile.endswith(':'):  # find metadata
        #         return self.csv_to_dataframe(csvfile[:-1], find_md=True)
        #     elif len(parts) == 2:  # path + md_path
        #         path, md_path = parts
        #         if os.path.exists(path):
        #             return self.csv_to_dataframe(path, md_path=md_path)
        # Now handled by csv_to_pandas
        if loader is None:
            loader = self.default_csv_loader
        return loader(csvfile, **kwargs)

    ####


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

    When the objects are dataframes, the .dfd field contains a DataFrameDiffs
    object with structured information on the dataframe differences.
    """
    def __init__(self, lines=None):
        self.lines = lines or []
        self.reconstructions = []
        self.dfd = DataFrameDiffs()  # only used for DataFrames

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

    def __bool__(self):
        return bool(self.lines)

    @property
    def ndiffs(self):
        return len(self.lines)

    __str__ = message


class SameStructureDDiff:
    """
    Container for information about differences betwee data frames
    with the same structure.
    """
    def __init__(self, shape, diff_df, row_counts, n_vals, n_cols, n_rows,
                 key=None, colour=None):
        self.shape = shape
        self.n_diff_values = n_vals
        self.n_diff_cols = n_cols
        self.n_diff_rows = n_rows
        self.key = key
        self.diff_df = diff_df             # keyed on common column name
        self.row_diff_counts = row_counts  # count of diffs on each row
        self.config = get_config()

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

            index_header = [] if self.key else ['row']

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
        eq = get_sceq(df)
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
                lstr = [
                    C.common(left) if eq(left, right)
                                   else C.left_diff(left, prefix)
                    for (left, right) in zip(l_vals, r_vals)
                ]
                rstr = [
                    C.common(right) if eq(left, right)
                                    else C.right_diff(right, prefix)
                    for (left, right) in zip(l_vals, r_vals)
                ]
                plstr = [
                    C.left_annotated(left, prefix) for left in l_vals
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
            index_head = '' if self.key else 'row'
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
        self.type_matching = 'strict'
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
        return col_names(df).index(c)
    except ValueError:
        return None


def py_val(x):
    try:
        v = x.item()
    except AttributeError:
        v = x
    return None if pd.isna(v) else v


def pd_eq(left, right):
    if pd.isna(left):
        if pd.isna(right):
            return True
    elif pd.isna(right):
        return False
    return left == right


def escape(name):
    """Escape column name etc. for passing through shell in single quotes"""
    return name.translate(ESC_MAP)


def escaped_list(items):
    """Escape column name etc. for passing through shell in single quotes"""
    return ','.join(item.translate(ESC_MAP) for item in items)


def type_header(col, suffix=''):
    t = str(col.dtype)
    m = re.match(QualifiedTypeRE, t)
    if m:
        t = m.group(1)
    return f'{t}{suffix}'


def create_row_diffs_mask(masks):
    """
    Combine all column diff masks efficiently for mask
    showing all rows with differences.

    Args:
        masks: list of bool columns indicating column difference

    Return:
        combined mask
    """
    while len(masks) > 1:
        last = [masks[-1]] if len(masks) % 2 == 1 else []
        masks = [
            (masks[2 * i] | masks[2 * i + 1])
            for i in range(len(masks) // 2)
        ] + last
    return masks[0]


def valid_level(level):
    if level == 'permissive':
        return 'loose'
    elif level is None:
        return 'strict'
    if not (level is None or level in ('strict', 'medium', 'loose')):
        raise ValueError(f'Type match level must be one of strict, medium, '
                         f'or loose(/permissive), not {level}')
    return level


