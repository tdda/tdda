import csv
import pandas as pd
from tdda.serial.examples.torture import DATA, FIELD_INFO

from tdda.serial import csv_to_pandas, pandas_to_csv
from tdda.serial.pandasio import serial_type_to_pandas_dtype


def make_dataframe(backend=None):
    if backend is None:  # OG
        df = pd.DataFrame(DATA)
    else:
        types = {
            k: serial_type_to_pandas_dtype(FIELD_INFO[k].type, backend)
            for k, v in FIELD_INFO.items()
        }
        df = pd.DataFrame({
            k: pd.Series(
                v, dtype=types[k] if not types[k].startswith('date') else None
            )
            for k, v in DATA.items()
        })
    return df


def og():
    odf = make_dataframe()
    ndf = make_dataframe('numpy_nullable')
    adf = make_dataframe('pyarrow')

    pandas_to_csv(odf, 'og_df.csv', md_outpath='og_default_metadata.serial',
                  flavours='tdda.serial')
    odf.to_csv('og_raw.csv')

    pandas_to_csv(odf, 'og_df.csv', md_outpath='og_default_metadata.serial',
                  flavours='tdda.serial')
    odf.to_csv('og_raw.csv')


def simple():
    df = pd.DataFrame({'n': [1, 2], 'f': [1.5, None], 's': ['à', 'é']})
    pandas_to_csv(df, 'simple3x2.csv', md_outpath='simple3x2.serial',
                  flavours='tdda.serial')

    pandas_to_csv(df, 'simple3x2.psv',
                  md_outpath='simple3x2-pipe-dot-latin1.serial',
                  flavours='tdda.serial', sep='|', na_rep='.',
                  encoding='latin-1', )

    pandas_to_csv(df, 'simple3x2-inmd.psv',
                  md_outpath='simple3x2-pipe-dot-latin1-from-inmd.serial',
                  md_inpath='psv-dot-latin1.serial',
                  flavours='tdda.serial')



if __name__ == '__main__':
    #og()
    simple()

