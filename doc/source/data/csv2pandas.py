from tdda.serial import csv_to_pandas

df1 = csv_to_pandas('docdata.txt', 'docdata.serial')
df2 = csv_to_pandas('docdata.txt:docdata.serial')
df3 = csv_to_pandas('docdata.txt:')
df4 = csv_to_pandas('docdata.txt', find_md=True)
