from collections import namedtuple
import re

class DateRE:
    DATEISH = re.compile(r'^[0-9]{1,4}[-./][0-9]{1,2}[-/][0-9]{1,2}.*$')
    ISO_DATEISH = re.compile(r'^[0-9]{4}[-/][0-9]{1,2}[-/][0-9]{1,2}$')
    ISO_DATETIMEISH = re.compile(r'^[0-9]{4}[-/][0-9]{1,2}[-/][0-9]{1,2}([ T].*)?$$')
    SEP_ISO = re.compile(
        r'^[0-9]{4}([-/])[0-9]{1,2}[-/][0-9]{1,2}([ T].*)?$')
    DATEISH4Y = re.compile(
        r'^([0-9]{1,2})[-./]([0-9]{1,2})[-/]([0-9]{4})'
        r'(.[0-9]{2}[:.][0-9]{2}[:.][0-9]{2}(\.[0-9]+)?)?$'
    )
    DATEISH2Y = re.compile(
        r'^([0-9]{1,2})[-./]([0-9]{1,2})[-/]([0-9]{2})'
        r'(.[0-9]{2}[:.][0-9]{2}[:.][0-9]{2}(\.[0-9]+)?)?$'
    )
    SEPS4Y = re.compile(
        r'[0-9]{1,2}([-./])[0-9]{1,2}[-/][0-9]{4}'
        r'((.)[0-9]{2}([:.])[0-9]{2}[:.][0-9]{2}(\.[0-9]+)?)?$'
    )
    SEPS2Y = re.compile(
        r'^[0-9]{1,2}([-./])[0-9]{1,2}[-/][0-9]{2}'
        r'((.)[0-9]{2}([:.])[0-9]{2}[:.][0-9]{2}(\.[0-9]+)?)?$'
    )


Separators = namedtuple(
    'Separators',
    'date_sep date_time_sep time_sep has_time has_frac time_part')


ISODT = 'ISO8601'


def infer_date_format(col, n=100):
    nonnulls = col.dropna()
    if nonnulls.size == 0:
        return None             # All null

    strings = nonnulls[:n].to_list()  # first n non-null strings
    if not strings:
        return None
    if type(strings[0]) != str:
        return None

    if not all(re.match(DateRE.DATEISH, s) for s in strings):
        return None    # Don't look like dates at all

    if all(re.match(DateRE.ISO_DATEISH, s) for s in strings):
        # all isodates
        m = re.match(DateRE.SEP_ISO, strings[0])
        assert m
        sep = m.group(1)
        fmt = '%%Y%s%%m%s%%d' % (sep, sep)
        return fmt
    elif all(re.match(DateRE.ISO_DATETIMEISH, s) for s in strings):
        return ISODT


    matches = [re.match(DateRE.DATEISH4Y, s) for s in strings]
    if all(matches):
        time_component = any(m.group(4) for m in matches)
        seps = get_date_separators(DateRE.SEPS4Y, strings[0])
        m1 = max(int(m.group(1)) for m in matches)
        m2 = max(int(m.group(2)) for m in matches)
        assert seps is not None
        dsep = seps.date_sep
        if m1 <= 12 and m2 > 12:  # US
            date_part = '%%m%s%%d%s%%Y' % (dsep, dsep)
            return date_part + seps.time_part
        elif m1 > 12 and m2 <= 12:  # EURO
            date_part = '%%d%s%%m%s%%Y' % (dsep, dsep)
            return date_part + seps.time_part
        elif m1 <= 12 and m2 <= 12:
            if nonnulls.size > n:
                return simple_infer_datetime_format(col, n * 10)
        return None

    matches = [re.match(DateRE.DATEISH2Y, s) for s in strings]
    if all(matches):
        time_component = any(m.group(4) for m in matches)
        seps = get_date_separators(DateRE.SEPS2Y, strings[0])
        m1 = max(int(m.group(1)) for m in matches)
        m2 = max(int(m.group(2)) for m in matches)
        assert seps is not None
        dsep = seps.date_sep
        if m1 <= 12 and m2 > 12:  # US
            date_part = '%%m%s%%d%s%%y' % (dsep, dsep)
            return date_part + seps.time_part
        elif m1 > 12 and m2 <= 12:  # EURO
            date_part = '%%d%s%%m%s%%y' % (dsep, dsep)
            return date_part + seps.time_part
        elif m1 <= 12 and m2 <= 12:
            if nonnulls.size > n:
                return simple_infer_datetime_format(col, n * 10)
        return None
    return None


def get_date_separators(r, s):
    m = re.match(DateRE.SEPS4Y, s)
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
