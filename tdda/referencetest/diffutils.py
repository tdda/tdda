from tdda.abstractdf import (
    col_names,
    calc_nunique,
    df_add_named_col_with_values,
    df_group_count,
    df_join,
    df_rename_cols,
    df_sort,
    index_col,
    is_pandas_df,
)
from tdda.utils import (
    error,
    find_free_name,
    is_sequence,
    listify,
    warn,
)


def join_for_diff(L, R, key):
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
    dfj = df_sort(df_join(L, R, keys), idx_col)  # sort on left
    common_cols =  [idx_col] + [k for k in left_names if not k in keys]
    L = dfj[keys + common_cols]
    R = df_rename_cols(
        dfj[keys + [f'{k}__r' for k in common_cols]],
        {f'{k}__r': k for k in common_cols}
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
        mode = 'key'   # key provided
    elif key == True:
        mode = 'find'   # try to find a key
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
        cands = sorted(shared_cols, key = lambda k: -distincts[k])
        for i, key1 in enumerate(cands[:-1]):
            for key2 in cands[i + 1:]:
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
             error(f'{str_key} is not a primary key for in right DataFrame.')
        else:
            return False
    elif raise_if_not:
        error(f'{str_key} is not a primary key for in left DataFrame.')
    return False
