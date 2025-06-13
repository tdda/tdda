import numpy as np
import pandas as pd

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
    return dtype == np.dtype('O') or is_categorical_dtype(dtype)


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
