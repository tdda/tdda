import numpy as np
import pandas as pd

from tdda import rexpy

df = pd.DataFrame({'a3': ["one", "two", np.NaN],
                   'a45': ['three', 'four', 'five']})

re3 = rexpy.pdextract(df['a3'])
re45 = rexpy.pdextract(df['a45'])
re345 = rexpy.pdextract([df['a3'], df['a45']])

print('  re3: %s' % re3)
print(' re45: %s' % re45)
print('re345: %s' % re345)




