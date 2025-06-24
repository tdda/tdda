import os

from tdda.referencetest.basecomparison import (
    BaseComparison,
    Diffs,
    FailureDiffs,
    ColDiff,
    DiffCounts,
    SameStructureDDiff,
    create_row_diffs_mask,
    valid_level,
)

from tdda.serial.polarsio import (
    csv_to_polars,
#    polars_df_to_csv
)

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

    def same_structure_ddiff(self, df, ref_df, diffs):
        """
        Test two dataframes with the same structure for differences.

        Datasets must be same shape (this should have been checked
        before calling). Assertions check this at start.

        Args:
            df         Actual/LHS data frame
            ref_df     Actual/RHS data frame
            diffs      Diffs object for reporting

        Returns:
            number of different values
        """
        assert df.columns == ref_df.columns
        assert df.shape == ref_df.shape

        if self.precision is not None:
            df = round_df(df, self.precision)
            ref_df = round_df(ref_df, self.precision)

        if self.fuzzy_nulls:
            for c in (df.columns):
                ltype = str(df[c].dtype)
                rtype = str(ref_df[c].dtype)
                if ltype == rtype == 'String':
                    df[c] = df[c].fill_null('')
                    ref_df[c] = ref_df[c].fill_null('')

        if df.equals(ref_df):  # the check
            return 0
        else:
            diffs.dfd.diff = same_structure_dataframe_diffs(df, ref_df)
            n_diffs = diffs.dfd.diff.n_diff_values
            if n_diffs:
                diffs.append(str(diffs.dfd.diff))
            return n_diffs

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
        self, path, actual_df=None, loader=None, reset_index=True,
        nullable=True, **kwargs
    ):
        """
        Function for constructing a pandas dataframe from a serialized
        dataframe in a file (parquet or CSV)
        """
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


def loosen_polars_type(t, level):
    t = str(t)
    level = valid_level(level)
    if level == 'strict':
        return 'String' if t == 'Utf8' else t

    if t.startswith('Float') or t.startswith('Decimal'):
        t = 'Float'
    elif t.startswith('Int') or t.startswith('UInt'):
        t = 'Int'
    elif t.startswith('Date'):
        t = 'Date'
    elif t in ('Categorical', 'Enum', 'Utf8'):
        t = 'String'

    if level == 'permissive':
        if t in {'Float', 'Int', 'Boolean'}:
            return 'Numeric'

    return t


def polars_types_match(t1, t2, level=None):
    return loosen_polars_type(t1, level) == loosen_polars_type(t2, level)


def round_df(df, n):
    floats = {c.name for c in df if str(c.dtype).startswith('Float')}
    if not floats:
        return df
    return pl.DataFrame({
         c: (df[c].round(n) if c in floats else df[c])
         for c in df.columns
    })


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
    assert set(df.columns) == set(ref_df.columns)
    d = {}
    n_vals = 0   # total number of values with diffenrences
    for c in df.columns:
        diffs = single_col_diffs(df[c], ref_df[c])
        if diffs.n > 0:
            d[c] = diffs.mask
            n_vals += diffs.n
    n_cols = len(d)  # number of columns with differences

    if n_vals > 0:
        D = create_row_diff_counts(list(d.values()))
        n_rows = (D > 0).sum()  # number of rows with differences
        row_diff_counts = DiffCounts(D, n_rows)
    else:
        n_rows = 0
        row_diff_counts = None
    diff_df = pl.DataFrame(d)
    return SameStructureDDiff(df.shape, diff_df, row_diff_counts,
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
    different = ~(L.eq(R) | (L.is_null() & R.is_null()))
    if different.dtype == pl.Boolean():
        different = different.fill_null(True)
    return ColDiff(different, different.sum())


def create_row_diff_counts(masks):
    """
    Combine all column diff masks efficiently for col with
    counts of number of differences for each row.

    Args:
        masks: list of bool columns indicating column difference

    Return:
        row_difference_col
    """
    counts = [m.cast(pl.Int64) for m in masks]
    while len(counts) > 1:
        last = [counts[-1].cast(Int64)] if len(counts) % 2 == 1 else []
        counts = [
            (counts[2 * i] + counts[2 * i + 1])
            for i in range(len(counts) // 2)
        ] + last
    return counts[0]


