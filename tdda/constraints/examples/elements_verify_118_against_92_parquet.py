# elements_verify_118_against_92_parquet.py

import pandas as pd

from tdda.constraints.pd.constraints import verify_df

df = pd.read_parquet('testdata/elements118.parquet')
verification = verify_df(df, 'testdata/elements92.tdda')

print('Basic Verification:')
print(verification)
print('\n')
print('Verification DataFrame:')
dfv = verification.to_frame()
print(dfv)

