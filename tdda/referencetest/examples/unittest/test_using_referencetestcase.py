# -*- coding: utf-8 -*-
"""
test_using_referencetestcase.py: A simple example of how to use
                                 tdda.referencetest.ReferenceTestCase.

Source repository: http://github.com/tdda/tdda

License: MIT

Copyright (c) Stochastic Solutions Limited 2016
"""

from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import sys
import os
import tempfile

from tdda.referencetest import ReferenceTestCase

# ensure we can import the generators module in the directory above
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from generators import generate_string, generate_file


class TestExample(ReferenceTestCase):
    def __init__(self, *args, **kwargs):
        ReferenceTestCase.__init__(self, *args, **kwargs)
        this_dir = os.path.abspath(os.path.dirname(__file__))
        self.set_data_location(os.path.join(this_dir, '..', 'reference'))

    def testExampleStringGeneration(self):
        """
        This test uses generate_string() from generators.py to generate
        some HTML as a string.

        It is similar to the reference HTML in
            tdda/referencetest/examples/reference/string_result.html
        except that the Copyright and version lines are slightly different.

        As shipped, the test should pass, because the ignore_patterns
        tell it to ignore those lines.

        Make a change to the generation code in the generate_string
        function in generators.py to change the HTML output.

        The test should then fail and suggest a diff command to run
        to see the difference.

        Rerun with

            python test_using_referencetestcase.py --write-all

        and it should re-write the reference output to match your
        modified results.
        """
        actual = generate_string()
        self.assertStringCorrect(actual, 'string_result.html',
                                 ignore_substrings=['Copyright', 'Version'])


    def testExampleFileGeneration(self):
        """
        This test uses generate_file() from generators.py to generate
        some HTML as a file.

        It is similar to the reference HTML in
        tdda/examples/reference/file_result.html except that the
        Copyright and version lines are slightly different.

        As shipped, the test should pass, because the ignore_patterns
        tell it to ignore those lines.

        Make a change to the generation code in the generate_file function
        in generators.py to change the HTML output.

        The test should then fail and suggest a diff command to run
        to see the difference.

        Rerun with

            python test_using_referencetestcase.py --write-all

        and it should re-write the reference output to match your
        modified results.
        """
        outdir = tempfile.gettempdir()
        outpath = os.path.join(outdir, 'file_result.html')
        generate_file(outpath)
        self.assertFileCorrect(outpath, 'file_result.html',
                               ignore_patterns=['Copyright', 'Version'])


if __name__ == '__main__':
    ReferenceTestCase.main()

