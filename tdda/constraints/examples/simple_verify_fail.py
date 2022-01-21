import numpy as np
import pandas as pd
from tdda.constraints.pd.constraints import verify_df

df = pd.DataFrame({'a': [0, 1, 2, 10, np.NaN],
                   'b': ['one', 'one', 'two', 'three', np.NaN]})
v = verify_df(df, 'example_constraints.tdda')

print('Passes: %d' % v.passes)
print('Failures: %d\n\n\n' % v.failures)
print(str(v))
print('\n\n')
print(v.to_frame())
