import sys
import pandas as pd
import polars as pl

from tdda.serial import (
    csv_to_pandas,
    pandas_to_csv,
    csv_to_polars,
    load_metadata,
    serial_to_polars_read_csv_args,
)

brk = f'\n{"-" * 72}\n\n'


df = pd.DataFrame({'n': [1, 2], 'f': [1.5, None], 's': ['à', 'é']})
print(f'Original Pandas Dataframe:\n{df}')

pandas_to_csv(df, 'simple3x2.csv', auto_md_outpath=True)
df2 = csv_to_pandas('simple3x2.csv', find_md=True)
print(f'{brk}Reconstructed Pandas Dataframe from .csv:\n{df2}')

pandas_to_csv(df, 'simple3x2-pdl.psv', auto_md_outpath=True,
              sep='|', na_rep='.', encoding='latin-1', )
df3 = csv_to_pandas('simple3x2-pdl.psv', find_md=True)
print(f'{brk}Reconstructed Pandas Dataframe from .psv:\n{df3}')

df4 = csv_to_polars('simple3x2-pdl.psv:')
print(f'{brk}Reconstructed Polars Dataframe from .psv:\n{df4}')

pl_kwargs = serial_to_polars_read_csv_args(
    load_metadata('simple3x2-pdl.serial')
)
print(f'{brk}Keyword args for polars.read_csv:\n{pl_kwargs}')
info = pandas_to_csv(df, 'simple3x2-inmd.psv',
                     md_outpath='simple3x2-pdl2.serial',
                     md_inpath='pdl.serial')
print(f'{brk}Write info:')
print(info)

pandas_to_csv(df, 'simple3x2-inmd.psv',
    md_outpath='simple3x2-pdl+pandas.serial', md_inpath='pdl.serial',
    flavour=['tdda.serial', 'pandas.read_csv', 'pandas.DataFrame.to_csv'])
df5 = csv_to_pandas('simple3x2.psv', 'simple3x2-pdl+pandas.serial')
print(f'{brk}Reconstructed Polars Dataframe from .psv with multi-flavour '
      f'tdda.serial metadata:\n{df5}')


df['s'] = pd.Series(df.s, dtype='string')
print(df.info())
pandas_to_csv(df, 'simple3x2-inmd.psv', md_inpath='pdl.serial',
    md_outpath='simple3x2-pdl+pandas-s.serial', flavour=['pandas.read_csv'])

df6 = csv_to_pandas('simple3x2.psv', 'simple3x2-pdl+pandas-s.serial')
print(f'{brk}Reconstructed Polars Dataframe from .psv with (only) pandas '
      f'tdda.serial metadata:\n{df6}')


