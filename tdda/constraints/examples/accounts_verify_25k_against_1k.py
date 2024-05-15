# accounts_verify_10k_against_1k.py

import pandas as pd

from tdda.constraints.pd.constraints import verify_df

df = pd.read_csv('testdata/accounts25k.csv')
print(verify_df(df, 'testdata/accounts1k.tdda'))
