import polars as pl

def read_data(inpath):
    return pl.read_csv(
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

