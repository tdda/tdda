# -*- coding: utf-8 -*-
"""
test_using_writabletestcase.py: A simple example of how to use
tdda.writabletestcase.WritableTestCase.

Source repository: http://github.com/tdda/tdda

License: MIT

Copyright (c) Stochastic Solutions Limited 2016
"""
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import os
import tempfile

from tdda import writabletestcase
from tdda.examples.generators import generate_string, generate_file


class TestExample(writabletestcase.WritableTestCase):
    def testExampleStringGeneration(self):
        """
        This test uses generate_string() from tdda.examples.generators
        to generate some HTML as a string.

        It is similar to the reference HTML in
        tdda/examples/reference/string_result.html except that the
        Copyright and version lines are slightly different.

        As shipped, the test should pass, because the ignore_patterns
        tell it to ignore those lines.

        Make a change to the generation code in the generate_string
        function in generators.py to change the HTML output.

        The test should then fail and suggest a diff command to run
        to see the difference.

        Rerun with

            python test_using_writabletestcase.py -w

        and it should re-write the reference output to match your
        modified results.
        """
        actual = generate_string()
        this_dir = os.path.abspath(os.path.dirname(__file__))
        expected_file = os.path.join(this_dir, 'reference',
                                     'string_result.html')
        self.check_string_against_file(actual, expected_file,
                                       ignore_patterns=['Copyright',
                                                        'Version'])


    def testExampleFileGeneration(self):
        """
        This test uses generate_file() from tdda.examples.generators
        to generate some HTML as a file.

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

            python test_using_writabletestcase.py -w

        and it should re-write the reference output to match your
        modified results.
        """
        outdir = tempfile.gettempdir()
        outpath = os.path.join(outdir, 'file_result.html')
        generate_file(outpath)
        this_dir = os.path.abspath(os.path.dirname(__file__))
        expected_file = os.path.join(this_dir, 'reference',
                                     'file_result.html')
        self.check_file(outpath, expected_file,
                        ignore_patterns=['Copyright', 'Version'])


if __name__ == '__main__':
    writabletestcase.main(argv=writabletestcase.set_write_from_argv())
