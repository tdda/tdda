# elements_verify_118_against_92_parquet.py

from __future__ import print_function

from tdda.constraints.pd.constraints import verify_df, load_df

df = load_df('testdata/elements118.parquet')
verification = verify_df(df, 'testdata/elements92.tdda')

print('Basic Verification:')
print(verification)
print('\n')
print('Verification DataFrame:')
dfv = verification.to_frame()
print(dfv)

