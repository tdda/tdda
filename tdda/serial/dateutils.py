"""
Date format utilities for flat-file (CSV) metadata in tdda.serial.

Covers two related concerns:

  Inference: detecting date/datetime formats from lists of string values
             (infer_date_format_from_strings and helpers).

  Formats:   parsing, translating and canonicalizing the four format styles
             supported in .serial files:

               isodate:     Named ISO8601 variants  (iso8601-date, ...)
               yyyydate:    Component tokens        (YYYY-MM-DD, HH:MM:SS)
               literaldate: Unambiguous date/time   (31/12/2000, 12:34:56PM)
               pcdate:      Python strftime strings (%Y-%m-%d, %H:%M:%S)

             Internally, % strings are used as the pivot format (needed by
             pandas/polars).  The canonical literaldate date is
             2000-12-31T12:34:56.789 — every component is unambiguous
             (day=31>12, month=12>12, year=2000 4-digit, hour=12=noon/PM).
"""

import datetime
import re

from collections import namedtuple


# ── Month name sets ───────────────────────────────────────────────────────────

MONTH_ABBREVS = frozenset(
    {
        'jan',
        'feb',
        'mar',
        'apr',
        'may',
        'jun',
        'jul',
        'aug',
        'sep',
        'oct',
        'nov',
        'dec',
    }
)

MONTH_FULLS = frozenset(
    {
        'january',
        'february',
        'march',
        'april',
        'may',
        'june',
        'july',
        'august',
        'september',
        'october',
        'november',
        'december',
    }
)


# ── ISO8601 named format names ────────────────────────────────────────────────

ISO_FORMAT_NAMES = frozenset(
    {
        'iso8601-date',
        'iso8601-datetime',
        'iso8601-datetime-tz',
        'iso8601',
    }
)

# ── Canonical date/time used for literaldate normalization ───────────────────

CANONICAL_DT = datetime.datetime(
    2000, 12, 31, 12, 34, 56, 789000, tzinfo=datetime.timezone.utc
)


# ── Regex patterns: inference ─────────────────────────────────────────────────


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
    # Date-time separator allows space, T, or : (colon covers Apache format).
    ALPHA_DMY = re.compile(  # dd-Mon-yyyy or dd Mon yyyy
        r'^([0-9]{1,2})([-. /])([a-zA-Z]{3,9})\2([0-9]{2,4})'
        r'(?:([ T:])([0-9]{2}:[0-9]{2}:[0-9]{2})(\.[0-9]+)?)?$'
    )
    ALPHA_MDY = re.compile(  # Mon-dd-yyyy or Mon dd yyyy
        r'^([a-zA-Z]{3,9})([-. /])([0-9]{1,2})\2([0-9]{2,4})'
        r'(?:([ T:])([0-9]{2}:[0-9]{2}:[0-9]{2})(\.[0-9]+)?)?$'
    )
    ALPHA_YMD = re.compile(  # yyyy-Mon-dd or yyyy Mon dd
        r'^([0-9]{4})([-. /])([a-zA-Z]{3,9})\2([0-9]{1,2})'
        r'(?:([ T:])([0-9]{2}:[0-9]{2}:[0-9]{2})(\.[0-9]+)?)?$'
    )
    ALPHA_MDY_COMMA = re.compile(  # Mon dd, yyyy  (US prose style)
        r'^([a-zA-Z]{3,9}) ([0-9]{1,2}), ([0-9]{2,4})'
        r'(?:([ T])([0-9]{2}:[0-9]{2}:[0-9]{2})(\.[0-9]+)?)?$'
    )


# ── Regex patterns: format style detection ───────────────────────────────────

# Longer alternatives first: YYYY before YY, MONTH before MON, SS.S+ before SS
_TOKEN_SPLIT_RE = re.compile(
    r'(yyyy|yy|month|mon|mm|dd|hh|ss\.s+|ss|am|pm|[+-]zz:zz|[+-]zzzz)',
    re.IGNORECASE,
)

_HAS_TOKEN_RE = re.compile(
    r'yyyy|yy|month|mon|mm|dd|hh|ss\.s+|ss|am|pm|[+-]zz:zz|[+-]zzzz',
    re.IGNORECASE,
)

# Time-only literaldate: HH:MM:SS or HH.MM.SS, optional frac (no AM/PM —
# AM/PM is stripped before this is applied)
_TIME_ONLY_RE = re.compile(
    r'^(\d{1,2})([:.])\d{2}\2\d{2}(\.\d+)?$',
)

# Timezone suffix in literaldate examples: +HHMM, +HH:MM, -HHMM, -HH:MM
# (optionally preceded by a space, as in Apache format: 12:34:56 +0000)
_TZ_SUFFIX_RE = re.compile(r' ?[+-]\d{4}$| ?[+-]\d{2}:\d{2}$')

