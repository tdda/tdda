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
