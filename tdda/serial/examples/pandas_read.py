import sys

from tdda.referencetest.checkpandas import diff_dataframes
from tdda.serial.examples.pdgen import (
    compare,
    read_with_tdda_serial,
    read_csv_explicit,
    generate_reference_base_pandas_dataframe
)


def main():
    verbose = '-v' in sys.argv or '--verbose' in sys.argv
    ref_df = generate_reference_base_pandas_dataframe()
    df1 = read_csv_explicit('base.csv', 'base-csv-pandas.serial')
    df2 = read_with_tdda_serial('base.csv', 'base-csv-pandas.serial')
    df3 = read_with_tdda_serial('base.psv', 'base-psv-pandas.serial')
    df4 = read_with_tdda_serial('base.tsv', 'base-tsv-pandas.serial')
    df5 = read_with_tdda_serial('base.csv', 'base-csv.serial')
    df6 = read_with_tdda_serial('base-dot-null.csv', 'base-dot-csv.serial')

    for n, df in enumerate((df1, df2, df3, df4, df5, df6), 1):
        compare(df, ref_df, n, verbose=verbose)

    assert diff_dataframes(df1, df2, type_matching='strict',
                           precision=6).diffs == []
    assert diff_dataframes(df1, df3, type_matching='strict',
                           precision=6).diffs == []
    assert diff_dataframes(df2, df3, type_matching='strict',
                           precision=6).diffs == []


if __name__ == '__main__':
    main()

