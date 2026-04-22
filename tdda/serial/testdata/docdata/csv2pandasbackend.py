from tdda.serial import csv_to_pandas
dfb = csv_to_pandas('docdata.txt', 'docdata.serial', backend='original')
print(dfb)
