def nvl(v, w):
    """
    This function is used as syntactic sugar for replacing null values.
    """
    return w if v is None else v
