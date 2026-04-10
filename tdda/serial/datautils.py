import datetime

from collections import namedtuple

import pandas as pd
import polars as pl


Names = namedtuple('Names', 'b i f s t')

LONG_NAMES = ['IAmBoolean', 'IAmInt', 'f', 'IAmString', 'IAmDate']


def tiny_python_values(
    nulls=False,
    sNullNull=False,
    euroStrDates=False,
    sBools=False,
    longNames=False,
):
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

    if longNames:
        names = Names(*LONG_NAMES)
    else:
        names = Names('b', 'i', 'f', 's', 't')
    values = {
        names.b: [f, t],
        names.i: [0, 1],
        names.f: [0.5, 1.5],
        names.s: [nil, 'a'],
        names.t: [d1, d2],
    }
    if nulls:
        values = {k: v[:1] + [None] + v[1:] for k, v in values.items()}
    return values


def tiny_pandas_df(
    nulls=False,
    nullable_types=False,
    sNullNull=False,
    euroStrDates=False,
    sBools=False,
    longNames=False,
):
    if nullable_types:
        df = pd.DataFrame(
            {
                k: pd.Series(v, dtype=pd_nullable_type(k))
                for k, v in tiny_python_values(nulls=nulls).items()
            }
        )
        if longNames:
            df.columns = LONG_NAMES
        return df
    else:
        return pd.DataFrame(
            tiny_python_values(
                nulls=nulls,
                sNullNull=sNullNull,
                euroStrDates=euroStrDates,
                sBools=sBools,
                longNames=longNames,
            )
        )


def tiny_polars_df(
    nulls=False,
    sNullNull=False,
    euroStrDates=False,
    sBools=False,
    longNames=False,
):
    return pl.DataFrame(
        tiny_python_values(
            nulls=nulls,
            sNullNull=sNullNull,
            euroStrDates=euroStrDates,
            sBools=sBools,
            longNames=longNames,
        )
    )


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
