import polars as pl

from tdda.serial.polarsio import csv_to_polars

from tdda.serial.examples.helpers import (
    generate_base_python_lists,
)


doc = """
pl.Config.set_tbl_cols(10)
pl.Config.set_fmt_str_lengths(10)
pl.Config.set_tbl_width_chars(70)
pl.Config.set_tbl_rows(2)
pl.Config.set_tbl_formatting('NOTHING')
pl.Config.set_tbl_column_data_type_inline(True)
pl.Config.set_tbl_dataframe_shape_below(True)
"""

def generate_reference_base_polars_dataframe():
    d = generate_base_python_lists()
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


def bool_values(s, f, t):
    return [
        None if v is None else True if v == t else False if v == f else None
        for v in list(s)
    ]


def fix_bool_cols(df):
    c2 = pl.Series('bool2', bool_values(df['bool2'], 'no', 'yes'), pl.Boolean)
    c3 = pl.Series('bool3', bool_values(df['bool3'], 0, 1), pl.Boolean)
    df.replace_column(4, c2)
    df.replace_column(5, c3)


