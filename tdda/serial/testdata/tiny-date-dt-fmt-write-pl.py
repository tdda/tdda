import polars as pl

def write_data(df, outpath):
    df = df.with_columns(
        pl.col('d').cast(pl.Datetime),
    )
    df.write_csv(
        outpath,
        separator=',',
        null_value='',
        datetime_format='%d/%m/%Y %H:%M:%S'
    )

