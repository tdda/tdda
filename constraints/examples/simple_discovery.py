# -*- coding: utf-8 -*-

"""
simple_discovery.py

This file writes constraints as JSON to /tmp/example_constraints.tdda
by default.

For reference, the file it writes should be semantically equivalent
to expected_example_constraints.tdda in this directory
(tdda/constraints/examples).
"""
from __future__ import division
from __future__ import print_function

import os
import sys
import pandas as pd

from tdda.constraints.pdconstraints import discover_constraints

OUTDIR = '/tmp'
OUTPATH = os.path.join(OUTDIR, 'example_constraints.tdda')

def example_constraint_generation(path=OUTPATH):

    df = pd.DataFrame({'a': [1, 2, 9], 'b': ['one', 'two', pd.np.NaN]})
    constraints = discover_constraints(df)

    if os.path.exists(path):
        os.unlink(path)

    with open(path, 'w') as f:
        f.write(constraints.to_json())

    if os.path.exists(path):
        print('Written %s successfully.' % path)
        sys.exit(0)
    else:
        print('Failed to write %s.' % path, file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    example_constraint_generation()

