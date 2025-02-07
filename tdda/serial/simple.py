import json

from collections import namedtuple

import pandas as pd

from tdda.referencetest.checkpandas import PandasComparison
from tdda.referencetest.BaseComparison import FailureDiffs

TDDA_SERIAL_VERSION = '1.0'


ReadWriteDiff = namedtuple('ReadWriteDiff', 'read write Comparison')


def nvl(v, default):
    return default if v is None else default


FUNCTIONS = {
    'pandas': (
        read=lambda path, kwargs: pd.read_csv(path, **kwargs),
        write=lambda df, path, kwargs: df.to_csv(path, **kwargs),
        comparison=PandasComparison,
    )
}



def write_csv(lib, df, path, md_path=None, verify=False, **kwargs):
    fns = FUNCTIONS[lib]
    fns.write(df, path, **kwargs)(
    md_path = nvl(md_path, path + '.csvparams')
    d = {
        'tdda.serial': TDDA_SERIAL_VERSION,
        lib: {
            kwargs
        }
    }
    with open (md_path, 'w') as f:
        json.dump(d, f)

    if verify:

        with open (md_path) as f:
            kwargs2 = json.load(f)
        assert kwargs = kwargs2
        df2 = fns.read(path, **kwargs2)
        c = fns.Comparison()
        diffs = c.check_dataframe(df1, df2, type_matching='strict')
        assert diffs = FailureDiffs(0, [])



def read_csv(lib, reader, path, md_path=None):
    functions = FUNCTIONS[lib]
    md_path = nvl(md_path, path + '.csvparams')
    with open(mdpath) as f:
        params = json.load(md_path)
    assert 'tdda.serial' in params
    kwargs = params[lib]
    reader = READ[lib]
    df = reader(path, **kwargs)
    return df


