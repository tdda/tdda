import pandas as pd

def write_data(df, outpath):
    df.to_csv(
        outpath,
        sep=';',
        encoding='latin-1',
        escapechar='`',
        quotechar="'",
        date_format='%d/%m/%Y',
        na_rep='.',
        index=False
    )

