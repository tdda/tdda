from tdda.utils import valid_level


def loosen_polars_type(t, level):
    t = str(t)
    level = valid_level(level)
    if level == 'strict':
        return 'String' if t == 'Utf8' else t

    if t.startswith('Float') or t.startswith('Decimal'):
        t = 'Float'
    elif t.startswith('Int') or t.startswith('UInt'):
        t = 'Int'
    elif t.startswith('Date'):
        t = 'Date'
    elif t in ('Categorical', 'Enum', 'Utf8'):
        t = 'String'

    if level == 'loose':
        if t in {'Float', 'Int', 'Boolean'}:
            return 'Numeric'

    return t


def polars_types_match(t1, t2, level=None):
    return loosen_polars_type(t1, level) == loosen_polars_type(t2, level)
