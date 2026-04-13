"""
Date format inference utilities for flat-file (CSV) metadata.

Provides regex patterns and functions for detecting date and datetime
formats from lists of string values, with no pandas dependency.
"""

import re

from collections import namedtuple


# ── Regex patterns ────────────────────────────────────────────────────────────

class DateRE:
    # Any date-ish string: starts with 1-4 digits, sep, 1-2 digits, sep, ...
    DATEISH = re.compile(r'^[0-9]{1,4}[-./][0-9]{1,2}[-./][0-9]{1,2}.*$')

    # ISO date: YYYY-MM-DD or YYYY/MM/DD (no time)
    ISO_DATEISH = re.compile(r'^[0-9]{4}[-/][0-9]{1,2}[-/][0-9]{1,2}$')

    # ISO datetime: YYYY-MM-DD optionally followed by T or space + time
    ISO_DATETIMEISH = re.compile(
        r'^[0-9]{4}[-/][0-9]{1,2}[-/][0-9]{1,2}([ T].*)?$$'
    )

    # ISO separator extraction: captures the date separator
    SEP_ISO = re.compile(
        r'^[0-9]{4}([-/])[0-9]{1,2}[-/][0-9]{1,2}([ T].*)?$'
    )

    # Detect fractional seconds: colon + 2 digits + decimal point + digit
    HAS_FRAC = re.compile(r':[0-9]{2}\.[0-9]')

    # Non-ISO, 4-digit year at end: DD/MM/YYYY or MM/DD/YYYY + optional time
    DATEISH4Y = re.compile(
        r'^([0-9]{1,2})[-./]([0-9]{1,2})[-./]([0-9]{4})'
        r'(.[0-9]{2}[:.][0-9]{2}[:.][0-9]{2}(\.[0-9]+)?)?$'
    )

    # Non-ISO, 2-digit year at end: DD/MM/YY or MM/DD/YY + optional time
    DATEISH2Y = re.compile(
        r'^([0-9]{1,2})[-./]([0-9]{1,2})[-./]([0-9]{2})'
        r'(.[0-9]{2}[:.][0-9]{2}[:.][0-9]{2}(\.[0-9]+)?)?$'
    )

    # Separator extraction for 4-digit-year-at-end dates
    SEPS4Y = re.compile(
        r'[0-9]{1,2}([-./])[0-9]{1,2}[-./][0-9]{4}'
        r'((.)[0-9]{2}([:.])[0-9]{2}[:.][0-9]{2}(\.[0-9]+)?)?$'
    )

    # Separator extraction for 2-digit-year-at-end dates
    SEPS2Y = re.compile(
        r'^[0-9]{1,2}([-./])[0-9]{1,2}[-./][0-9]{2}'
        r'((.)[0-9]{2}([:.])[0-9]{2}[:.][0-9]{2}(\.[0-9]+)?)?$'
    )


# Sentinel return value for ISO datetimes from infer_date_format (pddates)
ISODT = 'ISO8601'


class AmbiguousDateFormat:
    """
    Return values from infer_date_format_from_strings when the day/month
    order cannot be determined (all values <= 12) but year size and time
    presence are known.
    """
    EU_OR_US_DATE = 'eu-or-us-date'
    EU_OR_US_DATETIME = 'eu-or-us-datetime'
    EU_OR_US_DATE_2Y = 'eu-or-us-date-2y'
    EU_OR_US_DATETIME_2Y = 'eu-or-us-datetime-2y'


AMBIGUOUS_DATE_FORMATS = frozenset({
    AmbiguousDateFormat.EU_OR_US_DATE,
    AmbiguousDateFormat.EU_OR_US_DATETIME,
    AmbiguousDateFormat.EU_OR_US_DATE_2Y,
    AmbiguousDateFormat.EU_OR_US_DATETIME_2Y,
})

# Named tuple for separator information extracted from a date/time string
Separators = namedtuple(
    'Separators', 'date_sep date_time_sep time_sep has_time has_frac time_part'
)


# ── Functions ─────────────────────────────────────────────────────────────────

