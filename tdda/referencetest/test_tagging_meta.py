"""
test_tagging_meta.py: Automatically generated test code from tdda gentest.

Generation command:

tdda gentest --non-zero-exit 'python test_tagging.py -F' 'test_tagging_meta.py' '.'
"""

import os
import shutil
import sys
import tempfile

from tdda.referencetest import ReferenceTestCase
from tdda.referencetest.gentest import exec_command


class Test_TAGGING_META(ReferenceTestCase):
    command = f'{sys.executable} testdata/test_tagging.py -F'
    cwd = os.path.abspath(os.path.dirname(__file__))
    refdir = os.path.join(cwd, 'ref', 'tagging_meta')
    orig_tmpdir = (
        '/var/folders/2y/72gfd2691h9gf2cy48xp8slh0000gn/T/tmph73lgqj_'
    )
    if not os.environ.get('TMPDIR_SET_BY_GENTEST'):
        tmpdir = tempfile.mkdtemp()
        os.environ['TMPDIR'] = tmpdir
        os.environ['TMPDIR_SET_BY_GENTEST'] = 'true'
    else:
        tmpdir = os.environ['TMPDIR']

    generated_files = [
        os.path.join(tmpdir, '2026-04-11T163000-failing-tests.txt')
    ]

    @classmethod
    def setUpClass(cls):
        for path in cls.generated_files:
            if os.path.exists(path):
                os.unlink(path)
        (cls.output, cls.error, cls.exception, cls.exit_code, cls.duration) = (
            exec_command(cls.command, cls.cwd)
        )
        s = 'Failing tests written to '
        lines = [L for L in cls.output.splitlines() if s in L]
        cls.failures_file = lines[0][len(s) :]

    def test_no_exception(self):
        self.assertIsNone(self.exception)

    def test_exit_code(self):
        self.assertEqual(self.exit_code, 1)

    def test_stdout(self):
        patterns = [
            r'^Failing tests written to (.*)\-failing\-tests\.txt$',
        ]
        self.assertStringCorrect(
            self.output,
            os.path.join(self.refdir, 'STDOUT'),
            ignore_patterns=patterns,
        )

    def test_stderr(self):
        substrings = [
            '/Users/njr/python/tdda/tdda/referencetest/scratch',
        ]
        patterns = ['Ran 5 tests in (0.[0-9]+)s']
        remove = ['~~~']  # Python 3.13+ enhanced traceback expression markers
        self.assertStringCorrect(
            self.error,
            os.path.join(self.refdir, 'STDERR'),
            ignore_substrings=substrings,
            ignore_patterns=patterns,
            remove_lines=remove,
        )

    def test_test_failures_file(self):
        with open(os.path.join(self.refdir, 'failures.txt')) as f:
            ref_lines = [L.strip() for L in f.readlines() if L.strip()]
        with open(self.failures_file) as f:
            actual_lines = [L.strip() for L in f.readlines() if L.strip()]
        nR, nA = len(ref_lines), len(actual_lines)
        self.assertEqual(nR, nA)
        for r, a in zip(ref_lines, actual_lines):
            self.assertEqual(a[-len(r) :], r)


if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
