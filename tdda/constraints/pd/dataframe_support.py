try:
    import pyarrow
    from pyarrow import parquet
except ImportError:
    parquet = None


try:
    from pmmif import featherpmm
except ImportError:
    featherpmm = None

try:
    import feather as feather
except ImportError:
    feather = None


try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO


def check_parquet():
    if not parquet:
        raise Exception('The Python feather module is not installed.\n'
                        'Use:\n    pip install feather-format\n'
                        'to add capability.\n')


def write_parquet_file(df, path):
    check_parquet()
    table = pyarrow.Table.from_pandas(df, preserve_index=False)
    parquet.write_table(table, path)


def read_parquet_file(path):
    check_parquet()
    table = parquet.read_table(path)
    return table.to_pandas()

