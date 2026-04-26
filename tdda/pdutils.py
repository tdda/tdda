from tdda.utils import valid_level


def pandas_string_type(t):
    if type(t):
        s = str(t)
        if s.startswith('<'):
            s = (
                s.split('.')[-1]
                .replace('Dtype', '')
                .replace('_', '')
                .replace("'>", '')
            )
    else:
        s = t
    return s


def loosen_pandas_type(t):
    t = pandas_string_type(t)
    name = ''.join(c for c in t if not c.isdigit()).lower()
    p = name.find('[')
    name = name[:p] if p > -1 else name
    if name == 'boolean':
        return 'bool'
    if name == 'str':
        return 'string'
    return name


def pandas_types_match(t1, t2, level=None):
    level = valid_level(level)
    t1i = t1
    t2i = t2
    t1, t2 = pandas_string_type(t1), pandas_string_type(t2)
    if level == 'strict' or t1 == t2:
        if t1.lower() == t2.lower() and t1.lower().startswith('float'):
            return True  # Float64 and float64 are not meaningfully different
        if t1.startswith('datetime') and t2.startswith('datetime'):
            return True  # us, ns and even ms OK.
        return t1 == t2

    t1loose = loosen_pandas_type(t1)
    t2loose = loosen_pandas_type(t2)
    object_types = ('string', 'boolean', 'datetime', 'bool')
    if (
        t1loose == t2loose
        or t1loose == 'object'
        and t2loose in object_types
        or t2loose == 'object'
        and t1loose in object_types
    ):
        return True

    numeric_types = {'bool', 'boolean', 'int', 'float'}
    if (
        level == 'loose'
        and t1loose in numeric_types
        and t2loose in numeric_types
    ):
        return True
    return False
