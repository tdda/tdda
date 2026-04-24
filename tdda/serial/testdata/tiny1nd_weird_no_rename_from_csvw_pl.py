import polars as pl

def read_data(inpath):
    df = pl.read_csv(
        inpath,
        separator=';',
        quote_char="'",
        null_values=['.'],
        encoding='latin-1',
        schema={
            'b': pl.String,
            'i': pl.Int64,
            'f': pl.Float64,
            's': pl.String,
            't': pl.String
        }
    )

    df = df.with_columns([
        pl.col('b').replace_strict({'Yes': 1, 'n': 0}).cast(pl.Boolean),
        pl.col('t').str.to_date(format='%d/%m/%Y'),
    ])
    return df

