# accounts_verify_25k_against_1k_feather.py

from __future__ import print_function
import pandas as pd

from tdda.constraints.pd.constraints import verify_df

df = pd.read_csv('testdata/accounts25k.csv')
verification = verify_df(df, 'testdata/accounts1k.tdda')

print('Basic Verification:')
print(verification)
print('\n')
print('Verification DataFrame:')
dfv = verification.to_frame()
print(dfv)

