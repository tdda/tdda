import json
import os

from collections import namedtuple

import pandas as pd

from tdda.referencetest.checkpandas import PandasComparison
from tdda.referencetest.basecomparison import FailureDiffs
from tdda.referencetest.checkpandas import loosen_type

TDDA_SERIAL_VERSION = '1.0'


ReadWriteDiff = namedtuple('ReadWriteDiff', 'read write Comparison')


def nvl(v, default):
    return default if v is None else default


def swap_ext(path, ext):
    stem, oldext = os.path.splitext(path)
    dot = '' if ext.startswith('.') else '.'
    return f'{stem}{dot}{ext}'


def metadata_path(path, md_path=None):
    return nvl(md_path, swap_ext(path, '.tddacsvmd'))


FUNCTIONS = {
    'pandas': (
        ReadWriteDiff(read=lambda path, **kwargs:
                                  pd.read_csv(path, **kwargs),
                      write=lambda df, path, **kwargs:
                                   df.to_csv(path, **kwargs),
                      Comparison=PandasComparison)
    ),
}



def write_csv(lib, df, path, md_path=None, verify=False, **kwargs):
    fns = FUNCTIONS[lib]

    kw = kwargs.copy()  # so as not to alter one passed in

    defaults = {
        'index': False,
        'quotechar': '"',
        'quoting': 0,
        'escapechar': '\\',
    }

    if 'sep' not in kw and 'delimiter' not in kw:
        kw['sep'] = ','

    for k, v in defaults.items():
        if k not in kw:
            kw[k] = v

    fns.write(df, path, **kw)

    # Now transform to read params

    del kw['index']    # don't want in the read args

    # parse these dates
    dates = [col for col in df if 'date' in loosen_type(df[col].dtype.name)]

    # Don't specify these types (typically strings, bools, and dates)
    objects = [col for col in df if df[col].dtype.name == 'object']

    # Find any object columns with dates:
    for col in objects:
        nonnulls = df[col].dropna()
        if nonnulls.size > 0:
            m = nonnulls.iloc(0)[0]
            if 'date' in str(type(m)):  # add those to list of dates
                dates.append(col)

    # Specify types for non-object columns

    kw['dtype'] = {
        col: df[col].dtype.name for col in df
        if col not in objects and col not in dates
    }

    # Stop it picking up non-blank alternative null representations as N/As
    kw['keep_default_na'] = False

    # Read blank as null
    kw['na_values'] = ''

    # Specify ISO8601 dates
    if dates:
        kw['parse_dates'] = dates
        kw['date_format'] = 'ISO8601'
    md_path = metadata_path(path, md_path)
    d = {
        'tdda.serial': TDDA_SERIAL_VERSION,
        lib: kw,
    }
    with open (md_path, 'w') as f:
        json.dump(d, f, indent=4)

    if verify:

        with open (md_path) as f:
            kw2 = json.load(f)
        assert kw == kw2
        df2 = fns.read(path, **kw2)
        c = fns.Comparison()
        diffs = c.check_dataframe(df1, df2, type_matching='strict')
        assert diffs == FailureDiffs(0, [])

def pandas_write_csv(df, path, md_path=None, verify=False, **kwargs):
    return write_csv('pandas', df, path=path,
                     md_path=md_path, verify=verify, **kwargs)



def read_csv(lib, path, md_path=None, **kwargs):
    functions = FUNCTIONS[lib]
    md_path = metadata_path(path, md_path)
    with open(md_path) as f:
        params = json.load(f)
    assert 'tdda.serial' in params
    kwargs = params[lib]
    fns = FUNCTIONS[lib]
    df = fns.read(path, **kwargs)
    return df


def pandas_read_csv(path, md_path=None, **kwargs):
    return read_csv('pandas', path=path, md_path=md_path, **kwargs)



