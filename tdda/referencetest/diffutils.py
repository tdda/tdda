from collections import namedtuple
from tdda.abstractdf import (
    bool_type,
    cast_col_to_int,
    col_names,
    calc_nunique,
    col_types_match,
    df_add_named_col_with_values,
    df_group_count,
    df_join,
    df_len_diff,
    df_rename_cols,
    df_sort,
    fillnull_col,
    index_col,
    is_pandas_df,
    is_pandas_series,
    is_pandas_obj,
    eltwise_isnull,
    lib,
)
from tdda.referencetest.samestructurediff import SameStructureDDiff
from tdda.utils import (
    error,
    find_free_name,
    is_sequence,
    listify,
    warn,
    debug,
)

DiffCounts = namedtuple('DiffCounts', 'rowdiffs n')


class ColDiff:
    def __init__(self, mask, extra):
        self.mask = mask  # Boolean mask, 1 where different
        # within common area (length)
        self.n = int(mask.sum())  # Number of differences in common area
        self.extra = extra  # Number of extra rows (left - right)
        self.total = self.n + abs(extra)  # Total rows with differences
        # including extra/missing rows

    def __str__(self):
        return (
            'ColDiff(\n'
            f'    mask={self.mask},\n'
            f'    n={self.n},\n'
            f'    extra={self.extra}, \n'
            f'    total={self.total}\n'
            ')'
        )


def join_for_diff(L, R, key):
    """
    Joins L and R using specified key columns.

    Returns aligned versions of L and R with a column indicating
    which row they came from in the original L and R (index from 0)
    with nulls for keys that are only in the other dataframe.

    The name of indicator colums (usually #idx# is also returned.
    """
    keys = [key] if isinstance(key, str) else key
    left_names, right_names = col_names(L), col_names(R)
    names = set(left_names) | set(right_names)
    is_pd = is_pandas_df(L)
    if not is_pd == is_pandas_df(R):
        raise ValueError('Data Frames from different libraries.')
    if not len(left_names) == len(names):
        raise ValueError(f'Fields different in left and right data frames.')
    for k in keys:
        if not k in left_names:
            raise ValueError(f'No field {k} in left data frames')

    idx_col = find_free_name(names, ['#idx#'])
    nL, nR = len(L), len(R)
    L = df_add_named_col_with_values(L, idx_col, index_col(is_pd, nL))
    R = df_add_named_col_with_values(R, idx_col, index_col(is_pd, nR))
    dfj = df_sort(df_join(L, R, keys), idx_col)  # sort on left
    common_cols = [idx_col] + [k for k in left_names if not k in keys]
    L = dfj[keys + common_cols]
    R = df_rename_cols(
        dfj[keys + [f'{k}__r' for k in common_cols]],
        {f'{k}__r': k for k in common_cols},
    )
    return L, R, idx_col


def find_usable_key(is_pandas, left, right, key=None, verbosity=1):
    """
    If key is supplied, this adds a row number to (copies of) the
    left and right DataFrames, at the start.

    If key is True, this tries to find a common key to use for the outer
    join for diffing. If it fails, it falls back to using row index.

    If key is None/Falsy:
        If the DataFrames have the same length, this does nothing.
        If they have different lengths, a row number is added to them both.

    Args:
        left:   a DataFrame (currently Pandas)
        right:  a DataFrame (currently Pandas)

        key:    One of:

                    a field in left and right, to use as a join key

                    a list of fields, in left and right, to use as a join key

                    True: meaning that a join key should be found

                    None (or other falsy value) means just use row number
                    as the join key.

       Returns:
            (left, right, key):  The left and right and DataFrames are
                                 copies of left and right with an extra
                                 column, if that has been created.

                                 The key is the key found, to be used,
                                 if a key is created and found.
    """
    nL, nR = left.shape[0], right.shape[0]
    if isinstance(key, str) or is_sequence(key):
        check_is_usable_key(left, right, key, raise_if_not=True)
        mode = 'key'  # key provided
    elif key == True:
        mode = 'find'  # try to find a key
    elif key:
        error(f'Unexpected value for key value: {repr(key)}')
    elif nL == nR:
        mode = 'common'  # same length, no key needed
    else:
        mode = 'rownum'  # Add row number and use as key

    if mode == 'find':
        key = find_common_key(left, right, verbosity=verbosity)
        if key is None:
            mode = 'common' if nL == nR else 'rownum'

    return left, right, key


