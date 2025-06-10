import polars as pl
from example_helpers import generate_python_lists


doc = """
pl.Config.set_tbl_cols(10)
pl.Config.set_fmt_str_lengths(10)
pl.Config.set_tbl_width_chars(70)
pl.Config.set_tbl_rows(2)
pl.Config.set_tbl_formatting('NOTHING')
pl.Config.set_tbl_column_data_type_inline(True)
pl.Config.set_tbl_dataframe_shape_below(True)
"""

def generate_reference_polars_dataframe():
    d = generate_python_lists()
    df = pl.DataFrame((
        pl.Series('row', d.row, dtype=pl.Int64),
        pl.Series('int', d.ints, dtype=pl.Int64),
        pl.Series('float', d.floats, dtype=pl.Float64),
        pl.Series('bool1', d.bools, dtype=pl.Boolean),
        pl.Series('bool2', d.bools, dtype=pl.Boolean),
        pl.Series('bool3', d.bools, dtype=pl.Boolean),
        pl.Series('stri', d.stri, dtype=pl.String),
        pl.Series('strf', d.strf, dtype=pl.String),
        pl.Series('string', d.names, dtype=pl.String),
        pl.Series('string_accents', d.accents, dtype=pl.String),
        pl.Series('string_torture', d.torture, dtype=pl.String),
        pl.Series('date', d.dates, dtype=pl.Date),
        pl.Series('datetime', d.dts, dtype=pl.Datetime),
        pl.Series('datetimezone', d.dtzs, dtype=pl.Datetime),
        pl.Series('nil_bool', d.nulls, dtype=pl.Boolean),
        pl.Series('nil_str', d.nulls, dtype=pl.String),
        pl.Series('row2', d.row, dtype=pl.Int64),
    ))
    return df


df = pl.read_csv('base.csv',
                 separator=',',
                 schema_overrides={
                    'stri': pl.String,
                    'strf': pl.String,
                    'nil_str': pl.String,
                    'nil_bool': pl.Boolean,
                    'date': pl.Date,
                    'datetime': pl.Datetime,
                    'datetimezone': pl.Datetime,
            })
ref_df = generate_reference_polars_dataframe()

df = df.drop('bool2', 'bool3')
ref_df = ref_df.drop('bool2', 'bool3')
df.write_parquet('/tmp/pl_csv_actual.parquet')
ref_df.write_parquet('/tmp/pl_ref.parquet')

with pl.Config() as cfg:
    cfg.set_tbl_cols(-1)
    cfg.set_tbl_rows(-1)
    print(df)


print('Use:\ntdda diff /tmp/pl_csv_actual.parquet /tmp/pl_ref.parquet')
