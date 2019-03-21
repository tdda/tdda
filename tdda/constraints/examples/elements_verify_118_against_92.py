# elements_verify_118_against_92.py

from __future__ import print_function
import pandas as pd

from tdda.constraints.pd.constraints import verify_df

df = pd.read_csv('testdata/elements118.csv')
print(verify_df(df, 'elements92.tdda'))
