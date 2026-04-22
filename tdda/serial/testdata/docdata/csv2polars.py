from tdda.serial import csv_to_polars

df1 = csv_to_polars('docdata.txt', 'docdata.serial')
df2 = csv_to_polars('docdata.txt:docdata.serial')
df3 = csv_to_polars('docdata.txt:')
df4 = csv_to_polars('docdata.txt', find_md=True)
