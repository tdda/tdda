import polars as pl

def read_data(inpath):
    return pl.read_csv(
        separator=',',
        encoding='utf-8',
        schema={
            'index': pl.Int64,
            'evennulls': pl.Boolean,
            'oddnulls': pl.Boolean,
            'evens': pl.Int64,
            'odds': pl.Int64,
            'evenreals': pl.Float64,
            'oddreals': pl.Float64,
            'evenstr': pl.String,
            'oddstr': pl.String,
            'elevens': pl.String,
            'binnedindex': pl.Int64,
            'binnedodds': pl.Int64,
            'basedate': pl.Datetime,
            'evendates': pl.Datetime
        }
    )

