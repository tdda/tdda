# accounts_verify_25k.py

import pandas as pd

from tdda.constraints.pd.constraints import verify_df

df = pd.read_csv('testdata/accounts25k.csv')
print(verify_df(df, 'accounts25k.tdda'))
