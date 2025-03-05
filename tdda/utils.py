import os

def nvl(v, w):
    """
    This function is used as syntactic sugar for replacing null values.
    """
    return w if v is None else v


def handle_tilde(path):
    """
    Handle paths starting tilde.

    Does nothing unless path is a string and starts with '~'
    """
    if type(path) is str and path.startswith('~'):
        return os.path.expanduser(path)
    else:
        return path


def DQuote(string, escape=True):
    parts = string.split('"')
    if escape:
        parts = [p.replace('\\', r'\\').replace('\n', r'\n') for p in parts]
    quoted = ('\\"').join(parts)
    return '"%s"' % quoted


class Dummy(object):
    """
    A dummy object. For whatever.
    """
    def __init__(self, **kwargs):
        for k in kwargs:
            self.__dict__[k] = kwargs[k]

    def to_dict(self):
        return self.__dict__
