import os
import tempfile

from tdda.referencetest import ReferenceTestCase, tag

from tdda.constraints import discover, verify, detect
from tdda.utils import constraints_testdata_path as tdpath, rprint, swap_ext

TESTDATA_DIR = os.path.join(os.path.dirname(__file__), 'testdata')
TMPDIR = tempfile.gettempdir()

TDDA_MD_IGNORES = [
    r"""^\s*"?local_time"?: ["'].*['"],?$""",
    r"""^\s*"?utc_time"?: ['"].*['"],?$""",
    r"""^\s*"?creator"?: ['"]?TDDA .*['"]?,?$""",
    r"""^\s*"?source"?: ['"]?/.*/testdata/small7x5.parquet['"]?,?$""",
    r"""^\s*"?host"?: ['"]?.*['"]?,?$""",
    r"""^\s*"?user"?: ['"]?.*['"]?,?$""",
]


def testdata(filename):
    return os.path.join(TESTDATA_DIR, filename)


testdata.__test__ = False


def reportpath(path):
    return tdpath(os.path.join('reports', path))


def tmppath(path):
    return tdpath(os.path.join(TMPDIR, path))


class TestCommonConstraints(ReferenceTestCase):
    def testSimpleAllCorrectVerificationFromParquetFile(self):
        # Parquet file, right types all good
        report = verify(
            tdpath('ddd.parquet'), tdpath('ddd.tdda'), verbose=False
        )
        self.assertStringCorrect(
            str(report), reportpath('ddd10-all-correct.txt')
        )

        # Also test ascii vesion
        self.assertStringCorrect(
            report.to_string(ascii=True),
            reportpath('ddd10-all-correct-ascii.txt'),
        )

    def testSimpleNotCorrectVerificationFromFile(self):
        # Also parquet; here the constraints are too tight
        # from 4-row dataset
        report = verify(
            tdpath('ddd.parquet'), tdpath('ddd4.tdda'), verbose=False
        )
        self.assertStringCorrect(
            str(report), reportpath('ddd10-not-all-correct.txt')
        )
        self.assertStringCorrect(
            report.to_string(ascii=True),
            reportpath('ddd10-not-all-correct-ascii.txt'),
        )

    def testSimpleAllNotCorrectVerificationFromCSVFile(self):
        # CSV file. Elevens is read as integers with no metadata
        report = verify(
            tdpath('ddd.csv'), tdpath('ddd.tdda'), backend='o', verbose=False
        )
        self.assertStringCorrect(
            str(report), reportpath('ddd10-elevens-wrong-type.txt')
        )

    def testSimpleAllCorrectVerificationFromCSVFile(self):
        # CSV file with full pandas tddaserial metadata.
        report = verify(
            tdpath('ddd.csv'),
            tdpath('ddd.tdda'),
            md_path=tdpath('ddd-pandas.serial'),
            backend='o',
            verbose=False,
        )
        self.assertStringCorrect(
            str(report), reportpath('ddd10-all-correct.txt')
        )

        # CSV file with only the elevens field dtype.
        # So dates fail
        report = verify(
            tdpath('ddd.csv'),
            tdpath('ddd.tdda'),
            md_path=tdpath('ddd-pandas-minimal.serial'),
            backend='o',
            verbose=False,
        )
        self.assertStringCorrect(
            str(report), reportpath('ddd10-all-correct.txt')
        )

        report = verify(
            tdpath('ddd.csv'),
            tdpath('ddd.tdda'),
            md_path=tdpath('ddd.serial'),
            verbose=False,
        )
        self.assertStringCorrect(
            str(report), reportpath('ddd10-all-correct.txt')
        )

        # CSV file with only the elevens field dtype.
        # and no format or writer
        report = verify(
            tdpath('ddd.csv'),
            tdpath('ddd.tdda'),
            md_path=tdpath('ddd-pandas-really-minimal.serial'),
            backend='o',
            verbose=False,
        )

        # Doesn't work if you specify evennulls and oddnulls as object.
        # Even though they are from pandas.
        # And calc_all_non_nulls_boolean fails with odd error
        # And it doesn't like dates fields in dtype...which is OK
        # I suppose.


class TestDiscoverReports(ReferenceTestCase):
    norm_paths = True

    @classmethod
    def setUpClass(cls):
        small7x5path = testdata('small7x5.parquet')
        cls.constraints = c = discover(
            small7x5path, inc_rex=True, verbose=False
        )
        cls.constraints_json = c.to_json()

    def testDiscoverJSON(self):
        self.assertJSONCorrect(
            self.constraints_json,
            tdpath('small7x5.tdda'),
            remove_keys={'creation_metadata'},
        )

    def testDiscoverYAML(self):
        name = 'small7x5-constraints.yaml'
        path = tmppath(name)
        self.constraints.to_yaml_report(path)
        self.assertFileCorrect(
            path, reportpath(name), ignore_patterns=TDDA_MD_IGNORES
        )

    def testDiscoverTOML(self):
        name = 'small7x5-constraints.toml'
        path = tmppath(name)
        self.constraints.to_yaml_report(path)
        self.assertFileCorrect(
            path, reportpath(name), ignore_patterns=TDDA_MD_IGNORES
        )

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


