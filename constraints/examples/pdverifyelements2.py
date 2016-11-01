# pdverifyelements2.py

from __future__ import print_function
from tdda.constraints.pdconstraints import verify_df
from pmmif.featherpmm import read_dataframe

ds = read_dataframe('/miro/datasets/elements.feather')
v = verify_df(ds.df, '/tmp/elements92.tdda', report='fields')
print(str(v))

dfv = v.to_frame()
print(dfv[dfv.failures > 0])
