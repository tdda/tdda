# -*- coding: utf-8 -*-

"""
checkpandas.py: comparison mechanism for pandas dataframes (and CSV files)

Source repository: http://github.com/tdda/tdda

License: MIT

Copyright (c) Stochastic Solutions Limited 2016-2017
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import csv
import os

try:
    import pandas as pd
    import numpy as np
except ImportError:
    pd = None


class PandasNotImplemented(object):
    """
    Null implementation of PandasComparison, used when pandas not available.
    """
    def __getattr__(self, name):
        return lambda *args, **kwargs: self.method(name, *args, **kwargs)

    def method(self, name, *args, **kwargs):
        raise NotImplementedError('%s: Pandas not available.' % name)


class PandasComparison(object):
    """
    Comparison class for pandas dataframes (and CSV files).
    """

    def __new__(cls, *args, **kwargs):
        if pd is None:
            return PandasNotImplemented()
        return super(PandasComparison, cls).__new__(cls)

    def __init__(self, print_fn=None, verbose=True):
        """
        Constructor for an instance of the PandasComparison class.

        The optional print_fn parameter is a function to be used to
        display information while comparison operations are running.
        If specified, it should be a function with the same signature
        as python's builtin (__future__) print function.
        """
        self.print_fn = print_fn
        self.verbose = verbose

    def check_dataframe(self, df, ref_df, actual_path=None, expected_path=None,
                        check_data=None, check_types=None, check_order=None,
                        check_extra_cols=None, sortby=None,
                        condition=None, precision=None, msgs=None):
        """
        Compare two pandas dataframes.

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
                            Option to specify fields to use to compare typees.
            *check_order*
                            Option to specify fields to use to compare field
                            order.
            *check_data*
                            Option to specify fields to use to compare cell
                            values.
            *check_extra_cols*
                            Option to specify fields in the actual dataset
                            to use to check that there are no unexpected
                            extra columns.
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
                            List of strings

        Returns a tuple (failures, msgs), containing the number of failures,
        and a list of error messages.

        the comparison 'Option' flags can be of any of the following:

            - ``None`` (to apply that kind of comparison to all fields)
            - ``False`` (to skip that kind of comparison completely)
            - a list of field names
            - a function taking a dataframe as its single parameter, and
              returning a list of field names to use.
        """

        same = True
        if msgs is None:
            msgs = []

        if precision is None:
            precision = 6

        check_types = resolve_option_flag(check_types, ref_df)
        check_extra_cols = resolve_option_flag(check_extra_cols, df)

        missing_cols = []
        extra_cols = []
        wrong_types = []
        wrong_ordering = False
        for c in check_types:
            if c not in list(df):
                missing_cols.append(c)
            elif df[c].dtype != ref_df[c].dtype:
                wrong_types.append((c, df[c].dtype, ref_df[c].dtype))
        if check_extra_cols:
        # todo: shouldn't check_extra_cols be a boolean?
        #       ... and set(check_extra_cols) be set(list(df))
            extra_cols = set(check_extra_cols) - set(list(ref_df))
        if check_order != False and not missing_cols:
            check_order = resolve_option_flag(check_order, ref_df)
            c1 = [c for c in list(df) if c in check_order]
            c2 = [c for c in list(ref_df) if c in check_order]
            wrong_ordering = (list(df[c1]) != list(ref_df[c2]))
        same = not any((missing_cols, extra_cols, wrong_types, wrong_ordering))

        if not same:
            self.failure(msgs, 'Column check failed.',
                         actual_path, expected_path)
            if missing_cols:
                self.info(msgs, 'Missing columns: %s' % missing_cols)
            if extra_cols:
                self.info(msgs, 'Extra columns: %s' % list(extra_cols))
            if wrong_types:
                for (c, dtype, ref_dtype) in wrong_types:
                    self.info(msgs,
                              'Wrong column type %s (%s, expected %s)'
                              % (c, dtype, ref_dtype))
            if wrong_ordering:
                c1 = [c for c in list(df) if c in check_types]
                c2 = [c for c in list(ref_df) if c in check_types]
                ordermsg = 'mysterious difference, they appear to be the same!'
                for i, c in enumerate(c1):
                    if i >= len(c2):
                        ordermsg = 'not enough columns'
                        break
                    elif c != c2[i]:
                        ordermsg = ('found %s, expected %s' % (c, c2[i]))
                        break
                self.info(msgs, 'Wrong column ordering: %s' % ordermsg)

        if sortby:
            sortby = resolve_option_flag(sortby, ref_df)
            if any([c in sortby for c in missing_cols]):
                self.info('Cannot sort on missing columns')
            else:
                df.sort_values(sortby, inplace=True)
                ref_df.sort_values(sortby, inplace=True)

        if condition:
            df = df[condition(df)].reindex()
            ref_df = ref_df[condition(ref_df)].reindex()

        same = len(df) == len(ref_df)
        if not same:
            self.failure(msgs, 'Length check failed.',
                         actual_path, expected_path)
            self.info(msgs, 'Found %d records, expected %d'
                            % (len(df), len(ref_df)))
        else:
            check_data = resolve_option_flag(check_data, ref_df)
            if check_data:
                check_data = [c for c in check_data if c not in missing_cols]
                df = df[check_data]
                ref_df = ref_df[check_data]
                if precision is not None:
                    rounded = df.round(precision).reset_index(drop=True)
                    ref_rounded = (ref_df.round(precision)
                                         .reset_index(drop=True))
                else:
                    rounded = df
                    ref_rounded = ref_df
                same = rounded.equals(ref_rounded)
                if not same:
                    self.failure(msgs, 'Contents check failed.',
                                 actual_path, expected_path)
                    for c in list(ref_rounded):
                        if not rounded[c].equals(ref_rounded[c]):
                            diffs = self.differences(c, rounded[c],
                                                     ref_rounded[c], precision)
                            self.info(msgs, 'Column values differ: %s' % c)
                            self.info(msgs, diffs)

        same = same and not any((missing_cols, extra_cols, wrong_types,
                                 wrong_ordering))
        return (0 if same else 1, msgs)

    def differences(self, name, values, ref_values, precision):
        """
        Returns a short summary of where values differ, for two columns.
        """
        for i, val in enumerate(values):
            refval = ref_values[i]
            if val != refval and not (pd.isnull(val) and pd.isnull(refval)):
                stop = self.ndifferences(values, ref_values, i)
                summary_vals = self.sample_format(values, i, stop, precision)
                summary_ref_vals = self.sample_format(ref_values, i, stop,
                                                      precision)
                return 'From row %d: [%s] != [%s]' % (i+1,
                                                      summary_vals,
                                                      summary_ref_vals)
        if values.dtype != ref_values.dtype:
            return 'Different types'
        else:
            return 'But mysteriously appear to be identical!'

    def sample(self, values, start, stop):
        return [None if pd.isnull(values[i]) else values[i]
                for i in range(start, stop)]

    def sample_format(self, values, start, stop, precision):
        s = self.sample(values, start, stop)
        r = ', '.join(['null' if pd.isnull(v)
                       else str('%d' % v)
                              if type(v) in (np.int, np.int32, np.int64)
                       else str('%.*f' % (precision, v))
                              if type(v) in (np.float, np.float32, np.float64)
                       else str('"%s"' % v) if values.dtype == object
                       else str(v)
                       for v in s])
        if len(s) < stop - start:
            r += ' ...'
        return r

    def ndifferences(self, values1, values2, start, limit=10):
        stop = min(start+limit, len(values1))
        for i in range(start, stop):
            v1 = values1[i]
            v2 = values2[i]
            if v1 == v2 or (pd.isnull(v1) and pd.isnull(v2)):
                return i
        return stop

    def check_csv_file(self, actual_path, expected_path, loader=None,
                       check_data=None, check_types=None, check_order=None,
                       condition=None, sortby=None, precision=6, msgs=None,
                       **kwargs):
        """
        Checks two CSV files are the same, by comparing them as dataframes.

            *actual_path*
                            Pathname for actual CSV file.
            *expected_path*
                            Pathname for expected CSV file.
            *loader*
                            A function to use to read a CSV file to obtain
                            a pandas dataframe. If None, then a default CSV
                            loader is used, which takes the same parameters
                            as the standard pandas pd.read_csv() function.
            *\*\*kwargs*
                            Any additional named parameters are passed straight
                            through to the loader function.

        The other parameters are the same as those used by
        :py:mod:`check_dataframe`.
        Returns a tuple (failures, msgs), containing the number of failures,
        and a list of error messages.
        """

        ref_df = self.load_csv(expected_path, loader=loader, **kwargs)
        df = self.load_csv(actual_path, loader=loader, **kwargs)
        return self.check_dataframe(df, ref_df,
                                    actual_path=actual_path,
                                    expected_path=expected_path,
                                    check_data=check_data,
                                    check_types=check_types,
                                    check_order=check_order,
                                    condition=condition, sortby=sortby,
                                    precision=precision,
                                    msgs=msgs)

    def check_csv_files(self, actual_paths, expected_paths,
                        check_data=None, check_types=None, check_order=None,
                        condition=None, sortby=None, msgs=None, **kwargs):
        """
        Wrapper around the check_csv_file() method, used to compare
        collections of actual and expected CSV files.

            *actual_paths*
                            List of pathnames for actual CSV file.
            *expected_paths*
                            List of pathnames for expected CSV file.
            *loader*
                            A function to use to read a CSV file to obtain
                            a pandas dataframe. If None, then a default CSV
                            loader is used, which takes the same parameters
                            as the standard pandas pd.read_csv() function.
            *\*\*kwargs*
                            Any additional named parameters are passed straight
                            through to the loader function.

        The other parameters are the same as those used by
        :py:mod:`check_dataframe`.
        Returns a tuple (failures, msgs), containing the number of failures,
        and a list of error messages.

        Returns a tuple (failures, msgs), containing the number of failures,
        and a list of error messages.

        Note that this function compares ALL of the pairs of actual/expected
        files, and if there are any differences, then the number of failures
        returned reflects the total number of differences found across all
        of the files, and the msgs returned contains the error messages
        accumulated across all of those comparisons. In other words, it
        doesn't stop as soon as it hits the first error, it continues through
        right to the end.
        """
        failures = 0
        for (actual_path, expected_path) in zip(actual_paths, expected_paths):
            try:
                r = self.check_csv_file(actual_path, expected_path,
                                        check_data=check_data,
                                        check_types=check_types,
                                        check_order=check_order,
                                        sortby=sortby,
                                        condition=condition, msgs=msgs,
                                        **kwargs)
                (n, msgs) = r
                failures += n
            except Exception as e:
                self.info(msgs, 'Error comparing %s and %s (%s %s)'
                                % (os.path.normpath(actual_path),
                                   expected_path,
                                   e.__class__.__name__, str(e)))
                failures += 1
        return (failures, msgs)

    def info(self, msgs, s):
        """
        Add an item to the list of messages, and also display it immediately
        if verbose is set.
        """
        msgs.append(s)
        if self.verbose and self.print_fn:
            self.print_fn(s)

    def failure(self, msgs, s, actual_path, expected_path):
        """
        Add a failure to the list of messages, and also display it immediately
        if verbose is set. Also provide information about the two files
        involved.
        """
        diffcmd = 'fc' if os.name and os.name != 'posix' else 'diff'
        if actual_path and expected_path:
            self.info(msgs, 'Compare with "%s %s %s".'
                            % (diffcmd, os.path.normpath(actual_path),
                               expected_path))
        elif expected_path:
            self.info(msgs, 'Expected file %s' % expected_path)
        elif actual_path:
            self.info(msgs, 'Actual file %s' % os.path.normpath(actual_path))
        self.info(msgs, s)

    def load_csv(self, csvfile, loader=None, **kwargs):
        """
        Function for constructing a pandas dataframe from a CSV file.
        """
        if loader is None:
            loader = default_csv_loader
        return loader(csvfile, **kwargs)


def default_csv_loader(csvfile, **kwargs):
    """
    Default function for reading a csv file.

    Wrapper around the standard pandas pd.read_csv() function, but with
    slightly different defaults:

        - index_col             is ``None``
        - infer_datetime_format is ``True``
        - quotechar             is ``"``
        - quoting               is :py:const:`csv.QUOTE_MINIMAL`
        - escapechar            is ``\\`` (backslash)
        - na_values             are the empty string, ``"NaN"``, and ``"NULL"``
        - keep_default_na       is ``False``
    """
    options = {
        'index_col': None,
        'infer_datetime_format': True,
        'quotechar': '"',
        'quoting': csv.QUOTE_MINIMAL,
        'escapechar': '\\',
        'na_values': ['', 'NaN', 'NULL'],
        'keep_default_na': False,
    }
    options.update(kwargs)
    return pd.read_csv(csvfile, **options)


def resolve_option_flag(flag, df):
    """
    Method to resolve an option flag, which may be any of:

       ``None`` or ``True``:
                use all columns in the dataframe
       ``None``:
                use no columns
       list of columns
                use these columns
       function returning a list of columns
    """
    if flag is None or flag is True:
        return list(df)
    elif flag is False:
        return []
    elif hasattr(flag, '__call__'):
         return flag(df)
    else:
        return flag

