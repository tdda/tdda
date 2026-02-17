from tdda.serial.pandasio import tddaserial_to_pandas_read_csv_args, csv_to_pandas
from tdda.serial.reader import load_metadata

import pandas as pd
from rich import print as rprint



md = load_metadata('machines.serial')
kw = tddaserial_to_pandas_read_csv_args(md)
rprint(kw)

df = pd.read_csv('machines.csv', **kw)
print(df)
print(df.info())

