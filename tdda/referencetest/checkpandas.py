"""
checkpandas.py: comparison mechanism for pandas dataframes (and CSV files)

Source repository: http://github.com/tdda/tdda

License: MIT

Copyright (c) Stochastic Solutions Limited 2016-2026
"""

import csv
import os
import sys

from collections import OrderedDict

from tdda.pdutils import pandas_types_match
from tdda.referencetest.basecomparison import BaseComparison, ROW_NUM_HEADER
from tdda.referencetest.diffutils import (
    same_structure_dataframe_diffs,
    single_col_diffs,
)
from tdda.serial.pandasio import csv_to_pandas, pandas_read_df, infer_dates
from tdda.utils import debug, unicode_definite

from tdda.pd.utils import is_string_col, first_non_null, round_df

import pandas as pd
import numpy as np


# TDDA_DIFF = 'diff'


class PandasComparison(BaseComparison):
    """
    Comparison class for pandas dataframes (and CSV files).
    """

    tmp_file_counter = 0  # used to number otherwise-nameless temp files

    def get_temp_filename(self, ext=None):
        PandasComparison.tmp_file_counter += 1
        ext = ext or '.parquet'
        return f'df{self.tmp_file_counter:03}{ext}'

    def __new__(cls, *args, **kwargs):
        return super(PandasComparison, cls).__new__(cls)

    def same_structure_ddiff(self, df, ref_df, diffs, key=None, idx=None):
        """
        Test two dataframes with the same structure for differences.

        Datasets must be same shape (this should have been checked
        before calling). Assertions check this at start.

        Args:
            df         Actual/LHS data frame
            ref_df     Actual/RHS data frame
            diffs      Diffs object for reporting
            key
            idx

        Returns:
            number of different values

        Modifies:
            diffs, by adding in any differences found
        """
        assert list(df) == list(ref_df)
        assert df.shape[1] == ref_df.shape[1]

        if self.precision is not None:
            df = round_df(df, self.precision)
            ref_df = round_df(ref_df, self.precision)
        if self.fuzzy_nulls:
            dtypes = ['object', 'str']
            if self.fuzzy_nulls == True:
                dtypes.append('string')

            for c in df:
                ltype = str(df[c].dtype)
                rtype = str(ref_df[c].dtype)
                if ltype in dtypes and rtype in dtypes:
                    if ltype == 'string' or type(first_non_null(df[c])) == str:
                        df[c] = df[c].fillna('')
                    if (
                        rtype == 'string'
                        or type(first_non_null(ref_df[c])) == str
                    ):
                        ref_df[c] = ref_df[c].fillna('')

        if df.equals(ref_df):  # the check
            return 0
        else:
            D = same_structure_dataframe_diffs(
                df, ref_df, key=key, idx=idx, config=self.config
            )
            n_diffs = D.n_diff_values
            if n_diffs > 0:
                diffs.dfd.diff = D
                diffs.append(str(D))
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

    def single_col_difference_summary(self, name, left, right, n=10):
        """
        Args:
            name        is the name of the columns
            left        is the left-hand series
            right       is the right-hand series

        Returns a short summary of where values differ, for two columns.

        TODO: Extend summary if diff lengths, one < 10?
        """
        cdiff = single_col_diffs(left, right)
        if cdiff.total == 0:
            return ''

        nL, nR = len(left), len(right)
        mL, mR = min(nL, n), min(nR, n)
        l_vals = left[:nL][cdiff.mask[:nL]]
        r_vals = right[:nR][cdiff.mask[:nR]]
        N = max(nL, nR)
        s = (
            f'First {n} differences:\n'
            if N > n
            else ('Difference%s:\n' % ('s' if N > 1 else ''))
        )
        return f'{s}{col_comparison(l_vals, r_vals, n)}\n'

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

    def load_serialized_dataframe(
        self,
        path,
        actual_df=None,
        loader=None,
        reset_index=True,
        backend=None,
        **kwargs,
    ):
        """
        Function for constructing a pandas dataframe from a serialized
        dataframe in a file (parquet or CSV)
        """
        if isinstance(path, pd.DataFrame):
            return path
        ext = os.path.splitext(path)[1].lower()
        if ext == '.parquet':
            try:
                df = pandas_read_df(path, backend=backend)
                if reset_index and not df.index.is_monotonic_increasing:
                    df.reset_index(drop=True, inplace=True)
                return df
            except FileNotFoundError:
                if actual_df is not None:
                    tmp_path = self.tmp_path_for(path)
                    self._write_reference_dataframe(actual_df, tmp_path)
                    print(f'\n*** Expected parquet file {path} not found.\n')
                    print(self.compare_with(tmp_path, path))
                raise
        else:
            return self.load_csv(path, loader, backend=backend, **kwargs)

    def write_csv(self, df, csvfile, writer=None, **kwargs):
        """
        Function for saving a Pandas DataFrame to a CSV file.
        Used when regenerating DataFrame reference results.
        """
        if writer is None:
            writer = default_csv_writer
        writer(df, csvfile, **kwargs)

    def write_parquet(self, df, path):
        df.to_parquet(path)

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
        for actual_path, ref_path in zip(actual_paths, ref_paths):
            self._write_reference_dataframe_from_file(
                actual_path, ref_path, writer=writer, **kwargs
            )

    def default_csv_loader(self, path, **kwargs):
        # return default_csv_loader(path, **kwargs)
        return csv_to_pandas(path, **kwargs)

    def csv_to_dataframe(self, path, **kwargs):
        return csv_to_pandas(path, **kwargs)

    @staticmethod
    def _replace_cats(df):
        """
        Replace any columns of type category with corresponding string
        columns in df.
        """
        cats = [c for c in df if str(df[c].dtype) == 'category']
        if cats:
            df = pd.DataFrame(
                {c: df[c].astype('string') if c in cats else df[c] for c in df}
            )
        return df

    @staticmethod
    def _types_match(t1, t2, level=None):
        return pandas_types_match(t1, t2, level=level)

    @staticmethod
    def _sort_df(df, sortby):
        df.sort_values(sortby, inplace=True)

    @staticmethod
    def _apply_condition(df, condition):
        return df[condition(df)].reindex()

    ####


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

    if infer_datetimes:  # We do it ourselves, now, instead of letting
        # pandas do it.
        df = infer_dates(df)

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


def sample_format2(values, precision=None):
    return ', '.join(
        '%d: %s' % (values.index[i], values.iloc[i])
        for i in range(min(len(values), 10))
    )


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
    diffs = {k: single_col_diffs(df[k], ref_df[k]) for k in df}
    if only_diffs:
        for k in list(diffs):
            if diffs[k].total == 0:
                del [k]
    return diffs


def col_comparison(left, right, n):
    nL, nR = len(left), len(right)
    M = max(nL, nR)
    N = min(M, n)
    idx = left if nL >= nR else right
    indexes = [str(idx.index[i]) for i in range(N)]
    lefts = [repr(left.iloc[i]) for i in range(nL)] + [''] * (N - nL)
    rights = [repr(right.iloc[i]) for i in range(nR)] + [''] * (N - nR)
    df = pd.DataFrame(
        {
            ROW_NUM_HEADER: indexes,
            'actual': lefts,
            'expected': rights,
        }
    )
    return df.to_string(index=False) if N > 0 else ''


def diff_dataframes(*args, **kwargs):
    c = PandasComparison()
    return c.check_dataframe(*args, **kwargs)