# strftime code → yyyydate token; longest/most-specific substitutions first
_STRFTIME_TO_TOKEN = [
    ('%S.%f', 'SS.SSS'),
    ('%Y', 'YYYY'),
    ('%y', 'YY'),
    ('%m', 'MM'),
    ('%M', 'MM'),
    ('%d', 'DD'),
    ('%H', 'HH'),
    ('%I', 'HH'),
    ('%S', 'SS'),
    ('%p', 'PM'),
    ('%z', '+ZZ:ZZ'),
    ('%b', 'MON'),
    ('%B', 'MONTH'),
]


# ── Inference support types ───────────────────────────────────────────────────

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


# ── Inference functions ───────────────────────────────────────────────────────


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


# ── Format style detection ────────────────────────────────────────────────────


def detect_format_style(s):
    """
    Return the style of a date format string.

    Returns one of: 'isodate', 'yyyydate', 'literaldate', 'pcdate'.

    Args:
        s (str): date format string

    Raises:
        ValueError: if s is empty.
    """
    if not s:
        raise ValueError('Empty date format string')
    if s.startswith('%'):
        return 'pcdate'
    if s.lower() in ISO_FORMAT_NAMES:
        return 'isodate'
    if _HAS_TOKEN_RE.search(s):
        return 'yyyydate'
    return 'literaldate'


# ── Inward converters (any style → %) ────────────────────────────────────────


def yyyydate_to_strftime(s):
    """
    Convert a yyyydate token format string to a strftime format string.

    Token strings use YYYY, MM, DD, HH, SS etc. as placeholders.
    MM is resolved to month or minute by context (adjacent tokens).

    Args:
        s (str): token format such as 'YYYY-MM-DD HH:MM:SS'

    Returns:
        strftime format string such as '%Y-%m-%d %H:%M:%S'

    Raises:
        ValueError: if s contains no tokens or MM context is unresolvable.
    """
    parts = _TOKEN_SPLIT_RE.split(s)
    tokens_raw = [parts[i].upper() for i in range(1, len(parts), 2)]
    seps = [parts[i] for i in range(0, len(parts), 2)]

    if not tokens_raw:
        raise ValueError('No date tokens found: %r' % s)

    has_ampm = any(t in ('AM', 'PM') for t in tokens_raw)
    resolved = _resolve_mm(tokens_raw, s)

    result = [seps[0]]
    for i, t in enumerate(resolved):
        result.append(_token_to_strftime(t, has_ampm))
        result.append(seps[i + 1])
    return ''.join(result)


def literaldate_to_strftime(s):
    """
    Convert a literaldate unambiguous example date/time to a strftime format.

    The example must satisfy:
      - For numeric day/month, one must be > 12.
      - Two-digit years must be 00 or >= 60.

    Handles Apache-style bracket-wrapped dates: [31/Dec/2000:12:34:56 +0000]

    Args:
        s (str): example such as '31/12/2000', '12:34:56PM',
                 or '[31/Dec/2000:12:34:56 +0000]'

    Returns:
        strftime format string

    Raises:
        ValueError: if the example is ambiguous or unrecognisable.
    """
    s = s.strip()
    bracketed, s = _strip_brackets(s)
    ampm, s_bare = _strip_ampm(s)

    m = _TIME_ONLY_RE.match(s_bare)
    if m:
        fmt = _time_only_strftime(m, ampm is not None)
        return ('[' + fmt + ']') if bracketed else fmt

    has_tz, s_bare = _strip_tz(s_bare)

    fmt = infer_date_format_from_strings([s_bare])
    if fmt is None:
        raise ValueError('Unrecognized date format: %r' % s)
    if fmt in AMBIGUOUS_DATE_FORMATS:
        raise ValueError(
            'Ambiguous date example (day/month order unclear): %r' % s
        )

    if has_tz:
        fmt += '%z'

    _check_two_digit_year(s_bare, fmt)

    if ampm is not None:
        fmt = fmt.replace('%H', '%I') + '%p'

    return ('[' + fmt + ']') if bracketed else fmt


def to_strftime(s):
    """
    Convert any date format style to a strftime format string.

    isodate formats are passed through unchanged (caller should resolve
    them via serial_format_to_strftime in metadata.py if needed).

    Args:
        s (str): format string in any style, or None.

    Returns:
        strftime format string, or None if s is None.
    """
    if s is None:
        return None
    style = detect_format_style(s)
    if style == 'pcdate':
        return s
    if style == 'isodate':
        return s  # caller resolves via serial_format_to_strftime
    if style == 'yyyydate':
        return yyyydate_to_strftime(s)
    return literaldate_to_strftime(s)


# ── Outward converters (% → other styles) ────────────────────────────────────


def strftime_to_yyyydate(s):
    """
    Convert a strftime format string to a yyyydate token string.

    Used when writing .serial files with --use-yyyy-dates.

    Args:
        s (str): strftime format such as '%Y-%m-%d %H:%M:%S'

    Returns:
        yyyydate token string such as 'YYYY-MM-DD HH:MM:SS'
    """
    result = s
    for code, token in _STRFTIME_TO_TOKEN:
        result = result.replace(code, token)
    return result


