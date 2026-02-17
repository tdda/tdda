import pandas as pd

def read_data(inpath):
    return pd.read_csv(
        inpath,
        sep=',',
        encoding='UTF-8',
        escapechar='\\',
        quotechar='"',
        dtype={
            'n': 'Int64',
            'f': 'Float64',
            's': 'string'
        },
        na_values='',
        keep_default_na=False
    )

