from tdda.serial import csv_to_polars

df = csv_to_polars('docdata.txt:')
print(df)

