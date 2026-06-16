import polars as pl

def write_data(df, outpath):
    df.write_csv(
        outpath,
        separator=';',
        quote_char="'",
        null_value='.',
        datetime_format='%d/%m/%Y'
    )

