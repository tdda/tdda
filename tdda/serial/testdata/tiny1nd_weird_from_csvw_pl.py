import polars as pl

def read_data(inpath):
    df = pl.read_csv(
        inpath,
        separator=';',
        quote_char="'",
        null_values=['.'],
        encoding='latin-1',
        schema={
            'IAmBoolean': pl.String,
            'IAmInt': pl.Int64,
            'f': pl.Float64,
            'IAmString': pl.String,
            'IAmDate': pl.String
        }
    )

    df = df.with_columns([
        pl.col('IAmBoolean').replace_strict({'Yes': 1, 'n': 0}).cast(pl.Boolean),
        pl.col('IAmDate').str.to_date(format='%d/%m/%Y'),
    ])
    return df

