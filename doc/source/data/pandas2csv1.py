from tdda.serial import pandas_to_csv, csv_to_pandas

df = csv_to_pandas('docdata.txt:')
pandas_to_csv(df, 'docdata1pd.csv', md_outpath='docdata1pd.serial')
