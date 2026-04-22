import polars as pl

def read_data(inpath):
    df = pl.read_csv(
        inpath,
        separator='|',
        quote_char='"',
        null_values=[''],
        encoding='UTF-8',
        schema={
            'id': pl.Int64,
            'name': pl.String,
            'joined': pl.Datetime,
            'last_seen': pl.String
        }
    )

    df = df.with_columns([
        pl.col('last_seen').str.to_datetime(format='%m/%d/%Y %H:%M:%S'),
    ])
    return df

