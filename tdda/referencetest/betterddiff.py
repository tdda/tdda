import numpy as np
import pandas as pd

from tdda.abstractdf import col_names
from tdda.serial import csv_to_pandas
from tdda.utils import find_free_name, debug

from tdda.referencetest.ddiff import TDDADiff


def join_diff(left, right, key=None):

    if not key:
        all_names = set(col_names(left)) | set(col_names(right))
        key = find_free_name(all_names, ['Row', 'ROW', 'row', 'Row#'])
        L = pd.DataFrame({key: pd.Series(np.arange(len(left)), dtype='Int64')})
        for k in left:
            L[k] = left[k]
        R = pd.DataFrame({key: pd.Series(np.arange(len(right)),
                                         dtype='Int64')})
        for k in right:
            R[k] = right[k]
        left, right = L, R
        print(left)

    left.columns = [name + '_L' for name in left]
    right.columns = [name + '_R' for name in right]

    keyL, keyR = key + '_L', key + '_R'
    dfj = left.merge(right, left_on=keyL, right_on=keyR, how='outer')

    L = dfj[left.columns]
    R = dfj[right.columns]
    L.columns = [c[:-2] for c in L]
    R.columns = [c[:-2] for c in R]

    d = TDDADiff(L, R, engine='pandas', key=key, verbosity=2)
    d.ddiff()

if __name__ == '__main__':
    left = csv_to_pandas('tests/testdata/four-squares.csv')
    right = csv_to_pandas('tests/testdata/five-squares.csv')
#    join_diff(left, right, 'n')
    join_diff(left, right)


