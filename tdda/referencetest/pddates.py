"""
Pandas-specific date format inference.

The regex patterns, Separators namedtuple, get_date_separators and
infer_date_format_from_strings live in tdda.serial.dateutils (no pandas
dependency). This module re-exports them for backward compatibility and
adds infer_date_format() which operates on a pandas Series and returns
separator-preserving strftime strings suitable for pd.to_datetime().
"""

import re

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
    the sentinel 'ISO8601' for ISO datetimes, or None if format cannot
    be determined. Preserves the actual separators used in the data.

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
    return _infer_strftime(strings, n, nonnulls)


def _infer_strftime(strings, n, nonnulls):
    """
    Return a strftime string with the actual separators found in the data.
    Internal helper used by infer_date_format.
    """
    if not all(re.match(DateRE.DATEISH, s) for s in strings):
        return None

    # ── ISO: year-first ───────────────────────────────────────────────────────
    if all(re.match(DateRE.ISO_DATEISH, s) for s in strings):
        m = re.match(DateRE.SEP_ISO, strings[0])
        assert m
        sep = m.group(1)
        return '%%Y%s%%m%s%%d' % (sep, sep)

    if all(re.match(DateRE.ISO_DATETIMEISH, s) for s in strings):
        return ISODT

    # ── 4-digit year at end (EU or US) ────────────────────────────────────────
    matches = [re.match(DateRE.DATEISH4Y, s) for s in strings]
    if all(matches):
        seps = get_date_separators(DateRE.SEPS4Y, strings[0])
        if seps is None:
            return None
        m1 = max(int(m.group(1)) for m in matches)
        m2 = max(int(m.group(2)) for m in matches)
        dsep = seps.date_sep
        if m1 <= 12 and m2 > 12:  # US: month first, day second
            return ('%%m%s%%d%s%%Y' % (dsep, dsep)) + seps.time_part
        elif m1 > 12 and m2 <= 12:  # Euro: day first, month second
            return ('%%d%s%%m%s%%Y' % (dsep, dsep)) + seps.time_part
        elif m1 <= 12 and m2 <= 12 and nonnulls.size > n:
            # ambiguous with n samples — try more
            return _infer_strftime(nonnulls[:n * 10].to_list(), n * 10, nonnulls)
        return None

    # ── 2-digit year at end (EU or US) ────────────────────────────────────────
    matches = [re.match(DateRE.DATEISH2Y, s) for s in strings]
    if all(matches):
        seps = get_date_separators(DateRE.SEPS2Y, strings[0])  # fixed: uses SEPS2Y
        if seps is None:
            return None
        m1 = max(int(m.group(1)) for m in matches)
        m2 = max(int(m.group(2)) for m in matches)
        dsep = seps.date_sep
        if m1 <= 12 and m2 > 12:  # US 2Y
            return ('%%m%s%%d%s%%y' % (dsep, dsep)) + seps.time_part
        elif m1 > 12 and m2 <= 12:  # Euro 2Y
            return ('%%d%s%%m%s%%y' % (dsep, dsep)) + seps.time_part
        return None

    return None
