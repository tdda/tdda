import os
from tdda.referencetest import ReferenceTestCase, tag

from tdda.constraints import verify
from tdda.utils import constraints_testdata_path as tdpath, rprint



def reportpath(path):
    return tdpath(os.path.join('reports', path))


class TestCommon(ReferenceTestCase):

    def testSimpleAllCorrectVerificationFromParquetFile(self):
        # Parquet file, right types all good
        report = verify(tdpath('ddd.parquet'), tdpath('ddd.tdda'),
                        verbose=False)
        self.assertStringCorrect(str(report),
                                 reportpath('ddd10-all-correct.txt'))

        # Also test ascii vesion
        self.assertStringCorrect(report.to_string(ascii=True),
                                 reportpath('ddd10-all-correct-ascii.txt'))

    def testSimpleNotCorrectVerificationFromFile(self):
        # Also parquet; here the constraints are too tight
        # from 4-row dataset
        report = verify(tdpath('ddd.parquet'), tdpath('ddd4.tdda'),
                        verbose=False)
        self.assertStringCorrect(str(report),
                                 reportpath('ddd10-not-all-correct.txt'))
        self.assertStringCorrect(report.to_string(ascii=True),
                                 reportpath('ddd10-not-all-correct-ascii.txt'))

    def testSimpleAllNotCorrectVerificationFromCSVFile(self):
        # CSV file. Elevens is read as integers with no metadata
        report = verify(tdpath('ddd.csv'), tdpath('ddd.tdda'),
                        verbose=False)
        self.assertStringCorrect(str(report),
                                 reportpath('ddd10-elevens-wrong-type.txt'))
    #@tag
    def atestSimpleAllCorrectVerificationFromCSVFile(self):
        # CSV file with pandas tddaserial metadata.
        report = verify(tdpath('ddd.csv'), tdpath('ddd.tdda'),
                        mdpath=tdpath('ddd-pandas.tddaserial'), verbose=False)
        self.assertStringCorrect(str(report),
                                 reportpath('ddd10-all-correct.txt'))


if __name__ == '__main__':
    ReferenceTestCase.main()
