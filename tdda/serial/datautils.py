import datetime

import pandas as pd
import polars as pl

def tiny_python_values(nulls=False, sNullNull=False, euroStrDates=False,
                       sBools=False):
    """
    Generate tiny 5x2 or 5x3 set of values for a DataFrame
    with Python booleans, integers, floats, strings and dates.

    If nulls is True, the second row (row 1) is all null
    and there are three rows.

    Otherwise, there are two, non-null rows.
    """
    nil = None if sNullNull else ''
    if euroStrDates:
        d1 = '31/01/1970'
        d2 = '31/12/1999'
    else:
        d1 = datetime.datetime(1970, 1, 31)
        d2 = datetime.datetime(1999, 12, 31)
    if sBools:
        f, t = 'n', 'Yes'
    else:
        f, t = False, True
    values = {
        'b': [f, t],
        'i': [0, 1],
        'f': [0.5, 1.5],
        's': [nil, 'a'],
#        'd': [datetime.date(1970, 1, 1), datetime.date(1999, 12, 31)]
        't': [d1, d2]
    }
    if nulls:
        values = {
            k: v[:1] + [None] + v[1:]
            for k, v in values.items()
        }
    return values


def tiny_pandas_df(nulls=False, nullable_types=False):
    if nullable_types:
        return pd.DataFrame({
            k: pd.Series(v, dtype=pd_nullable_type(k))
            for k, v in tiny_python_values(nulls=nulls).items()
        })
    else:
        return pd.DataFrame(tiny_python_values(nulls=nulls))


def tiny_polars_df(nulls=False, sNullNull=False, euroStrDates=False,
                   sBools=False):
    return pl.DataFrame(tiny_python_values(nulls=nulls, sNullNull=sNullNull,
                        euroStrDates=euroStrDates, sBools=sBools))



def pd_nullable_type(name):
    d = {
        'b': 'boolean',
        'i': 'Int64',
        'f': 'float',
        'r': 'float',
        's': 'string',
        'd': 'datetime64[ns]',
        't': 'datetime64[ns]',
    }
    return d[name[:1].lower()]

