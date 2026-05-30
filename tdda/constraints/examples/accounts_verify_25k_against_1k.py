# accounts_verify_25k_against_1k.py

import pandas as pd

from tdda.constraints.pd.constraints import verify_df

# parse_dates ensures date fields are read correctly.
# tdda.serial.csv_to_pandas handles this automatically:
#   from tdda.serial import csv_to_pandas
#   df = csv_to_pandas('accounts25k.csv')
df = pd.read_csv('accounts25k.csv', parse_dates=['open_date', 'close_date'])
print(verify_df(df, 'testdata/accounts1k.tdda'))
