from tdda.serial import polars_to_csv, csv_to_polars

df = csv_to_polars('docdata.txt:')
polars_to_csv(df, 'docdata3pl.csv', md_inpath='docdata.serial')
