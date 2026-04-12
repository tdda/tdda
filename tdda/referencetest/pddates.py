"""
Pandas-specific date format inference.

The regex patterns, Separators namedtuple, get_date_separators and
infer_date_format_from_strings live in tdda.serial.dateutils (no pandas
dependency). This module re-exports them for backward compatibility and
adds infer_date_format() which operates on a pandas Series and returns
separator-preserving strftime strings suitable for pd.to_datetime().
"""

from tdda.serial.dateutils import (
    DateRE,
    ISODT,
    Separators,
    get_date_separators,
    infer_date_format_from_strings,
)


def infer_date_format(col, n=100):
    """
    Infer a strftime format string from a pandas Series of date strings.

    Returns a strftime string (e.g. '%d-%m-%Y', '%m/%d/%Y %H:%M:%S'),
    the sentinel 'ISO8601' for ISO datetimes (which pandas/polars accept
    directly), or None if the format cannot be determined.

    Args:
        col: pandas Series of string values
        n:   maximum number of non-null values to inspect
    """
    nonnulls = col.dropna()
    if nonnulls.size == 0:
        return None
    strings = nonnulls[:n].to_list()
    if not strings or type(strings[0]) != str:
        return None
    fmt = infer_date_format_from_strings(strings)
    if fmt is not None:
        # pandas/polars accept 'ISO8601' for any ISO datetime variant
        if fmt.startswith('%Y') and '%H' in fmt:
            return ISODT
        return fmt
    # Ambiguous with n samples — try more if available
    if nonnulls.size > n:
        return infer_date_format(col, n * 10)
    return None
