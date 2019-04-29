# accounts_detect_25k_against_1k.py

from __future__ import print_function
import pandas as pd

from tdda.constraints.pd.constraints import detect_df

df = pd.read_csv('testdata/accounts25k.csv')
print(detect_df(df, 'accounts1k.tdda', outpath='accounts25k_detect.csv',
                per_constraint=True, output_fields=[]))

