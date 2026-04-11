import numpy as np
import pandas as pd

from tdda.abstractdf import col_names
from tdda.serial import csv_to_pandas
from tdda.utils import find_free_name, debug, is_sequence

from tdda.referencetest.ddiff import TDDADiff, find_usable_key


def join_diff(left, right, key=None):
    left, right, key = find_usable_key(left, right, key)
    d = TDDADiff(left, right, engine='pandas', key=key, verbosity=2)
    d.ddiff()


if __name__ == '__main__':
    left = csv_to_pandas('tests/testdata/four-squares.csv')
    right = csv_to_pandas('tests/testdata/five-squares.csv')
    join_diff(left, right, 'n')
    join_diff(left, right)

    left = csv_to_pandas('../constraints/testdata/elements92.csv')
    right = csv_to_pandas('../constraints/testdata/elements118.csv')
    join_diff(left, right, 'Z')
    join_diff(left, right)
