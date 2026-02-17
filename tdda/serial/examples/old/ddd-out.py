import pandas as pd

def read_data(inpath):
    return pd.read_csv(
        dtype={
            'index': 'Int64',
            'evennulls': 'boolean',
            'oddnulls': 'boolean',
            'evens': 'Int64',
            'odds': 'Int64',
            'evenreals': 'float',
            'oddreals': 'float',
            'evenstr': 'string',
            'oddstr': 'string',
            'elevens': 'string',
            'binnedindex': 'Int64',
            'binnedodds': 'Int64'
        },
        date_format={
            'basedate': 'ISO8601',
            'evendates': 'ISO8601'
        },
        parse_dates=[
            'basedate',
            'evendates'
        ],
        dtype_backend='numpy_nullable'
    )

