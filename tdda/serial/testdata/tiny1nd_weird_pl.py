import polars as pl

def read_data(inpath):
    df = pl.read_csv(
        inpath,
        separator=';',
        quote_char="'",
        null_values=['.'],
        encoding='latin-1',
        schema={
            'IAmBoolean': pl.Boolean,
            'IAmInt': pl.Int64,
            'f': pl.Float64,
            'IAmString': pl.String,
            'IAmDate': pl.String
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
        pl.col('IAmDate').str.to_datetime(format='%d/%m/%Y'),
    ])
    return df

