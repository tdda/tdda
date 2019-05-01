# -*- coding: utf-8 -*-

"""
test_examples.py: Automatically generated test code from tdda gentest.

Generation command:

  tdda gentest 'tdda examples constraints $TMPDIR' 'test_examples.py' '.' STDOUT STDERR
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

import os
import sys
import tempfile

from tdda.referencetest import ReferenceTestCase
from tdda.referencetest.gentest import exec_command



class TestEXAMPLES(ReferenceTestCase):
    command = 'tdda examples constraints $TMPDIR'
    cwd = os.path.abspath(os.path.dirname(__file__))
    refdir = os.path.join(cwd, 'ref', 'examples')
    orig_tmpdir = '/var/folders/zv/3xvhmvpj0216687_pk__2f5h0000gn/T/tmpAN6YaZ'
    if not os.environ.get('TMPDIR_SET_BY_GENTEST'):
        tmpdir = tempfile.mkdtemp()
        os.environ['TMPDIR'] = tmpdir
        os.environ['TMPDIR_SET_BY_GENTEST'] = 'true'
    else:
        tmpdir = os.environ['TMPDIR']
    generated_files = [
        os.path.join(tmpdir, 'constraints_examples/README.md'),
    os.path.join(tmpdir, 'constraints_examples/accounts25k.tdda'),
    os.path.join(tmpdir, 'constraints_examples/accounts_detect_25k_against_1k.py'),
    os.path.join(tmpdir, 'constraints_examples/accounts_discover_1k.py'),
    os.path.join(tmpdir, 'constraints_examples/accounts_verify_1k.py'),
    os.path.join(tmpdir, 'constraints_examples/accounts_verify_25k.py'),
    os.path.join(tmpdir, 'constraints_examples/accounts_verify_25k_against_1k.py'),
    os.path.join(tmpdir, 'constraints_examples/accounts_verify_25k_against_1k_feather.py'),
    os.path.join(tmpdir, 'constraints_examples/accounts_verify_25k_to_frame.py'),
    os.path.join(tmpdir, 'constraints_examples/elements118.tdda'),
    os.path.join(tmpdir, 'constraints_examples/elements_detect_118_against_92.py'),
    os.path.join(tmpdir, 'constraints_examples/elements_discover_92.py'),
    os.path.join(tmpdir, 'constraints_examples/elements_verify_118.py'),
    os.path.join(tmpdir, 'constraints_examples/elements_verify_118_against_92.py'),
    os.path.join(tmpdir, 'constraints_examples/elements_verify_118_against_92_feather.py'),
    os.path.join(tmpdir, 'constraints_examples/elements_verify_92.py'),
    os.path.join(tmpdir, 'constraints_examples/files_extension.py'),
    os.path.join(tmpdir, 'constraints_examples/simple_discovery.py'),
    os.path.join(tmpdir, 'constraints_examples/simple_verification.py'),
    os.path.join(tmpdir, 'constraints_examples/simple_verify_fail.py'),
    os.path.join(tmpdir, 'constraints_examples/simple_verify_pass.py'),
    os.path.join(tmpdir, 'constraints_examples/testdata/accounts1k.csv'),
    os.path.join(tmpdir, 'constraints_examples/testdata/accounts1k.tdda'),
    os.path.join(tmpdir, 'constraints_examples/testdata/accounts25k.csv'),
    os.path.join(tmpdir, 'constraints_examples/testdata/ddd.csv'),
    os.path.join(tmpdir, 'constraints_examples/testdata/ddd.tdda'),
    os.path.join(tmpdir, 'constraints_examples/testdata/elements118.csv'),
    os.path.join(tmpdir, 'constraints_examples/testdata/elements118.feather'),
    os.path.join(tmpdir, 'constraints_examples/testdata/elements118.pmm'),
    os.path.join(tmpdir, 'constraints_examples/testdata/elements92.csv'),
    os.path.join(tmpdir, 'constraints_examples/testdata/elements92.tdda')
    ]
    @classmethod
    def setUpClass(cls):
        for path in cls.generated_files:
            if os.path.exists(path):
                os.unlink(path)
        (cls.output,
         cls.error,
         cls.exc,
         cls.exit_code,
         cls.duration) = exec_command(cls.command, cls.cwd)

    def test_no_exception(self):
        msg = 'No exception should be generated'
        self.assertEqual((str(self.exc), msg), ('None', msg))

    def test_exit_code(self):
        self.assertEqual(self.exit_code, 0)

    def test_stdout(self):
        substrings = [
            self.orig_tmpdir,
        ]
        self.assertStringCorrect(self.output,
                                 os.path.join(self.refdir, 'STDOUT'),
                                 ignore_substrings=substrings)

    def test_stderr(self):
        self.assertStringCorrect(self.error,
                                 os.path.join(self.refdir, 'STDERR'))

    def test_README_md(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/README.md'),
                               os.path.join(self.refdir, 'README.md'))

    def test_accounts25k_tdda(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/accounts25k.tdda'),
                               os.path.join(self.refdir, 'accounts25k.tdda'))

    def test_accounts_detect_25k_against_1k_py(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/accounts_detect_25k_against_1k.py'),
                               os.path.join(self.refdir, 'accounts_detect_25k_against_1k.py'))

    def test_accounts_discover_1k_py(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/accounts_discover_1k.py'),
                               os.path.join(self.refdir, 'accounts_discover_1k.py'))

    def test_accounts_verify_1k_py(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/accounts_verify_1k.py'),
                               os.path.join(self.refdir, 'accounts_verify_1k.py'))

    def test_accounts_verify_25k_py(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/accounts_verify_25k.py'),
                               os.path.join(self.refdir, 'accounts_verify_25k.py'))

    def test_accounts_verify_25k_against_1k_py(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/accounts_verify_25k_against_1k.py'),
                               os.path.join(self.refdir, 'accounts_verify_25k_against_1k.py'))

    def test_accounts_verify_25k_against_1k_feather_py(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/accounts_verify_25k_against_1k_feather.py'),
                               os.path.join(self.refdir, 'accounts_verify_25k_against_1k_feather.py'))

    def test_accounts_verify_25k_to_frame_py(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/accounts_verify_25k_to_frame.py'),
                               os.path.join(self.refdir, 'accounts_verify_25k_to_frame.py'))

    def test_elements118_tdda(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/elements118.tdda'),
                               os.path.join(self.refdir, 'elements118.tdda'))

    def test_elements_detect_118_against_92_py(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/elements_detect_118_against_92.py'),
                               os.path.join(self.refdir, 'elements_detect_118_against_92.py'))

    def test_elements_discover_92_py(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/elements_discover_92.py'),
                               os.path.join(self.refdir, 'elements_discover_92.py'))

    def test_elements_verify_118_py(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/elements_verify_118.py'),
                               os.path.join(self.refdir, 'elements_verify_118.py'))

    def test_elements_verify_118_against_92_py(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/elements_verify_118_against_92.py'),
                               os.path.join(self.refdir, 'elements_verify_118_against_92.py'))

    def test_elements_verify_118_against_92_feather_py(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/elements_verify_118_against_92_feather.py'),
                               os.path.join(self.refdir, 'elements_verify_118_against_92_feather.py'))

    def test_elements_verify_92_py(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/elements_verify_92.py'),
                               os.path.join(self.refdir, 'elements_verify_92.py'))

    def test_files_extension_py(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/files_extension.py'),
                               os.path.join(self.refdir, 'files_extension.py'))

    def test_simple_discovery_py(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/simple_discovery.py'),
                               os.path.join(self.refdir, 'simple_discovery.py'))

    def test_simple_verification_py(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/simple_verification.py'),
                               os.path.join(self.refdir, 'simple_verification.py'))

    def test_simple_verify_fail_py(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/simple_verify_fail.py'),
                               os.path.join(self.refdir, 'simple_verify_fail.py'))

    def test_simple_verify_pass_py(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/simple_verify_pass.py'),
                               os.path.join(self.refdir, 'simple_verify_pass.py'))

    def test_accounts1k_csv(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/testdata/accounts1k.csv'),
                               os.path.join(self.refdir, 'accounts1k.csv'))

    def test_accounts1k_tdda(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/testdata/accounts1k.tdda'),
                               os.path.join(self.refdir, 'accounts1k.tdda'))

    def test_accounts25k_csv(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/testdata/accounts25k.csv'),
                               os.path.join(self.refdir, 'accounts25k.csv'))

    def test_ddd_csv(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/testdata/ddd.csv'),
                               os.path.join(self.refdir, 'ddd.csv'))

    def test_ddd_tdda(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/testdata/ddd.tdda'),
                               os.path.join(self.refdir, 'ddd.tdda'))

    def test_elements118_csv(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/testdata/elements118.csv'),
                               os.path.join(self.refdir, 'elements118.csv'))

    def test_elements118_feather(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/testdata/elements118.feather'),
                               os.path.join(self.refdir, 'elements118.feather'))

    def test_elements118_pmm(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/testdata/elements118.pmm'),
                               os.path.join(self.refdir, 'elements118.pmm'))

    def test_elements92_csv(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/testdata/elements92.csv'),
                               os.path.join(self.refdir, 'elements92.csv'))

    def test_elements92_tdda(self):
        self.assertFileCorrect(os.path.join(self.tmpdir, 'constraints_examples/testdata/elements92.tdda'),
                               os.path.join(self.refdir, 'elements92.tdda'))

if __name__ == '__main__':
    ReferenceTestCase.main()
