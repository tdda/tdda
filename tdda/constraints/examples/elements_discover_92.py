# elements_discover_92.py

import pandas as pd

from tdda.constraints.pd.constraints import discover_df

df = pd.read_csv('testdata/elements92.csv')
constraints = discover_df(df)
with open('elements92.tdda', 'w', encoding='utf-8') as f:
    f.write(constraints.to_json())
print('Written elements92.tdda')


