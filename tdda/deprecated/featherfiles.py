import os
import sys
try:
    from pmmif import featherpmm
except ImportError:
    featherpmm = None

try:
    import feather as feather
except ImportError:
    feather = None

DEPRECATION_WARNING = '''*** DEPRECATION WARNING:
Feather files will be removed in version 2.2, in favour of .parquet files
(already supported).

Please consider installing pyarrow (pip install pyarrow) and using
parquet files instead of feather files.
'''

def deprecation_warning():
    if not os.environ.get('TDDA_TESTING', None):
        print(DEPRECATION_WARNING, file=sys.stderr)

def read_feather_file(path):
    deprecation_warning()
    if featherpmm and feather:
        ds = featherpmm.read_dataframe(path)
        return ds.df
    elif feather:
        return feather.read_dataframe(path)
    else:
        raise Exception('The Python feather module is not installed.\n'
                        'Use:\n    pip install feather-format\n'
                        'to add capability.\n')


def write_feather_file(df, path, name):
    deprecation_warning()
    if featherpmm and feather:
        featherpmm.write_dataframe(featherpmm.Dataset(df, name=name), path)
    elif feather:
        feather.write_dataframe(df, path)
    else:
        raise Exception('The Python feather module is not installed.\n'
                        'Use:\n    pip install feather-format\n'
                        'to add capability.\n')

