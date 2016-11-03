# elements_constraints_discovery.py

from __future__ import print_function
import pandas as pd

from tdda.constraints.pdconstraints import discover_constraints, verify_df

df = pd.read_csv('../testdata/elements92.csv')
constraints = discover_constraints(df)
with open('elements92.tdda', 'w') as f:
    f.write(constraints.to_json())
print('Written elements92.tdda')

print(verify_df(df, 'elements92.tdda'))



