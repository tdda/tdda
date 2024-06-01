import pandas as pd

from tdda.referencetest import ReferenceTestCase, tag
from tdda.referencetest.referencetest import ReferenceTest
from tdda.referencetest.checkpandas import (
    PandasComparison,
    types_match,
    loosen_type,
)

import os

TESTDATA = os.path.join(os.path.dirname(__file__), 'testdata')
PQ_REF4_PATH = os.path.join(TESTDATA, 'four-squares.parquet')
CSV_REF4_PATH = os.path.join(TESTDATA, 'four-squares.csv')

class TestOne(ReferenceTestCase):

    def testNoDiffsInMem(self):
        self.assertDataFramesEqual(four_squares(), four_squares())

    def testNoDiffsMemParquet(self):
        self.assertDataFrameCorrect(four_squares(), PQ_REF4_PATH)

    def testNoDiffsMemCSV(self):
        self.assertDataFrameCorrect(four_squares(), CSV_REF4_PATH)

    def testNoDiffsParquetParquet(self):
        self.assertOnDiskDataFrameCorrect(PQ_REF4_PATH, PQ_REF4_PATH)

    def testNoDiffsParquetCSV(self):
        self.assertOnDiskDataFrameCorrect(PQ_REF4_PATH, CSV_REF4_PATH)

    def testNoDiffsCSVParquet(self):
        self.assertOnDiskDataFrameCorrect(CSV_REF4_PATH, PQ_REF4_PATH)

    def testNoDiffsCSVCSV(self):
        self.assertOnDiskDataFrameCorrect(CSV_REF4_PATH, CSV_REF4_PATH)

    def testOneDiffInMem(self):
        c = PandasComparison()
        ref = four_squares()
        actual = four_squares_and_ten()
        r = c.check_dataframe(actual, ref)
        self.assertEqual(r.failures, 1)
        print(r.diffs)
        print(r.diffs.df)

    def testDiffColTypeInMemIntStr(self):
        c = PandasComparison()
        actual = four_squares()
        actual['squares'] = [str(sq) for sq in actual['squares']]
        expected = four_squares()
        r = c.check_dataframe(actual, expected)
        self.assertEqual(r.failures, 1)
        print(r.diffs)
        print(r.diffs.df)

    def testDiffColTypeInMemIntFloat(self):
        c = PandasComparison()
        actual = four_squares()
        actual['squares'] = [float(sq) for sq in actual['squares']]
        expected = four_squares()
        r = c.check_dataframe(actual, expected)
        self.assertEqual(r.failures, 1)
        print(r.diffs)
        print(r.diffs.df)

    def testDiffColTypeInMemIntFloat(self):
        c = PandasComparison()
        ref = four_squares()
        actual = pd.DataFrame({
            'squares': ref['squares'],
            'row': ref['row'],
        })
        self.assertEqual(list(reversed(list(actual))), list(ref))
        r = c.check_dataframe(actual, ref)
        self.assertEqual(r.failures, 1)
        print(r.diffs)
        print(r.diffs.df)

def four_squares():
    return pd.DataFrame({
        'row': [0, 1, 2, 3],
        'squares': [0, 1, 4, 9],
    })


def four_squares_and_ten():
    return pd.DataFrame({
        'row': [0, 1, 2, 3],
        'squares': [0, 1, 10, 9],
    })

def write_ref():
    df = four_squares()
    df.to_parquet(PQ_REF4_PATH, index=False)
    df.to_csv(CSV_REF4_PATH, index=False)



if __name__ == '__main__':
    # write_ref()              # generate test files
    ReferenceTestCase.main()
