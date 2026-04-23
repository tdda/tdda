import pandas as pd

def read_data(inpath):
    return pd.read_csv(
        inpath,
        sep=';',
        encoding='latin-1',
        quotechar="'",
        doublequote=False,
        dtype={
            'b': 'boolean',
            'i': 'Int64',
            'f': 'Float64',
            's': 'string'
        },
        date_format={
            't': '%d/%m/%Y'
        },
        parse_dates=['t'],
        na_values='.',
        keep_default_na=False,
        true_values=[
            'Yes',
            'y'
        ],
        false_values=[
            'No',
            'n'
        ]
    )

