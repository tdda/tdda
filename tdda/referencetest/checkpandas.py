"""
checkpandas.py: comparison mechanism for pandas dataframes (and CSV files)

Source repository: http://github.com/tdda/tdda

License: MIT

Copyright (c) Stochastic Solutions Limited 2016-2024
"""

import csv
import os
import sys

from collections import OrderedDict, namedtuple

from tdda.referencetest.basecomparison import (
    BaseComparison,
    Diffs,
    FailureDiffs,
    ColDiff,
    DiffCounts,
    SameStructureDDiff
)
from tdda.referencetest.pddates import infer_date_format
from tdda.pd.utils import is_string_col
from tdda.utils import nvl


import pandas as pd
import numpy as np



# TDDA_DIFF = 'tdda diff'
TDDA_DIFF = 'diff'


class PandasComparison(BaseComparison):
    """
    Comparison class for pandas dataframes (and CSV files).
    """

    tmp_file_counter = 0  # used to number otherwise-nameless temp files

    def get_temp_filename(self, ext=None):
        self.tmp_file_counter += 1
        ext = ext or '.parquet'
        return f'df{self.tmp_file_counter:03}{ext}'

    def __new__(cls, *args, **kwargs):
        return super(PandasComparison, cls).__new__(cls)

    def check_dataframe(
        self,
        df,
        ref_df,
        actual_path=None,
        expected_path=None,
        check_data=None,
        check_types=None,
        check_order=None,
        check_extra_cols=None,
        sortby=None,
        condition=None,
        precision=None,
        msgs=None,
        type_matching=None,
        create_temporaries=True,
    ):
        """
        Compare two pandas dataframes.

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
                            Optional Diffs object.

            *type_matching* 'strict', 'medium', 'permissive'.
                            None is same as strict.

            *create_temporaries*  If True (the default), if the check fails,
                                  the actual result in the dataframe will be
                                  written to disk (usually as parquet).

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

        self.expected_path = expected_path
        self.actual_path = actual_path

        type_matching = type_matching or 'strict'
        diffs = nvl(diffs, Diffs())
        self.precision = nvl(precision, 6)

        check_types = resolve_option_flag(check_types, ref_df)
        check_extra_cols = resolve_option_flag(check_extra_cols, df)

        missing_cols = []
        extra_cols = []
        wrong_types = []
        wrong_ordering = False
        df = replace_cats(df)
        ref_df = replace_cats(ref_df)
        for c in check_types:
            if c not in list(df):
                missing_cols.append(c)
            elif not (
                types_match(df[c].dtype, ref_df[c].dtype, type_matching)
            ):
                wrong_types.append((c, df[c].dtype, ref_df[c].dtype))
        if check_extra_cols:
            extra_cols = set(check_extra_cols) - set(list(ref_df))
        if check_order != False and not missing_cols:
            check_order = resolve_option_flag(check_order, ref_df)
            order1 = [c for c in list(df) if c in check_order if c in ref_df]
            order2 = [c for c in list(ref_df) if c in check_order if c in df]
            wrong_ordering = order1 != order2

        same = not any(
            (missing_cols, extra_cols, wrong_types, wrong_ordering)
        )
        if not same:  # Just column structure, at this point
            self.different_column_structure(diffs)
            self.missing_columns_detected(diffs, missing_cols, ref_df)
            self.extra_columns_found(diffs, extra_cols, df)
            if wrong_types:
                for c, dtype, ref_dtype in wrong_types:
                    self.field_types_differ(diffs, c, dtype, ref_dtype)
            if wrong_ordering:
                self.different_column_orders(diffs, df, ref_df)

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

        na, nr = len(df), len(ref_df)
        same_len = na == nr
        if not same_len:
            self.different_numbers_of_rows(diffs, na, nr)
            same = False

        if same:
            check_data = resolve_option_flag(check_data, ref_df)
            if check_data:
                cols = [c for c in check_data if c not in missing_cols]
                nd = self.same_structure_ddiff(df[cols], ref_df[cols], diffs)
                same = nd == 0

        if not same and create_temporaries:
            self.write_temporaries(df, ref_df, diffs)
        return FailureDiffs(failures=0 if same else 1, diffs=diffs)

    def write_temporaries(self, actual, expected, msgs):
        differ = None
        actual_path = self.actual_path
        expected_path = self.expected_path
        if actual_path and expected_path:
            commonname = os.path.split(actual_path)[1]
            differ = self.compare_with(actual_path, expected_path)

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
                    differ = self.compare_with(
                        actual_path, tmpExpectedPath, custom_diff_cmd=TDDA_DIFF
                    )
            if actual is not None and not actual_path:
                # no actual file, so write it
                tmpActualPath = os.path.join(
                    self.tmp_dir, 'actual-' + commonname
                )
                self._write_reference_dataframe(actual, tmpActualPath)
                if expected_path:
                    differ = self.compare_with(
                        tmpActualPath, expected_path, custom_diff_cmd=TDDA_DIFF
                    )

        if differ:
            self.info(msgs, differ)

        # if not actual_path or not expected_path:
        #     if expected_path:
        #         self.info(msgs, 'Expected file %s' % expected_path)
        #     elif actual_path:
        #         self.info(msgs,
        #                   'Actual file %s' % os.path.normpath(actual_path))


    def same_structure_ddiff(self, df, ref_df, diffs):
        """
        Test two dataframes with the same structure for differences.

        Datasets must be same shape (this should have been checked
        before calling). Assertions check this at start.

        Args:
            df         Actual/LHS data frame
            ref_df     Actual/RHS data frame
            diffs      Diffs object for reporing

        Returns:
            number of different values
        """
        assert list(df) == list(ref_df)
        assert df.shape == ref_df.shape

        if self.precision is not None:
            df = df.round(self.precision).reset_index(drop=True)
            ref_df = ref_df.round(self.precision).reset_index(
                drop=True
            )

        if df.equals(ref_df):  # the check
            return 0
        else:
            #return self.same_structure_summary_diffs(df, ref_df, diffs)
            diffs.df.diff = same_structure_dataframe_diffs(df, ref_df)
            n_diffs = diffs.df.diff.n_diff_values
            if n_diffs:
                diffs.append(str(diffs.df.diff))
            return n_diffs

    def same_structure_summary_diffs(self, df, ref_df, diffs):
        """
        Summarize differences between two dataframes with the same structure.

        Datasets must be same shape (this should have been checked
        before calling), and are assumed to have at least one difference.

        (It's a problem if they aren't the same shape; it's just needlessly
        slow (in the sense that there are faster ways to check this)
        if there are differences.

        Args:
            df         Actual/LHS data frame
            ref_df     Actual/RHS data frame
            diffs      Diffs object for reporing

        Returns:
            number of different values
        """

        failures = []
        for c in list(df):
            if not df[c].equals(ref_df[c]):
                pdiffs = self.single_col_difference_summary(
                    c, df[c], ref_df[c]
                )
                if pdiffs:
                    failures.append('Column values differ: %s' % c)
                    failures.append(pdiffs)
        if failures:
            self.failure(diffs, 'Contents check failed.')
            for f in failures:
                self.info(diffs, f)
            return 1
        else:
            return 0

    def single_col_difference_summary(self, name, left, right):
        """
        Args:
            name        is the name of the columns
            left        is the left-hand series
            right       is the rish-hand series

        Returns a short summary of where values differ, for two columns.
        """
        cdiff = single_col_diffs(left, right)
        if cdiff.n == 0:
            return ''

        l_vals = left[cdiff.mask][:10]
        r_vals = right[cdiff.mask][:10]
        n = len(l_vals)
        s = (
            'First 10 differences:\n'
            if n > 10
            else ('Difference%s:\n' % ('s' if n > 1 else ''))
        )
        return f'{s}{col_comparison(l_vals, r_vals)}\n'


    def sample(self, values, start, stop):
        return [
            None if pd.isnull(values[i]) else values[i]
            for i in range(start, stop)
        ]

    def sample_format(self, values, start, stop, precision):
        s = self.sample(values, start, stop)
        r = ', '.join(
            [
                'null'
                if pd.isnull(v)
                else str('%d' % v)
                if type(v) in (int, np.int32, np.int64)
                else str('%.*f' % (precision, v))
                if type(v) in (float, np.float32, np.float64)
                else str('"%s"' % v)
                if values.dtype == object
                else str(v)
                for v in s
            ]
        )
        if len(s) < stop - start:
            r += ' ...'
        return r

    def ndifferences(self, values1, values2, start, limit=10):
        stop = min(start + limit, len(values1))
        for i in range(start, stop):
            v1 = values1[i]
            v2 = values2[i]
            if v1 == v2 or (pd.isnull(v1) and pd.isnull(v2)):
                return i
        return stop

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
        msgs=None,
        **kwargs,
    ):
        """
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
        msgs=None,
        **kwargs,
    ):
        """
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

    def all_fields_except(self, exclusions):
        """
        Helper function, for using with *check_data*, *check_types* and
        *check_order* parameters to assertion functions for Pandas DataFrames.

        It returns the names of all of the fields in the DataFrame being
        checked, apart from the ones given.

        *exclusions* is a list of field names.
        """
        return lambda df: list(set(list(df)) - set(exclusions))

    def load_csv(self, csvfile, loader=None, **kwargs):
        """
        Function for constructing a pandas dataframe from a CSV file.
        """
        if loader is None:
            loader = default_csv_loader
        return loader(csvfile, **kwargs)

    def load_serialized_dataframe(
        self, path, actual_df=None, loader=None, **kwargs
    ):
        """
        Function for constructing a pandas dataframe from a serialized
        dataframe in a file (parquet or CSV)
        """
        ext = os.path.splitext(path)[1].lower()
        if ext == '.parquet':
            try:
                return pd.read_parquet(path)
            except FileNotFoundError:
                if actual_df is not None:
                    tmp_path = self.tmp_path_for(path)
                    self._write_reference_dataframe(actual_df, tmp_path)
                    print(f'\n*** Expected parquet file {path} not found.\n')
                    print(self.compare_with(tmp_path, path))
                raise
        else:
            return self.load_csv(path, loader, **kwargs)

    def write_csv(self, df, csvfile, writer=None, **kwargs):
        """
        Function for saving a Pandas DataFrame to a CSV file.
        Used when regenerating DataFrame reference results.
        """
        if writer is None:
            writer = default_csv_writer
        writer(df, csvfile, **kwargs)

    def _write_reference_dataframe(
        self, df, path, writer=None, **kwargs
    ):
        """
        Function for saving a Pandas DataFrame to a CSV file.
        Used when regenerating DataFrame reference results.
        """
        ext = os.path.splitext(path)[1].lower()
        if ext == '.parquet':
            df.to_parquet(path)
        else:
            self.write_csv(df, path, writer, **kwargs)
        if self.verbose:
            print(f'*** Written {path}.')

    def _write_reference_dataframe_from_file(
        self, actual_path, ref_path, writer=None, **kwargs
    ):
        """
        Function for saving a Pandas DataFrame to a CSV file.
        Used when regenerating DataFrame reference results.
        """
        df = self.load_serialized_dataframe(actual_path)
        self._write_reference_dataframe(df, ref_path, writer=writer, **kwargs)

    def _write_reference_dataframes_from_files(
        self, actual_paths, ref_paths, writer=None, **kwargs
    ):
        """
        Function for saving a Pandas DataFrame to a CSV file.
        Used when regenerating DataFrame reference results.
        """
        for (actual_path, ref_path) in zip(actual_paths, ref_paths):
            df = self.load_serialized_dataframe(actual_path)
            self._write_reference_dataframe_from_file(
                actual_path, ref_path, writer=writer, **kwargs
            )


class PandasNotImplemented(object):
    """
    Null implementation of PandasComparison, used when pandas not available.
    """

    def __getattr__(self, name):
        return lambda *args, **kwargs: self.method(name, *args, **kwargs)

    def method(self, name, *args, **kwargs):
        raise NotImplementedError('%s: Pandas not available.' % name)


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
        'quotechar': '"',
        'quoting': csv.QUOTE_MINIMAL,
        'escapechar': '\\',
        'na_values': ['', 'NaN', 'NULL'],
        'keep_default_na': False,
    }
    options.update(kwargs)
    if 'infer_datetime_format' in options:  # don't let pandas do it.
        del options['infer_datetime_format']
    infer_datetimes = kwargs.get('infer_datetime_format', True)

    try:
        df = pd.read_csv(csvfile, **options)
    except pd.errors.ParserError:
        # Pandas CSV reader gets confused by stutter-quoted text that
        # also includes escapechars. So try again, with no escapechar.
        del options['escapechar']
        df = pd.read_csv(csvfile, **options)

    if infer_datetimes:  # We do it ourselves, now, instead of lettings
        # pandas do it.
        colnames = df.columns.tolist()
        for c in colnames:
            if is_string_col(df[c]):
                fmt = infer_date_format(df[c])
                if fmt:
                    try:
                        datecol = pd.to_datetime(df[c], format=fmt)
                        if datecol.dtype == np.dtype('datetime64[ns]'):
                            df[c] = datecol
                    except Exception as e:
                        pass
        ndf = pd.DataFrame()
        for c in colnames:
            ndf[c] = df[c]
        return ndf
    else:
        return df


def default_csv_writer(df, csvfile, **kwargs):
    """
    Default function for writing a csv file.

    Wrapper around the standard pandas pd.to_csv() function, but with
    slightly different defaults:

        - index                 is ``False``
        - encoding              is ``utf-8``
    """
    options = {
        'index': False,
        'encoding': 'utf-8',
    }
    options.update(kwargs)
    if sys.version_info[0] > 2 and len(df) > 0:
        bytes_cols = find_bytes_cols(df)
        if bytes_cols:
            df = bytes_to_unicode(df, bytes_cols)
    return df.to_csv(csvfile, **options)


def find_bytes_cols(df):
    bytes_cols = []
    for c in list(df):
        if is_string_col(df[c]):
            nonnulls = df[df[c].notnull()].reset_index()[c]
            if len(nonnulls) > 0 and type(nonnulls[0]) is bytes:
                bytes_cols.append(c)
    return bytes_cols


def bytes_to_unicode(df, bytes_cols):
    cols = OrderedDict()
    for c in list(df):
        if c in bytes_cols:
            cols[unicode_definite(c)] = df[c].str.decode('UTF-8')
        else:
            cols[unicode_definite(c)] = df[c]
    return pd.DataFrame(cols, index=df.index.copy())


def unicode_definite(s):
    return s if type(s) == str else s.decode('UTF-8')


def resolve_option_flag(flag, df):
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
        return list(df)
    elif flag is False:
        return []
    elif hasattr(flag, '__call__'):
        return flag(df)
    else:
        return flag


def sample_format2(values, precision=None):
    return ', '.join(
        '%d: %s' % (values.index[i], values.iloc[i])
        for i in range(min(len(values), 10))
    )


def loosen_type(t):
    name = ''.join(c for c in t if not c.isdigit()).lower()
    p = name.find('[')
    name = name[:p] if p > -1 else name
    return 'bool' if name == 'boolean' else name


def types_match(t1, t2, level=None):
    assert level is None or level in ('strict', 'medium', 'permissive')
    if level is None or level == 'strict' or t1.name == t2.name:
        return t1.name == t2.name

    t1loose = loosen_type(t1.name)
    t2loose = loosen_type(t2.name)
    object_types = ('string', 'boolean', 'datetime', 'bool')
    if (
        t1loose == t2loose
        or t1loose == 'object'
        and t2loose in object_types
        or t2loose == 'object'
        and t1loose in object_types
    ):
        return True

    numeric_types = ('bool', 'boolean', 'int', 'float')
    if (
        level == 'permissive'
        and t1loose in numeric_types
        and t2loose in numeric_types
    ):
        return True
    return False


def diff_masks(df, ref_df, only_diffs=False):
    """
    Compares two data frames dictionary of ColDiff pairs keyed on column name

    Args:
        df           "left-hand" data frame
        ref_df       "right-hand" column
        only_diffs   If True, filter the dictionary to only those
                     columns with differences

    Returns:
        (diffs,    boolean mask with 1's where there are differences
         n)        number of differences
    """
    assert list(df) == list(ref_df)
    diffs = {
        k: single_col_diffs(df[k], ref_df[k])
        for k in df
    }
    if only_diffs:
        for k in list(diffs):
            if diff[k].n == 0:
                del[k]
    return diffs


def same_structure_dataframe_diffs(df, ref_df):
    """
    Compute differences between each pair of columns in two data frames.

    The two data frames must have the same columns, the same lengths,
    and compatible types.

    Args:
        df        "left" data frame  (typically "actual")
        ref_df    "right" data frame (typically expected/reference)

    Returns:
        SameStructureDDiff  for df, ref_df
    """
    assert list(df) == list(ref_df)
    d = {}
    n_vals = 0   # total number of values with diffenrences
    for c in list(df):
        diffs = single_col_diffs(df[c], ref_df[c])
        if diffs.n > 0:
            d[c] = diffs.mask
            n_vals += diffs.n
    n_cols = len(d)  # number of columns with differences

    if n_vals > 0:
        D = create_row_diff_counts(list(d.values()))
        n_rows = (D > 0).sum().item()  # number of rows with differences
        row_diff_counts = DiffCounts(D, n_rows)
    else:
        n_rows = 0
        row_diff_counts = None

    return SameStructureDDiff(df.shape,
                              pd.DataFrame(d), row_diff_counts,
                              n_vals, n_cols, n_rows)


def single_col_diffs(L, R):
    """
    Compares two columns and returns col indicating where they are different

    Args:
        L     "left-hand" column
        R     "left-hand" column

    Returns:
        (diffs,    boolean mask with 1's where there are differences
         n)        number of differences
    """
    different = ~(L.eq(R) | (L.isnull() & R.isnull()))
    if different.dtype == pd.BooleanDtype():
        different = different.fillna(True)
    return ColDiff(different, different.sum().item())


def col_comparison(left, right):
    n = min(len(left), 10)
    indexes = [str(left.index[i]) for i in range(n)]
    lefts = [repr(left.iloc[i]) for i in range(n)]
    rights = [repr(right.iloc[i]) for i in range(n)]
    df = pd.DataFrame({
        'row': indexes,
        'actual': lefts,
        'expected': rights,
    })
    return df.to_string(index=False) if n > 0 else ''


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


def create_row_diff_counts(masks):
    """
    Combine all column diff masks efficiently for col with
    counts of number of differences for each row.

    Args:
        masks: list of bool columns indicating column difference

    Return:
        row_difference_col
    """
    counts = [m.astype(int) for m in masks]
    while len(counts) > 1:
        last = [counts[-1].astype(int)] if len(counts) % 2 == 1 else []
        counts = [
            (counts[2 * i] + counts[2 * i + 1])
            for i in range(len(counts) // 2)
        ] + last
    return counts[0]


def replace_cats(df):
    cats = [c for c in df if str(df[c].dtype) == 'category']
    if cats:
        df = pd.DataFrame({
            c: df[c].astype('string') if c in cats else df[c]
            for c in df
        })
    return df
