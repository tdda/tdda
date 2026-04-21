from tdda.serial import csv_to_pandas

df = csv_to_pandas('docdata.txt:')
print(df)
print('dtypes:', ' '.join(str(df[c].dtype) for c in df))


