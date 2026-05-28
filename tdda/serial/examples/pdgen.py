import datetime
import json
import sys

import pandas as pd

from tdda.serial.pandasio import yn2bool,csv_to_pandas

from tdda.referencetest.checkpandas import diff_dataframes

from tdda.serial.examples.helpers import generate_base_python_lists


def read_csv_explicit(datapath, md_path):
    with open(md_path, encoding='utf-8') as f:
        d = json.load(f)
    params = d['pandas.read_csv']
    df = pd.read_csv(datapath, **params)
    return df


def read_with_tdda_serial(datapath, md_path, **kw):
    df = csv_to_pandas(datapath, md_path, upgrade_types=False, **kw)
    return df


def generate_reference_base_pandas_dataframe():
    d = generate_base_python_lists()
    df = pd.DataFrame({
        'row': pd.Series(d.row, dtype='int64'),
        'int': pd.Series(d.ints, dtype='Int64'),
        'float': pd.Series(d.floats, dtype='float64'),
        'bool1': pd.Series(d.bools, dtype='boolean'),
        'bool2': pd.Series(d.bools, dtype='boolean'),
        'bool3': pd.Series(d.bools, dtype='boolean'),
        'stri': pd.Series(d.stri, dtype='string'),
        'strf': pd.Series(d.strf, dtype='string'),
        'string': pd.Series(d.names, dtype='string'),
        'string_accents': pd.Series(d.accents, dtype='string'),
        'string_torture': pd.Series(d.torture, dtype='string'),
        'date': pd.Series(d.dates, dtype='datetime64[ns]'),
        'datetime': pd.Series(d.dts, dtype='datetime64[ns]'),
        'datetimezone': pd.Series(d.dtzs, dtype='object'),
        'nil_bool': pd.Series(d.nulls, dtype='boolean'),
        'nil_str': pd.Series(d.nulls, dtype='string'),
        'row2': pd.Series(d.row, dtype='int64'),
    })
    return df


def compare(actual_df, ref_df, n, verbose=True):
    if verbose:
        print(actual_df)
        print(actual_df.info())

    result = diff_dataframes(actual_df, ref_df, type_matching='strict',
                             precision=6)

    print(f'df{n} vs reference dataframe')
    if str(result.diffs):
        print(f'Differences:')
        print(result.diffs)
    else:
        print('Dataframes Identical')


