from tdda.serial.pandasio import csv_to_pandas

df = csv_to_pandas('machines.psv', 'machines.serial')
print(df, '\n')
df.info()
