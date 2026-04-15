import sys
from tdda.serial import csv_to_pandas


USAGE = """USAGE:
    python cat.py FLATFILE
or: python cat.py FLATFILE:
or: or: python cat.py FLATFILE:METADATA
"""


def main(path):
    df = csv_to_pandas(path)
    print(df.head(30))


if __name__ == '__main__':
    if len(sys.argv) == 2:
        main(sys.argv[1])
    else:
        print(USAGE)
