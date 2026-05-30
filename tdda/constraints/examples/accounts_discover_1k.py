# accounts_discover_1k.py

import pandas as pd

from tdda.constraints.pd.constraints import discover_df

# parse_dates ensures date fields are typed as 'date' in the constraints.
# tdda.serial.csv_to_pandas handles this automatically:
#   from tdda.serial import csv_to_pandas
#   df = csv_to_pandas('accounts1k.csv')
df = pd.read_csv('accounts1k.csv', parse_dates=['open_date', 'close_date'])
constraints = discover_df(df, inc_rex=True)
with open('accounts1k.tdda', 'w', encoding='utf-8') as f:
    f.write(constraints.to_json())
print('Written accounts1k.tdda')


