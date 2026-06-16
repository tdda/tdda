import pandas as pd

def write_data(df, outpath):
    df.to_csv(
        outpath,
        sep='|',
        encoding='utf-8',
        quotechar='"',
        date_format='%Y-%m-%dT%H:%M:%S',
        na_rep='NULL',
        index=False
    )

