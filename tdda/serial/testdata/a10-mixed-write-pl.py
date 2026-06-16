import polars as pl

def write_data(df, outpath):
    df.write_csv(
        outpath,
        separator='|',
        quote_char='"',
        null_value='NULL',
        date_format='%Y-%m-%d'
    )

