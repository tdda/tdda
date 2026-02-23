import sys

from tdda.abstractdf import df_join
from tdda.referencetest.checkpandas import PandasComparison
from tdda.serial import csv_to_pandas, csv_to_polars

from tdda.utils import stdout_console as console

from tdda.referencetest.diffutils import join_for_diff

print('PANDAS\n\n')

a = csv_to_pandas('a.csv')
b = csv_to_pandas('f5.tsv')
print(a)
print(b)

L, R, key = join_for_diff(a, b, 'row')
print(L)
print(R)
sys.exit(0)



# c = PandasComparison()
# r = c.check_dataframe(a, b, quick=False)
# d = r.diffs.dfd.diff
# console.print(d)
# console.print(d.details_table(a, b))


print('POLARS\n\n')
a = csv_to_polars('an.csv')
b = csv_to_polars('bn.csv')
print(a)
print(b)

L, R, k = join_for_diff(a, b, 'row')
print(L)
print(R)



