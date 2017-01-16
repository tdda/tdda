# -*- coding: utf-8 -*-

"""
simple_verification.py

This file shows both a successful verification of a dataframe against
a constraints (.tdda) file, and an unsuccessful verification (i.e.
one in which some constraints are not satisfied.)


"""
from __future__ import division
from __future__ import print_function

import os
import sys
import pandas as pd

from tdda.constraints.pdconstraints import verify_df

THIS_DIR = os.path.split(os.path.abspath(__file__))[0]
TDDA_FILE = os.path.join(THIS_DIR, 'example_constraints.tdda')


def example_positive_verification():
    n_failures = 0
    df = pd.DataFrame({'a': [2, 4], 'b': ['one', pd.np.NaN]})
    v = verify_df(df, TDDA_FILE)

    if v.failures == 0:
        print('Correctly verified dataframe against constraints in %s.'
              % TDDA_FILE)
    else:
        print('*** Unexpectedly failed to verify dataframe against constraints'
              ' in %s.\nSomething is wrong!' % TDDA_FILE, file=sys.stderr)
        print(v)
        n_failures = 1
    return n_failures


def example_failing_verification():
    n_failures = 0
    df = pd.DataFrame({'a': [0, 1, 2, 10, pd.np.NaN],
                       'b': ['one', 'one', 'two', 'three', pd.np.NaN]})
    v = verify_df(df, TDDA_FILE)

    if v.failures > 0:
        print('Correctly failed to verify dataframe that does not satisify '
              'all the constraints in %s' % TDDA_FILE)
        if v.failures != 7 and v.passes != 5:
            print('However, expected 7 failures and 5 passes.\n'
                  'Actual: Failures: %d, Passes: %s.\n'
                  '*** Not great!' % (v.failures, v.passes))
            n_failures = 1
    elif v.failures == 0:
        print('*** Incorrectly verified dataframe that should have failed '
              'against constraints in\n %s.' % TDDA_FILE, file=sys.stderr)
        n_failures = 1

    print('\nRESULT AS A STRING:\n')
    print(str(v))
    print('\nRESULT AS A DATAFRAME:\n')
    print(v.to_frame())
    print('\n')
    return n_failures

if __name__ == '__main__':
    failures = example_positive_verification()
    failures += example_failing_verification()
    sys.exit(failures)
