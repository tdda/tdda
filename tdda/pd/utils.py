import datetime

import numpy as np
import pandas as pd

from tdda.pdutils import loosen_pandas_type

pdmaj = int(pd.__version__.split('.')[0])
pd3 = pdmaj >= 3

if pd3:

    def round_df(df, precision):
        num_cols = df.select_dtypes(include='number').columns
        df = df.copy()
        df[num_cols] = df[num_cols].round(precision)
        return df.reset_index(drop=True)
else:

    def round_df(df, precision):
        return df.round(precision).reset_index(drop=True)


NULL_REPS = [
    '',
    'NULL',
    chr(0x2219),  # ∙ centred dot (BULLET OPERATOR)
    chr(0x2205),  # ∅  EMPTY SET
] + [chr(c) for c in range(0xA1, 0xBF)]
NON_ASCII_REPS = NULL_REPS[2:]
FIRST_BRAILLE = 0x2801  # first Braille character


def is_categorical_dtype(dtype):
    """
    Given column dtype, test whether it is a string type
    --- object or categorical
    """
    return isinstance(dtype, pd.core.dtypes.dtypes.CategoricalDtype)


def is_string_dtype(dtype):
    """
    Given column dtype, test whether it is a string type
    --- object or categorical
    """
    return (
        isinstance(dtype, pd.StringDtype)
        or dtype == np.dtype('O')
        or is_categorical_dtype(dtype)
        or str(dtype).startswith('string')  # includes pyarrow
    )


def coltype_is_boolean(col):
    return loosen_pandas_type(col.dtype) == 'bool'


def pandas_col_to_tdda_type(col):
    """
    Returns the TDDA type of a pandas Series (column).

    Basic TDDA types are one of 'bool', 'int', 'real', 'string' or 'date'.
    Returns 'other' if unrecognized.
    """
    dt = col.dtype
    dts = str(dt).lower()
    if dt == np.dtype('O'):
        # objects could be strings, booleans-with-nulls, or dates
        nn = col.dropna()
        if len(nn) == 0:
            return 'string'
        v = nn.iloc[0]
        if type(v) in (bool, np.bool_):
            return 'bool'
        if type(v) in (str, bytes):
            return 'string'
        if isinstance(v, (datetime.datetime, datetime.date)):
            return 'date'
        return 'string'
    if is_categorical_dtype(dt) or dts.startswith('str'):
        return 'string'
    if 'bool' in dts:
        return 'bool'
    if 'int' in dts:
        return 'int'
    if 'float' in dts or 'double' in dts:
        return 'real'
    if 'date' in dts:
        return 'date'
    return 'other'


def is_string_col(col):
    """
    Given a column col from a DataFrame, test whether it is a
    string type --- object or categorical
    """
    return is_string_dtype(col.dtype)


def first_non_null(s):
    """
    Returns first non-null value in series s
    """
    i = s.first_valid_index()
    return s.loc[i] if i is not None else None


def object_col_underlying_type(s):
    dt = str(s.dtype)
    if dt == 'object':
        v = first_non_null(s)
        return str(type(v).__name__)
    return dt


def find_safe_null_rep(df, preferred=None, non_ascii=False):
    """
    Returns a null string that can be used as a null safely
    because it is not in any string field in df.

    Can optionally pass in preferred values to true in preferred
    a list of strings.

    If non_ascii is set, the empty string and NULL will not be used.
    In this case, centred dot ('∙', BULLET OPERTOR) or EMPTY SET ('∅')
    are most likely, followed by a 0xA? character.
    """
    cols = [
        c for c in df if object_col_underlying_type(df[c]) in ('str', 'string')
    ]
    sdf = df[cols]
    standards = NON_ASCII_REPS if non_ascii else NULL_REPS
    for c in (preferred or []) + standards:
        if is_safe_null_rep(sdf, c):
            return c
    # None of the standard or requested ones is safe.
    n = FIRST_BRAILLE
    c = chr(n)
    while not is_safe_null_rep(sdf, c):
        n += 1
        c = chr(n)
    return c


def is_safe_null_rep(sdf, c):
    for s in sdf:
        if len(sdf.query(f'{s} == "{c}"')):
            return False
    return True