class TestVerificationReports(ReferenceTestCase):
    @classmethod
    def setUpClass(cls):
        small7x5path = testdata('small7x5.parquet')
        bads_path = testdata('small7x5bad.parquet')
        constraints_path = testdata('small7x5.tdda')
        cls.verification = verify(
            small7x5path, constraints_path, verbose=False
        )
        cls.bad_verification = verify(
            bads_path, constraints_path, verbose=False
        )

    def testVerifyGood(self):
        name = 'small7x5-verification_good.txt'
        path = tmppath(name)
        self.assertStringCorrect(
            self.verification.to_string(), reportpath(name)
        )

    def testVerifyBads(self):
        name = 'small7x5-verification_bad.txt'
        path = tmppath(name)
        self.assertStringCorrect(
            self.bad_verification.to_string(), reportpath(name)
        )


class TestDetectionReports(ReferenceTestCase):
    @classmethod
    def setUpClass(cls):
        constraints_path = testdata('small7x5.tdda')

        cls.formats = ['html', 'md', 'txt', 'json', 'yaml', 'toml']

        # TRAINING DATA: NO FAILURES; DETECTION TABLE GENERATED

        train_path = testdata('small7x5.parquet')  # no failures
        cls.actual_train_detect_full_path = tmppath('small7x5-full.parquet')
        cls.actual_train_detect_bads_path = tmppath('small7x5-bads.parquet')

        cls.train_bads_detection = detect(
            train_path,
            constraints_path,
            cls.actual_train_detect_bads_path,
            # write_all_records = False,  # default
            # interleave = True,          # default
            report_formats=cls.formats,
            verbose=False,
        )

        cls.train_full_detection = detect(
            train_path,
            constraints_path,
            cls.actual_train_detect_full_path,
            write_all_records=True,
            interleave=False,
            report_formats=cls.formats,
            verbose=False,
        )

        # VALIDATION DATA: SOME FAILURES: DETECTION TABLE GENERATED

        validation_path = testdata('small7x5bad.parquet')  # some failures

        detect_full = 'small7x5bad-full.parquet'
        detect_bads = 'small7x5bad-bads.parquet'
        cls.ref_validation_detect_full_path = testdata(detect_full)
        cls.ref_validation_detect_bads_path = testdata(detect_bads)
        cls.actual_validation_detect_full_path = tmppath(detect_full)
        cls.actual_validation_detect_bads_path = tmppath(detect_bads)

        cls.validation_bads_detection = detect(
            validation_path,
            constraints_path,
            cls.actual_validation_detect_bads_path,
            # write_all_records = False,  # default
            # interleave = True,          # default
            report_formats=cls.formats,
            verbose=False,
        )

        cls.validation_full_detection = detect(
            validation_path,
            constraints_path,
            cls.actual_validation_detect_full_path,
            write_all_records=True,
            interleave=False,
            report_formats=cls.formats,
            verbose=False,
        )

    def testDetectionTrainBads(self):
        paths = [
            swap_ext(self.actual_train_detect_bads_path, fmt)
            for fmt in self.formats
        ]
        for path in paths:
            if os.path.exists(path):
                os.unlink(path)

        # No failures
        self.assertEqual(self.train_bads_detection.failures, 0)

        # So no detection table
        self.assertFalse(os.path.exists(self.actual_train_detect_bads_path))

        # And no reports
        for path in paths:
            self.assertFalse(os.path.exists(path))

    def testDetectionTrainFull(self):
        paths = [
            swap_ext(self.actual_train_detect_full_path, fmt)
            for fmt in self.formats
        ]
        for path in paths:
            if os.path.exists(path):
                os.unlink(path)
        # No failures
        self.assertEqual(self.train_full_detection.failures, 0)

        # So no detection table
        self.assertFalse(os.path.exists(self.actual_train_detect_full_path))

        # And no reports
        for path in paths:
            self.assertFalse(os.path.exists(path))

    def testDetectionValidationBads(self):
        # No failures
        self.assertEqual(self.validation_bads_detection.failures, 4)

        # So no detection table
        self.assertTrue(
            os.path.exists(self.actual_validation_detect_bads_path)
        )

        # And no reports
        for fmt in self.formats:
            path = swap_ext(self.actual_validation_detect_bads_path, fmt)
            self.assertTrue(os.path.exists(path))

    def testDetectionValidationFull(self):
        # No failures
        self.assertEqual(self.validation_full_detection.failures, 4)

        # So no detection table
        self.assertTrue(
            os.path.exists(self.actual_validation_detect_full_path)
        )

        # And no reports
        for fmt in self.formats:
            path = swap_ext(self.actual_validation_detect_full_path, fmt)
            self.assertTrue(os.path.exists(path))


if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
