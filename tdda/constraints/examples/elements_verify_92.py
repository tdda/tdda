# elements_verify_92.py

import pandas as pd

from tdda.constraints.pd.constraints import verify_df

df = pd.read_csv('testdata/elements92.csv')
print(verify_df(df, 'elements92.tdda'))
