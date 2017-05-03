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
import unittest

from tdda.referencetest import ReferenceTestCase

# ensure we can import the generators module in the directory above
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# directory where reference results are kept
reference_data_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                  '..', 'reference')

from generators import generate_string, generate_file

try:
    from dataframes import generate_dataframe
except ImportError:
    generate_dataframe = None


@unittest.skipIf(generate_dataframe is None, 'Pandas tests skipped')
class TestStructuredDataExample(ReferenceTestCase):
    def testExampleDatafFameGeneration(self):
        """
        This test uses generate_dataframe() from dataframes.py to
        generate a simple Pandas DataFrame.

        The test checks the DataFrame is as expected, in terms of both
        data content (the values) and metadata (the types, order, etc)
        of the columns.
        """
        df = generate_dataframe(nrows=10, precision=3)
        columns = self.all_fields_except(['random'])
        self.assertDataFrameCorrect(df, 'dataframe_result.csv',
                                    check_data=columns)


class TestUnstructuredDataExample(ReferenceTestCase):
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


TestStructuredDataExample.set_default_data_location(reference_data_dir)
TestUnstructuredDataExample.set_default_data_location(reference_data_dir)


if __name__ == '__main__':
    ReferenceTestCase.main()

