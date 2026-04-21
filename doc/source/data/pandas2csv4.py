from tdda.serial import pandas_to_csv, csv_to_pandas

df = csv_to_pandas('docdata.txt:')
pandas_to_csv(df, 'docdata4pd.csv', md_inpath='docdata.serial',
              md_outpath='docdata4pd.serial')

