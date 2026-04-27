import os
import sys
import tempfile
import unittest
from tdda.referencetest import ReferenceTestCase


from tdda.referencetest.tagutils import copy_files
from tdda.referencetest.gentest import exec_command

IS_NOT_PY_312_PLUS = sys.version_info < (3, 12)

TMP = (
    tempfile.TemporaryDirectory().name
    if IS_NOT_PY_312_PLUS
    else tempfile.TemporaryDirectory(delete=False).name
)

THISDIR = os.path.dirname(__file__)
REFDIR = os.path.join(THISDIR, 'testdata')


@unittest.skipIf(IS_NOT_PY_312_PLUS, 'requires Python 3.12+')
class TestTagFailures(ReferenceTestCase):
    def testTagFailures(self):
        # Copy the files into place
        copy_files(dest=TMP)

        command = f'{sys.executable} test_tagging.py -F'
        (output, error, exception, exit_code, duration) = exec_command(
            command, TMP
        )  # Write the failing tests

        # Tag the failures
        command = 'tdda tag'
        (output, error, exception, exit_code, duration) = exec_command(
            command, TMP
        )  # Tag the failing tests

        names = [f'test_tags{c}.py' for c in 'abc']
        actuals = [os.path.join(TMP, f) for f in names]
        refs = [os.path.join(REFDIR, f + '-tagged') for f in names]

        self.assertFilesCorrect(actuals, refs)

        # Report the tagged tests
        command = f'{sys.executable} test_tagging.py -0'
        (output, error, exception, exit_code, duration) = exec_command(
            command, TMP
        )  # Tag the failing tests
        tagged = [L.strip() for L in output.splitlines() if L.strip()]
        self.assertEqual(tagged, ['test_tagsa.TestA', 'test_tagsc.TestC'])

        # Untag everything
        command = f'{sys.executable} test_tagging.py -9'
        (output, error, exception, exit_code, duration) = exec_command(
            command, TMP
        )  # Tag the failing tests

        refs2 = [os.path.join(REFDIR, f) for f in names]
        self.assertFilesCorrect(actuals, refs2)


if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
