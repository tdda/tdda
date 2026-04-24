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
        },
        new_columns=[
            'IAmBoolean',
            'IAmInt',
            'f',
            'IAmString',
            'IAmDate'
        ]
    )

    df = df.with_columns([
        pl.col('IAmBoolean').replace_strict({'Yes': 1, 'y': 1, 'No': 0, 'n': 0}).cast(pl.Boolean),
        pl.col('IAmDate').str.to_datetime(format='%d/%m/%Y'),
    ])
    return df

