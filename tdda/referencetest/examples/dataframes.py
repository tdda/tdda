# -*- coding: utf-8 -*-
"""
dataframes.py: Trivial result generation functions for illustrating
               tdda.referencetest with Pandas Dataframes.

Source repository: http://github.com/tdda/tdda

License: MIT

Copyright (c) Stochastic Solutions Limited 2016-2018
"""
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import numpy as np
import pandas as pd


def generate_dataframe(nrows=10, precision=3):
    """
    Generate a simple Pandas DataFrame with examples of integer, real and
    string columns.
    """
    df = pd.DataFrame({'i': range(nrows)})
    df['r'] = df.i * (10/9)
    df['random'] = np.random.randint(0, nrows-1, nrows)
    df['b'] = df.i >= nrows/2
    df['i_square'] = df.i * df.i
    df['r_square'] = df.r * df.r
    df['s'] = 'result ' + df.r_square.round(precision).astype(str)
    return df

