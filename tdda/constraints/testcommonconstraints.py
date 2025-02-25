import os
from tdda.referencetest import ReferenceTestCase, tag

from tdda.constraints import verify
from tdda.utils import constraints_testdata_path as tdpath, rprint



def reportpath(path):
    return tdpath(os.path.join('reports', path))


class TestCommon(ReferenceTestCase):

    def testSimpleAllCorrectVerificationFromFile(self):
        report = verify(tdpath('ddd.parquet'), tdpath('ddd.tdda'),
                        verbose=False)
        self.assertStringCorrect(str(report),
                                 reportpath('ddd10-all-correct.txt'))
        self.assertStringCorrect(report.to_string(ascii=True),
                                 reportpath('ddd10-all-correct-ascii.txt'))

    def testSimpleNotCorrectVerificationFromFile(self):
        report = verify(tdpath('ddd.parquet'), tdpath('ddd4.tdda'),
                        verbose=False)
        self.assertStringCorrect(str(report),
                                 reportpath('ddd10-not-all-correct.txt'))
        self.assertStringCorrect(report.to_string(ascii=True),
                                 reportpath('ddd10-not-all-correct-ascii.txt'))

if __name__ == '__main__':
    ReferenceTestCase.main()
