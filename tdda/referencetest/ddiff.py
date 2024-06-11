import sys

from tdda.referencetest.checkpandas import PandasComparison, same_structure_dataframe_diffs

from rich import print as rprint


def ddiff(leftpath, rightpath):
    c = PandasComparison()
    dfL = c.load_serialized_dataframe(leftpath)
    dfR = c.load_serialized_dataframe(rightpath)
    result = c.check_dataframe(dfL, dfR, create_temporaries=False, type_matching='medium')

    if result.failures > 0:
        print(result.diffs)
        diff = result.diffs.df.diff  # there if same structure
        if diff:
            table = diff.details_table(dfL, dfR)
            print()
            rprint(table)


def ddiff_helper(args):
    if len(args) != 2:
        print('USAGE: tdda diff LEFT.parquet RIGHT.parquet', file=sys.stderr)
        print('   or: tdda diff LEFT.csv RIGHT.csv', file=sys.stderr)
        sys.exit(1)
    else:
        ddiff(*args)

if __name__ == '__main__':
    if len(sys.argv) == 3:
        ddiff(sys.argv[1], sys.argv[2])

