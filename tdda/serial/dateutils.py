"""
Date format inference utilities for flat-file (CSV) metadata.

Provides regex patterns and functions for detecting date and datetime
formats from lists of string values, with no pandas dependency.
"""

import re

from collections import namedtuple


# ── Month name sets ───────────────────────────────────────────────────────────

MONTH_ABBREVS = frozenset({
    'jan', 'feb', 'mar', 'apr', 'may', 'jun',
    'jul', 'aug', 'sep', 'oct', 'nov', 'dec',
})

MONTH_FULLS = frozenset({
    'january', 'february', 'march', 'april', 'may', 'june',
    'july', 'august', 'september', 'october', 'november', 'december',
})


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
    SEP_ISO = re.compile(r'^[0-9]{4}([-/])[0-9]{1,2}[-/][0-9]{1,2}([ T].*)?$')

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

    # Alpha-month patterns: backreference \2 ensures consistent separator.
    # Groups: see infer_alpha_date_format for layout.
    ALPHA_DMY = re.compile(  # dd-Mon-yyyy or dd Mon yyyy
        r'^([0-9]{1,2})([-. /])([a-zA-Z]{3,9})\2([0-9]{2,4})'
        r'(?:([ T])([0-9]{2}:[0-9]{2}:[0-9]{2})(\.[0-9]+)?)?$'
    )
    ALPHA_MDY = re.compile(  # Mon-dd-yyyy or Mon dd yyyy
        r'^([a-zA-Z]{3,9})([-. /])([0-9]{1,2})\2([0-9]{2,4})'
        r'(?:([ T])([0-9]{2}:[0-9]{2}:[0-9]{2})(\.[0-9]+)?)?$'
    )
    ALPHA_YMD = re.compile(  # yyyy-Mon-dd or yyyy Mon dd
        r'^([0-9]{4})([-. /])([a-zA-Z]{3,9})\2([0-9]{1,2})'
        r'(?:([ T])([0-9]{2}:[0-9]{2}:[0-9]{2})(\.[0-9]+)?)?$'
    )
    ALPHA_MDY_COMMA = re.compile(  # Mon dd, yyyy  (US prose style)
        r'^([a-zA-Z]{3,9}) ([0-9]{1,2}), ([0-9]{2,4})'
        r'(?:([ T])([0-9]{2}:[0-9]{2}:[0-9]{2})(\.[0-9]+)?)?$'
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


AMBIGUOUS_DATE_FORMATS = frozenset(
    {
        AmbiguousDateFormat.EU_OR_US_DATE,
        AmbiguousDateFormat.EU_OR_US_DATETIME,
        AmbiguousDateFormat.EU_OR_US_DATE_2Y,
        AmbiguousDateFormat.EU_OR_US_DATETIME_2Y,
    }
)

# Named tuple for separator information extracted from a date/time string
Separators = namedtuple(
    'Separators', 'date_sep date_time_sep time_sep has_time has_frac time_part'
)


# ── Functions ─────────────────────────────────────────────────────────────────


def _is_valid_month(s):
    """Return True if s (lowercased) is a valid English month name."""
    return s in MONTH_ABBREVS or s in MONTH_FULLS


def _alpha_month_code(month_str):
    """Return '%b' for 3-char abbreviations, '%B' for full month names."""
    return '%b' if len(month_str) == 3 else '%B'


def _alpha_time_part(m):
    """
    Build strftime time suffix from an alpha-date match.

    Groups 5-7 are the optional time components: datetime separator,
    HH:MM:SS, and fractional seconds.
    """
    if m.group(5) is None:
        return ''
    frac = '.%f' if m.group(7) else ''
    return '%s%%H:%%M:%%S%s' % (m.group(5), frac)


def infer_alpha_date_format(strings):
    """
    Infer strftime format for dates with alphabetical month names.

    Handles three field orderings with any of -, /, . as separator:
      - day-first:   dd-Mon-yyyy  → %d-%b-%Y  (or %B for full names)
      - month-first: Mon-dd-yyyy  → %b-%d-%Y
      - year-first:  yyyy-Mon-dd  → %Y-%b-%d

    Also handles optional HH:MM:SS time components and 2-digit years.
    Month names must be valid English abbreviations or full names.

    Args:
        strings: list of non-null string values believed to be dates

    Returns:
        strftime format string, or None if strings don't match.
    """
    # Mon dd, yyyy  (US prose — comma after day, groups differ from others)
    matches = [DateRE.ALPHA_MDY_COMMA.match(s) for s in strings]
    if all(matches):
        if all(_is_valid_month(m.group(1).lower()) for m in matches):
            m0 = matches[0]
            mon_code = _alpha_month_code(m0.group(1))
            yr_code = '%Y' if len(m0.group(3)) == 4 else '%y'
            # time groups are 4 (dtsep), 5 (HH:MM:SS), 6 (frac)
            if m0.group(4) is None:
                time_part = ''
            else:
                frac = '.%f' if m0.group(6) else ''
                time_part = '%s%%H:%%M:%%S%s' % (m0.group(4), frac)
            return '%s %%d, %s%s' % (mon_code, yr_code, time_part)

    # (pattern, day_group, mon_group, yr_group)
    candidates = [
        (DateRE.ALPHA_DMY, 1, 3, 4),
        (DateRE.ALPHA_MDY, 3, 1, 4),
        (DateRE.ALPHA_YMD, 4, 3, 1),
    ]
    for pattern, day_grp, mon_grp, yr_grp in candidates:
        matches = [pattern.match(s) for s in strings]
        if not all(matches):
            continue
        if not all(_is_valid_month(m.group(mon_grp).lower()) for m in matches):
            continue
        m0 = matches[0]
        sep = m0.group(2)
        mon_code = _alpha_month_code(m0.group(mon_grp))
        yr_code = '%Y' if len(m0.group(yr_grp)) == 4 else '%y'
        time_part = _alpha_time_part(m0)
        if pattern is DateRE.ALPHA_DMY:
            base = '%%d%s%s%s%s' % (sep, mon_code, sep, yr_code)
        elif pattern is DateRE.ALPHA_MDY:
            base = '%s%s%%d%s%s' % (mon_code, sep, sep, yr_code)
        else:
            base = '%s%s%s%s%%d' % (yr_code, sep, mon_code, sep)
        return base + time_part
    return None


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


def resolve_ambiguous_format(strings, ambig_fmt, convention='eu'):
    """
    Resolve an ambiguous date/datetime format to a concrete strftime string,
    using the given day/month convention.

    Args:
        strings:    list of date strings from the field (used to extract
                    the date and time separators)
        ambig_fmt:  one of the AmbiguousDateFormat.* constants
        convention: 'eu' (day-first) or 'us' (month-first)

    Returns:
        strftime format string, or None if separators cannot be extracted.
    """
    if ambig_fmt in (
        AmbiguousDateFormat.EU_OR_US_DATE,
        AmbiguousDateFormat.EU_OR_US_DATETIME,
    ):
        seps_re, year_code = DateRE.SEPS4Y, 'Y'
    elif ambig_fmt in (
        AmbiguousDateFormat.EU_OR_US_DATE_2Y,
        AmbiguousDateFormat.EU_OR_US_DATETIME_2Y,
    ):
        seps_re, year_code = DateRE.SEPS2Y, 'y'
    else:
        return None
    seps = get_date_separators(seps_re, strings[0])
    if seps is None:
        return None
    dsep = seps.date_sep
    if convention == 'eu':
        base = '%%d%s%%m%s%%%s' % (dsep, dsep, year_code)
    else:
        base = '%%m%s%%d%s%%%s' % (dsep, dsep, year_code)
    return base + seps.time_part


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
    alpha_fmt = infer_alpha_date_format(strings)
    if alpha_fmt is not None:
        return alpha_fmt
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
        frac = (
            '.%f'
            if any(re.search(DateRE.HAS_FRAC, s) for s in strings)
            else ''
        )
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
