from tdda.serial import polars_to_csv, csv_to_polars

df = csv_to_polars('docdata.txt:')
polars_to_csv(df, 'docdata4pl.csv', md_inpath='docdata.serial',
              md_outpath='docdata4pl.serial')

