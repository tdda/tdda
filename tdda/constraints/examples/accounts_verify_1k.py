# accounts_verify_1k.py
import pandas as pd

from tdda.constraints.pd.constraints import verify_df

df = pd.read_csv('testdata/accounts1k.csv')
print(verify_df(df, 'accounts1k.tdda'))
