import sys

from tdda.referencetest.checkpandas import (
    PandasComparison,
    same_structure_dataframe_diffs
)

from rich import print as rprint

USAGE = '''
USAGE: tdda diff LEFT.parquet RIGHT.parquet [MAX_DIFFS]
   or: tdda diff LEFT.csv RIGHT.csv [MAX_DIFFS]
'''


def ddiff(leftpath, rightpath, max_diffs=None):
    c = PandasComparison()
    dfL = c.load_serialized_dataframe(leftpath)
    dfR = c.load_serialized_dataframe(rightpath)
    result = c.check_dataframe(dfL, dfR, create_temporaries=False,
                               type_matching='medium')
    print(dfL)
    print(dfR)
    if result.failures > 0:
        print(result.diffs)
        diff = result.diffs.df.diff  # there if same structure
        if diff:
            table = diff.details_table(dfL, dfR, max_diffs)
            print()
            rprint(table)


def ddiff_helper(args):
    if len(args) not in (2, 3):
        print(USAGE, file=sys.stderr)
        sys.exit(1)
    else:
        if len(args) == 3:
            try:
                n = int(args[2])
            except ValueError:
                print(USAGE, file=sys.stderr)
                sys.exit(1)
        else:
            n = None
        ddiff(*(args[:2]), n)

if __name__ == '__main__':
    if len(sys.argv) == 3:
        ddiff(sys.argv[1], sys.argv[2])

