"""
testexamples.py: tests for the `tdda examples` command.

Tests the command via main_with_argv (not subprocess), so they always
exercise the current source tree rather than whatever `tdda` is on $PATH.

Run standalone:
    python testexamples.py [-F] [-1] [-1W]

Or included in the full suite via testtdda.py.
"""

import os
import shutil
import tempfile
import unittest

from tdda.referencetest import ReferenceTestCase, tag
from tdda.referencetest.captureoutput import capture_output
from tdda.constraints.console import main_with_argv


def is_online():
    try:
        import requests
        requests.get('https://github.com', timeout=3)
        return True
    except Exception:
        return False


THISDIR = os.path.dirname(os.path.abspath(__file__))
REFDIR = os.path.join(THISDIR, 'testdata', 'examples')


def capture_stdout(argv):
    """Run main_with_argv(argv), capturing and returning stdout."""
    with capture_output() as c:
        main_with_argv(argv)
    return str(c)


def dir_listing(path):
    """Sorted recursive file listing relative to path, one per line."""
    lines = []
    for root, dirs, files in os.walk(path):
        dirs.sort()
        rel_root = os.path.relpath(root, path)
        for f in sorted(files):
            rel = f if rel_root == '.' else os.path.join(rel_root, f)
            lines.append(rel.replace(os.sep, '/'))
    return '\n'.join(lines) + '\n'


class TestExamplesDryRun(ReferenceTestCase):
    """Test --dryrun output for various argument combinations."""

    def ref(self, name):
        return os.path.join(REFDIR, name)

    def test_dryrun_default(self):
        output = capture_stdout(['tdda', 'examples', '--dryrun'])
        self.assertStringCorrect(output, self.ref('dryrun-default.txt'))

    def test_dryrun_serial(self):
        output = capture_stdout(['tdda', 'examples', 'serial', '--dryrun'])
        self.assertStringCorrect(output, self.ref('dryrun-serial.txt'))

    def test_dryrun_constraints(self):
        output = capture_stdout(
            ['tdda', 'examples', 'constraints', '--dryrun']
        )
        self.assertStringCorrect(output, self.ref('dryrun-constraints.txt'))

    def test_dryrun_serial_constraints(self):
        output = capture_stdout(
            ['tdda', 'examples', 'serial', 'constraints', '--dryrun']
        )
        self.assertStringCorrect(
            output, self.ref('dryrun-serial-constraints.txt')
        )

    def test_dryrun_all(self):
        output = capture_stdout(['tdda', 'examples', 'all', '--dryrun'])
        self.assertStringCorrect(output, self.ref('dryrun-all.txt'))

    def test_dryrun_book(self):
        output = capture_stdout(['tdda', 'examples', 'book', '--dryrun'])
        self.assertStringCorrect(output, self.ref('dryrun-book.txt'))


class TestExamplesSerial(ReferenceTestCase):
    """Test that tdda examples serial copies the right files."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        cls.passed = False
        main_with_argv(
            ['tdda', 'examples', 'serial', cls.tmpdir], verbose=False
        )
        cls.outdir = os.path.join(cls.tmpdir, 'serial_examples')

    @classmethod
    def tearDownClass(cls):
        if cls.passed:
            shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def ref(self, name):
        return os.path.join(REFDIR, name)

    def test_output_dir_exists(self):
        self.assertTrue(os.path.isdir(self.outdir))

    def test_file_listing(self):
        listing = dir_listing(self.outdir)
        self.assertStringCorrect(listing, self.ref('serial-listing.txt'))
        self.__class__.passed = True


class TestExamplesConstraints(ReferenceTestCase):
    """Test that tdda examples constraints copies the right files."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        cls.passed = False
        main_with_argv(
            ['tdda', 'examples', 'constraints', cls.tmpdir], verbose=False
        )
        cls.outdir = os.path.join(cls.tmpdir, 'constraints_examples')

    @classmethod
    def tearDownClass(cls):
        if cls.passed:
            shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def ref(self, name):
        return os.path.join(REFDIR, name)

    def test_output_dir_exists(self):
        self.assertTrue(os.path.isdir(self.outdir))

    def test_file_listing(self):
        listing = dir_listing(self.outdir)
        self.assertStringCorrect(listing, self.ref('constraints-listing.txt'))
        self.__class__.passed = True


class TestExamplesAll(ReferenceTestCase):
    """Test that tdda examples TMPDIR copies all default examples."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        cls.passed = False
        main_with_argv(['tdda', 'examples', cls.tmpdir], verbose=False)

    @classmethod
    def tearDownClass(cls):
        if cls.passed:
            shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def ref(self, name):
        return os.path.join(REFDIR, name)

    def test_file_listing(self):
        listing = dir_listing(self.tmpdir)
        self.assertStringCorrect(listing, self.ref('all-listing.txt'))
        self.__class__.passed = True


class TestExamplesAllCWD(ReferenceTestCase):
    """Test that tdda examples (no dest) copies to current directory."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        cls.passed = False
        cls.origdir = os.getcwd()
        os.chdir(cls.tmpdir)
        main_with_argv(['tdda', 'examples'], verbose=False)

    @classmethod
    def tearDownClass(cls):
        os.chdir(cls.origdir)
        if cls.passed:
            shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def ref(self, name):
        return os.path.join(REFDIR, name)

    def test_file_listing(self):
        listing = dir_listing(self.tmpdir)
        self.assertStringCorrect(listing, self.ref('all-listing.txt'))
        self.__class__.passed = True


@unittest.skipUnless(is_online(), 'Cannot reach GitHub')
class TestExamplesBook(ReferenceTestCase):
    """Test that tdda examples book TMPDIR copies book examples."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.mkdtemp()
        cls.passed = False
        main_with_argv(['tdda', 'examples', 'book', cls.tmpdir], verbose=False)
        cls.outdir = os.path.join(cls.tmpdir, 'book_examples')

    @classmethod
    def tearDownClass(cls):
        if cls.passed:
            shutil.rmtree(cls.tmpdir, ignore_errors=True)

    def ref(self, name):
        return os.path.join(REFDIR, name)

    def test_output_dir_exists(self):
        self.assertTrue(os.path.isdir(self.outdir))

    def test_file_listing(self):
        listing = dir_listing(self.outdir)
        self.assertStringCorrect(listing, self.ref('book-listing.txt'))
        self.__class__.passed = True


if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
