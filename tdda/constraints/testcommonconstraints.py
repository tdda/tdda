import os
import tempfile

from tdda.referencetest import ReferenceTestCase, tag

from tdda.constraints import discover, verify
from tdda.utils import constraints_testdata_path as tdpath, rprint

TESTDATA_DIR = os.path.join(os.path.dirname(__file__), 'testdata')
TMPDIR = tempfile.gettempdir()

TDDA_MD_IGNORES = [
    r'''^\s*"?local_time"?: ["'].*['"],?$''',
    r'''^\s*"?utc_time"?: ['"].*['"],?$''',
    r'''^\s*"?creator"?: ['"]TDDA .*['"],?$''',
    r'''^\s*"?source"?: ['"]/.*/testdata/small7x5.parquet['"],?$''',
    r'''^\s*"?host"?: ['"].*['"],?$''',
    r'''^\s*"?user"?: ['"].*['"],?$''',
]


def testdata(filename):
    return os.path.join(TESTDATA_DIR, filename)


def reportpath(path):
    return tdpath(os.path.join('reports', path))


def tmppath(path):
    return tdpath(os.path.join(TMPDIR, path))



class TestCommonConstraints(ReferenceTestCase):

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

    def testSimpleAllCorrectVerificationFromCSVFile(self):
        # CSV file with full pandas tddaserial metadata.
        report = verify(tdpath('ddd.csv'), tdpath('ddd.tdda'),
                        mdpath=tdpath('ddd-pandas.tddaserial'), verbose=False)
        self.assertStringCorrect(str(report),
                                 reportpath('ddd10-all-correct.txt'))

        # CSV file with only the elevens field dtype.
        report = verify(tdpath('ddd.csv'), tdpath('ddd.tdda'),
                        mdpath=tdpath('ddd-pandas-minimal.tddaserial'),
                        verbose=False)
        self.assertStringCorrect(str(report),
                                 reportpath('ddd10-all-correct.txt'))

        report = verify(tdpath('ddd.csv'), tdpath('ddd.tdda'),
                        mdpath=tdpath('ddd.tddaserial'),
                        verbose=False)
        self.assertStringCorrect(str(report),
                                 reportpath('ddd10-all-correct.txt'))

        # CSV file with only the elevens field dtype.
        # and no format or writer
        report = verify(tdpath('ddd.csv'), tdpath('ddd.tdda'),
                        mdpath=tdpath('ddd-pandas-really-minimal.tddaserial'),
                        verbose=False)



        # Doesn't work if you specify evennulls and oddnulls as object.
        # Even though they are from pandas.
        # And calc_all_non_nulls_boolean fails with odd error
        # And it doesn't like dates fields in dtype...which is OK
        # I suppose.


class TestDiscoverReports(ReferenceTestCase):
    @classmethod
    def setUpClass(cls):
        small7x5path = testdata('small7x5.parquet')
        cls.constraints = c = discover(small7x5path, inc_rex=True,
                                       verbose=False)
        cls.constraints_json = c.to_json()

    def testDiscoverJSON(self):
        self.assertStringCorrect(self.constraints_json,
                                 tdpath('small7x5.tdda'),
                                 ignore_patterns=TDDA_MD_IGNORES)

    def testDiscoverYAML(self):
        name = 'small7x5-constraints.yaml'
        path = tmppath(name)
        self.constraints.to_yaml_report(path)
        self.assertFileCorrect(path, reportpath(name),
                                 ignore_patterns=TDDA_MD_IGNORES)

    def testDiscoverTOML(self):
        name = 'small7x5-constraints.toml'
        path = tmppath(name)
        self.constraints.to_yaml_report(path)
        self.assertFileCorrect(path, reportpath(name),
                                 ignore_patterns=TDDA_MD_IGNORES)

    def testDiscoverTextTable(self):
        name = 'small7x5-constraints.txt'
        path = tmppath(name)
        self.constraints.to_text_report(path)
        self.assertFileCorrect(path, reportpath(name))

    def testMarkdownTable(self):
        name = 'small7x5-constraints.md'
        path = tmppath(name)
        self.constraints.to_markdown_report(path)
        self.assertFileCorrect(path, reportpath(name))

    def testMultiMarkdownTable(self):
        name = 'small7x5-constraints-mmd.md'
        path = tmppath(name)
        self.constraints.to_markdown_report(path, flavour='mmd')
        self.assertFileCorrect(path, reportpath(name))

    def testDiscoverHTMLTable(self):
        name = 'small7x5-constraints.html'
        path = tmppath(name)
        self.constraints.to_html_report(path)
        self.assertFileCorrect(path, reportpath(name))




if __name__ == '__main__':
    ReferenceTestCase.main()
