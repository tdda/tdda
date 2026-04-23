import pandas as pd

def read_data(inpath):
    return pd.read_csv(
        inpath,
        sep=';',
        encoding='latin-1',
        escapechar='`',
        quotechar="'",
        dtype={
            'IAmBoolean': 'bool[pyarrow]',
            'IAmInt': 'int64[pyarrow]',
            'f': 'double[pyarrow]',
            'IAmString': 'string[pyarrow]'
        },
        date_format={
            'IAmDate': '%d/%m/%Y'
        },
        parse_dates=['IAmDate'],
        na_values='.',
        keep_default_na=False,
        names=[
            'IAmBoolean',
            'IAmInt',
            'f',
            'IAmString',
            'IAmDate'
        ],
        header=0,
        true_values=[
            'Yes',
            'y'
        ],
        false_values=[
            'No',
            'n'
        ]
    )

