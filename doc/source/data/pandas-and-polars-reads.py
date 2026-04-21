from tdda.serial import csv_to_polars, csv_to_pandas

df1 = csv_to_pandas('docdata.serial')
df2 = csv_to_polars('docdata-metadata.json')
df3 = csv_to_polars('docdata.resource.yaml')
