# elements_detect_118_against_92.py

from __future__ import print_function
import pandas as pd

from tdda.constraints.pd.constraints import detect_df

df = pd.read_csv('testdata/elements118.csv')
print(detect_df(df, 'elements92.tdda', outpath='elements118_detect.csv',
                per_constraint=True, output_fields=[]))

