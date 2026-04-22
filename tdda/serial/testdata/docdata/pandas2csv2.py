from tdda.serial import pandas_to_csv, csv_to_pandas

df = csv_to_pandas('docdata.txt:')
pandas_to_csv(df, 'docdata2pd.csv', md_outpath='docdata2pd.serial',
              sep='|', na_rep='NULL', quotechar="'")
