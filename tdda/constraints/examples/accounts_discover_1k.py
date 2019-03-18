# accounts_discover_1k.py

from __future__ import print_function
import pandas as pd

from tdda.constraints.pd.constraints import discover_df

df = pd.read_csv('testdata/accounts1k.csv')
constraints = discover_df(df)
with open('accounts1k.tdda', 'w') as f:
    f.write(constraints.to_json())
print('Written accounts1k.tdda')


