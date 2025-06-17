import polars as pl

from tdda.serial.polarsio import csv_to_polars
from tdda.serial.examples.plgen import (
    fix_bool_cols,
    generate_reference_base_polars_dataframe,
)

if __name__ == '__main__':

    dfc = csv_to_polars('base.csv', 'base-csv-polars.serial')
    dfp = csv_to_polars('base.psv', 'base-psv-polars.serial')
    dft = csv_to_polars('base.tsv', 'base-tsv-polars.serial')

    raw_df = pl.read_csv('base.csv')
    ref_df = generate_reference_base_polars_dataframe()

    for d in (dfc, dfp, dft):
        fix_bool_cols(d)


    ref_df.write_parquet('/tmp/pl_ref.parquet')
    dfc.write_parquet('/tmp/pl_csv_actualc.parquet')
    dfp.write_parquet('/tmp/pl_csv_actualp.parquet')
    dft.write_parquet('/tmp/pl_csv_actualt.parquet')
    raw_df.write_parquet('/tmp/pl_raw.parquet')


    with pl.Config() as cfg:
        cfg.set_tbl_cols(-1)
        cfg.set_tbl_rows(-1)
        print(dfc)


    print('Use:\ntdda diff /tmp/pl_csv_actualc.parquet /tmp/pl_ref.parquet')
    print('Use:\ntdda diff /tmp/pl_csv_actualc.parquet /tmp/pl_csv_actualp.parquet')
    print('Use:\ntdda diff /tmp/pl_csv_actualc.parquet /tmp/pl_raw.parquet')
