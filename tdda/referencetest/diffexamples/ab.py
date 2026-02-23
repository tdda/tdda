from tdda.referencetest.checkpandas import PandasComparison
from tdda.serial import csv_to_pandas

from tdda.utils import stdout_console as console
a = csv_to_pandas('a.csv')
b = csv_to_pandas('b.csv')
print(a)
print(b)

c = PandasComparison()
r = c.check_dataframe(a, b)
d = r.diffs.dfd.diff
console.print(d)
console.print(d.details_table(a, b))

