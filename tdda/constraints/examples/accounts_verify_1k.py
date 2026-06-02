# accounts_verify_1k.py
import pandas as pd

from tdda.constraints.pd.constraints import verify_df

# parse_dates ensures date fields are read correctly.
# tdda.serial.csv_to_pandas handles this automatically:
#   from tdda.serial import csv_to_pandas
#   df = csv_to_pandas('accounts1k.csv')
df = pd.read_csv('accounts1k.csv', parse_dates=['open_date', 'close_date'])
print(verify_df(df, 'accounts1k.tdda'))
