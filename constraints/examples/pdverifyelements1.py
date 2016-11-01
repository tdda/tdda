# pdverifyelements1.py

from __future__ import print_function
from tdda.constraints.pdconstraints import verify_df
from pmmif.featherpmm import read_dataframe

ds = read_dataframe('/miro/datasets/elements92.feather')
v = verify_df(ds.df, '/tmp/elements92.tdda')
print('Passes:', v.passes, 'Failures:', v.failures)
