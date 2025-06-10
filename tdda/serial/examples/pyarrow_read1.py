from pyarrow import csv

table = csv.read_csv('base.csv')
print(table)

df = table.to_pandas()
print(df)
print(df.info())