def find_common_key(left, right, verbosity=1):
    nL, nR = left.shape[0], right.shape[0]
    right_cols = set(col_names(right))
    shared_cols = [k for k in col_names(left) if k in right_cols]
    distincts = {}
    for key in shared_cols:
        ndL = calc_nunique(left[key])
        if ndL == nL:
            ndR = calc_nunique(right[key])
            if ndR == nR:
                return key
        distincts[key] = ndL
    if len(distincts) >= 2:
        cands = sorted(shared_cols, key=lambda k: -distincts[k])
        for i, key1 in enumerate(cands[:-1]):
            for key2 in cands[i + 1 :]:
                keys = [key1, key2]
                L = left[keys].groupby(keys).count().reset_index()
                if L.shape[0] == nL:
                    R = right[keys].groupby(keys).count().reset_index()
                    if R.shape[0] == nR:
                        return keys

    warn('No usable key find. Use row number.', verbose=verbosity > 0)
    return None


def check_is_usable_key(left, right, key, raise_if_not=False):
    keys = listify(key)
    str_key = ','.join(key)
    nL, nR = left.shape[0], right.shape[0]
    L = df_group_count(left[keys], keys)
    if L.shape[0] == nL:
        R = df_group_count(right[keys], keys)
        if R.shape[0] == nR:
            return True
        elif raise_if_not:
            error(f'{str_key} is not a primary key for the right DataFrame.')
        else:
            return False
    elif raise_if_not:
        error(f'{str_key} is not a primary key for the left DataFrame.')
    return False


def same_structure_dataframe_diffs(
    df, ref_df, key=None, idx=None, config=None
):
    """
    Compute differences between each pair of columns in two data frames.

    The two data frames must have the same columns and compatible types,
    but not necessarily the same length.

    Args:
        df        "left" data frame  (typically "actual")
        ref_df    "right" data frame (typically expected/reference)

    Returns:
        SameStructureDDiff  for df, ref_df
    """
    assert set(col_names(df)) == set(col_names(ref_df))
    d = {}
    missings = None
    if idx:
        missings = eltwise_isnull(df[idx]) | eltwise_isnull(ref_df[idx])
    n_vals = 0  # total number of values with differences
    # (including values from "extra" rows)
    for c in col_names(df):
        if c != idx:
            diffs = single_col_diffs(df[c], ref_df[c], missings)
            if diffs.total > 0:
                d[c] = diffs.mask
                n_vals += diffs.total
    n_cols = len(d)  # number of columns with differences

    delta = df_len_diff(df, ref_df)
    if n_vals > 0:
        D = create_row_diff_counts(list(d.values()))
        n_rows = int((D > 0).sum()) + abs(delta)  # rows with differences
        row_diff_counts = DiffCounts(D, n_rows)
    else:
        n_rows = 0
        row_diff_counts = None
    dfl = lib(df)
    diff_df = dfl.DataFrame(d)
    return SameStructureDDiff(
        df.shape,
        diff_df,
        row_diff_counts,
        n_vals,
        n_cols,
        n_rows,
        delta,
        key=key,
        idx=idx,
        config=config,
    )


def single_col_diffs(left, right, missings=None):
    """
    Compares two columns and returns col indicating where they are different

    Args:
        L     "left-hand" column
        R     "right-hand" colum
        missings: optional col with mask that is true for unmatched rows
                  (always return True for diff)



    Returns:
        (diffs,    boolean mask with 1's where there are differences
         n)        number of differences

    If they are different lengths, all the values in the longer row
    are considered different (even if null).

    The col diff is the length of the SHORTER of left and right
    (with all the extra places "obviously" being different.

    """
    ispd = is_pandas_series(left)
    if ispd and 'string' in (str(left.dtype), str(right.dtype)):
        # "eq not implemented for
        #  <class 'pandas.core.arrays.string_.StringArray'>"
        left, right = left.astype('string'), right.astype('string')
    nL, nR = left.shape[0], right.shape[0]
    L, R = left, right
    if nL > nR:
        L = left[:nR]
    elif nR > nL:
        R = right[:nL]
    if col_types_match(L, R, level='loose'):
        if (
            ispd
            and str(L.dtype).startswith('datetime')
            and str(R.dtype).startswith('datetime')
            and L.dtype != R.dtype
        ):
            L = L.astype(R.dtype)
        different = ~(L.eq(R) | (eltwise_isnull(L) & eltwise_isnull(R)))
    else:
        different = ~(eltwise_isnull(L) & eltwise_isnull(R))
    different = fillnull_col(different, True)
    if missings is not None:
        difference = different | missings
    return ColDiff(different, df_len_diff(left, right))


def create_row_diff_counts(masks):
    """
    Combine all column diff masks efficiently for col with
    counts of number of differences for each row.

    Args:
        masks: list of bool columns indicating column difference

    Return:
        row_difference_col
    """
    counts = [cast_col_to_int(m) for m in masks]
    while len(counts) > 1:
        last = [cast_col_to_int(counts[-1])] if len(counts) % 2 == 1 else []
        counts = [
            (counts[2 * i] + counts[2 * i + 1])
            for i in range(len(counts) // 2)
        ] + last
    return counts[0]
