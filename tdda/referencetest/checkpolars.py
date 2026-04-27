"""
checkpolars.py: comparison mechanism for polars dataframes (and CSV files)

Source repository: http://github.com/tdda/tdda

License: MIT

Copyright (c) Stochastic Solutions Limited 2016-2026
"""

import os

from tdda.referencetest.basecomparison import BaseComparison, ROW_NUM_HEADER
from tdda.referencetest.diffutils import (
    same_structure_dataframe_diffs,
)
from tdda.plutils import polars_types_match
from tdda.serial.polarsio import (
    csv_to_polars,
    polars_read_df,
)
from tdda.utils import debug
import polars as pl


class PolarsComparison(BaseComparison):
    """
    Comparison class for pandas dataframes (and CSV files).
    """

    tmp_file_counter = 0  # used to number otherwise-nameless temp files

    def get_temp_filename(self, ext=None):
        PolarsComparison.tmp_file_counter += 1
        ext = ext or '.parquet'
        return f'df{self.tmp_file_counter:03}{ext}'

    def __new__(cls, *args, **kwargs):
        return super(PolarsComparison, cls).__new__(cls)

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
        """
        assert df.columns == ref_df.columns
        assert df.shape == ref_df.shape

        if self.precision is not None:
            df = round_df(df, self.precision)
            ref_df = round_df(ref_df, self.precision)

        if self.fuzzy_nulls:
            for c in df.columns:
                ltype = str(df[c].dtype)
                rtype = str(ref_df[c].dtype)
                if ltype == rtype == 'String':
                    df[c] = df[c].fill_null('')
                    ref_df[c] = ref_df[c].fill_null('')

        if df.equals(ref_df):  # the check
            return 0
        else:
            D = same_structure_dataframe_diffs(
                df, ref_df, key=key, idx=idx, config=self.config
            )
            n_diffs = D.n_diff_values
            if n_diffs > 0:
                diffs.dfd.diff = D
                if n_diffs:
                    diffs.append(str(diffs.dfd.diff))
            return n_diffs

    def write_csv(self, df, csvfile, writer=None, **kwargs):
        """
        Function for saving a Pandas DataFrame to a CSV file.
        Used when regenerating DataFrame reference results.
        """
        if writer:
            writer(df, csvfile, **kwargs)
        else:
            df.write_csv(**kwargs)

    def write_parquet(self, df, path):
        df.write_parquet(path)

    def csv_to_dataframe(self, path, **kwargs):
        return csv_to_polars(path, **kwargs)

    default_csv_loader = csv_to_dataframe

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
        if isinstance(path, pl.DataFrame):
            return path
        ext = os.path.splitext(path)[1].lower()
        if ext == '.parquet':
            try:
                return polars_read_df(path)
            except FileNotFoundError:
                if actual_df is not None:
                    tmp_path = self.tmp_path_for(path)
                    self._write_reference_dataframe(actual_df, tmp_path)
                    print(f'\n*** Expected parquet file {path} not found.\n')
                    print(self.compare_with(tmp_path, path))
                raise
        else:
            return self.load_csv(path, loader, **kwargs)

    @staticmethod
    def _replace_cats(df):
        return df  # for now

    @staticmethod
    def _types_match(t1, t2, level=None):
        return polars_types_match(t1, t2, level)

    ####


def round_df(df, n):
    floats = {c.name for c in df if str(c.dtype).startswith('Float')}
    if not floats:
        return df
    return pl.DataFrame(
        {
            c: (df[c].round(n, mode='half_to_even') if c in floats else df[c])
            for c in df.columns
        }
    )


def diff_dataframes(*args, **kwargs):
    c = PolarsComparison()
    return c.check_dataframe(*args, **kwargs)
