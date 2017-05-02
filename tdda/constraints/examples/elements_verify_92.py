# elements_verify_92.py

from __future__ import print_function
import pandas as pd

from tdda.constraints.pdconstraints import verify_df

df = pd.read_csv('testdata/elements92.csv')
print(verify_df(df, 'elements92.tdda'))