def strftime_to_literaldate(s):
    """
    Convert a strftime format string to a canonicalized literaldate string.

    Applies the format to the canonical datetime (2000-12-31T12:34:56.789+0000)
    to produce a concrete date string in the target format.

    Used when writing .serial files with --use-literal-dates.

    Args:
        s (str): strftime format such as '%d/%m/%Y'

    Returns:
        canonical example string such as '31/12/2000'
    """
    return CANONICAL_DT.strftime(s)


def canonicalize_date_format(s):
    """
    Canonicalize a date format string, preserving its style.

    - yyyydate:    uppercase  (YYYY-MM-DD, not yyyy-mm-dd)
    - literaldate: replace date components with canonical values
    - isodate and pcdate: returned unchanged

    Args:
        s (str): date format string in any style.

    Returns:
        canonicalized format string in the same style.
    """
    if s is None:
        return None
    style = detect_format_style(s)
    if style == 'yyyydate':
        return s.upper()
    if style == 'literaldate':
        fmt = literaldate_to_strftime(s)
        return strftime_to_literaldate(fmt)
    return s


# ── Private helpers ───────────────────────────────────────────────────────────


def _strip_brackets(s):
    """
    Strip outer [ ] from s if present.

    Returns:
        (bracketed, bare): bracketed is True if brackets were found.
    """
    if s.startswith('[') and s.endswith(']'):
        return True, s[1:-1]
    return False, s


def _strip_tz(s):
    """
    Strip a trailing timezone suffix from s (e.g. '+0000', ' +00:00').

    Returns:
        (has_tz, bare): has_tz is True if a TZ suffix was stripped.
    """
    m = _TZ_SUFFIX_RE.search(s)
    if m:
        return True, s[: m.start()]
    return False, s


def _strip_ampm(s):
    """
    Strip a trailing AM/PM suffix (with optional preceding space) from s.

    Returns:
        (ampm, bare): ampm is 'am'/'pm' or None; bare is s without the suffix.
    """
    lower = s.lower()
    for suffix in (' pm', ' am', 'pm', 'am'):
        if lower.endswith(suffix):
            return suffix.strip(), s[: len(s) - len(suffix)].rstrip()
    return None, s


def _resolve_mm(tokens, original):
    """
    Resolve each MM token to NUMMON or MINUTE based on adjacent tokens.

    MM adjacent to YYYY/YY/DD/MON/MONTH → NUMMON (numeric month).
    MM adjacent to HH/SS*               → MINUTE.
    """
    resolved = list(tokens)
    for i, t in enumerate(tokens):
        if t != 'MM':
            continue
        prev = tokens[i - 1] if i > 0 else None
        nxt = tokens[i + 1] if i < len(tokens) - 1 else None
        if _is_date_tok(prev) or _is_date_tok(nxt):
            resolved[i] = 'NUMMON'
        elif _is_time_tok(prev) or _is_time_tok(nxt):
            resolved[i] = 'MINUTE'
        else:
            raise ValueError(
                'Cannot determine if MM is month or minute in: %r' % original
            )
    return resolved


def _is_date_tok(t):
    return t in ('YYYY', 'YY', 'DD', 'MON', 'MONTH')


def _is_time_tok(t):
    return t == 'HH' or (t is not None and t.startswith('SS'))


def _token_to_strftime(t, has_ampm):
    if t == 'YYYY':
        return '%Y'
    if t == 'YY':
        return '%y'
    if t == 'NUMMON':
        return '%m'
    if t == 'MINUTE':
        return '%M'
    if t == 'DD':
        return '%d'
    if t == 'MON':
        return '%b'
    if t == 'MONTH':
        return '%B'
    if t == 'HH':
        return '%I' if has_ampm else '%H'
    if t.startswith('SS.'):
        return '%S.%f'
    if t == 'SS':
        return '%S'
    if t in ('AM', 'PM'):
        return '%p'
    if t.endswith('ZZ:ZZ'):
        return '%z'
    if t.endswith('ZZZZ'):
        return '%z'
    raise ValueError('Unknown token: %r' % t)


def _time_only_strftime(m, has_ampm):
    sep = m.group(2)
    frac = '.%f' if m.group(3) is not None else ''
    hour = '%I' if has_ampm else '%H'
    ampm_code = '%p' if has_ampm else ''
    return '%s%s%%M%s%%S%s%s' % (hour, sep, sep, frac, ampm_code)


def _check_two_digit_year(s, fmt):
    """
    Raise ValueError if fmt uses %y and the year value in s is ambiguous
    (not 00 and < 60).
    """
    if '%y' not in fmt:
        return
    try:
        dt = datetime.datetime.strptime(s, fmt)
    except ValueError:
        return
    yr2 = dt.year % 100
    if yr2 != 0 and yr2 < 60:
        raise ValueError(
            'Ambiguous 2-digit year %02d in %r (must be 00 or >= 60)'
            % (yr2, s)
        )