def get_date_separators(r, s):
    """
    Extract date and time separator characters from a date/datetime string.

    Args:
        r: compiled regex (SEPS4Y or SEPS2Y) to use for matching
        s: date/datetime string to parse

    Returns:
        Separators namedtuple, or None if s doesn't match r.

    Note: groups are the same for both SEPS4Y and SEPS2Y:
        group 1: date separator (- / .)
        group 2: full time portion (if present)
        group 3: date-time separator (T, space, : etc.)
        group 4: time separator (: or .)
        group 5: fractional seconds (if present)
    """
    m = re.match(r, s)
    if m is None:
        return None
    dsep = m.group(1)
    time_component = m.group(2) is not None
    time_part = frac = ''
    dtsep = tsep = None
    if time_component:
        dtsep = m.group(3)
        tsep = m.group(4)
        frac = '.%f' if m.group(5) else ''
        time_part = '%s%%H%s%%M%s%%S%s' % (dtsep, tsep, tsep, frac)
    return Separators(dsep, dtsep, tsep, time_component, frac != '', time_part)


def infer_date_format_from_strings(strings):
    """
    Infer the date/datetime format from a list of string values.

    Args:
        strings: list of non-null string values believed to be dates

    Returns:
        A strftime format string preserving the actual separators found
        in the data (e.g. '%d-%m-%Y', '%m/%d/%Y %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S'), or None if the format cannot be determined
        (e.g. ambiguous EU vs US with all values having both parts <= 12).
    """
    if not strings:
        return None
    if not all(re.match(DateRE.DATEISH, s) for s in strings):
        return None

    # ── ISO: year-first ───────────────────────────────────────────────────────
    if all(re.match(DateRE.ISO_DATEISH, s) for s in strings):
        m = re.match(DateRE.SEP_ISO, strings[0])
        assert m
        sep = m.group(1)
        return '%%Y%s%%m%s%%d' % (sep, sep)

    if all(re.match(DateRE.ISO_DATETIMEISH, s) for s in strings):
        # Preserve date separator and T/space; detect fractional seconds
        m = re.match(DateRE.SEP_ISO, strings[0])
        assert m
        sep = m.group(1)
        dtsep = 'T' if 'T' in strings[0] else ' '
        frac = '.%f' if any(re.search(DateRE.HAS_FRAC, s) for s in strings) else ''
        return '%%Y%s%%m%s%%d%s%%H:%%M:%%S%s' % (sep, sep, dtsep, frac)

    # ── 4-digit year at end (EU or US) ────────────────────────────────────────
    matches = [re.match(DateRE.DATEISH4Y, s) for s in strings]
    if all(matches):
        seps = get_date_separators(DateRE.SEPS4Y, strings[0])
        if seps is None:
            return None
        m1 = max(int(m.group(1)) for m in matches)
        m2 = max(int(m.group(2)) for m in matches)
        dsep = seps.date_sep
        if m1 > 12 and m2 <= 12:  # Euro: day first
            return ('%%d%s%%m%s%%Y' % (dsep, dsep)) + seps.time_part
        elif m1 <= 12 and m2 > 12:  # US: month first
            return ('%%m%s%%d%s%%Y' % (dsep, dsep)) + seps.time_part
        # ambiguous: both parts <= 12 across all rows
        if seps.has_time:
            return AmbiguousDateFormat.EU_OR_US_DATETIME
        return AmbiguousDateFormat.EU_OR_US_DATE

    # ── 2-digit year at end (EU or US) ────────────────────────────────────────
    matches = [re.match(DateRE.DATEISH2Y, s) for s in strings]
    if all(matches):
        seps = get_date_separators(DateRE.SEPS2Y, strings[0])
        if seps is None:
            return None
        m1 = max(int(m.group(1)) for m in matches)
        m2 = max(int(m.group(2)) for m in matches)
        dsep = seps.date_sep
        if m1 > 12 and m2 <= 12:  # Euro 2Y
            return ('%%d%s%%m%s%%y' % (dsep, dsep)) + seps.time_part
        elif m1 <= 12 and m2 > 12:  # US 2Y
            return ('%%m%s%%d%s%%y' % (dsep, dsep)) + seps.time_part
        # ambiguous
        if seps.has_time:
            return AmbiguousDateFormat.EU_OR_US_DATETIME_2Y
        return AmbiguousDateFormat.EU_OR_US_DATE_2Y

    return None
