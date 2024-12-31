# -*- coding: utf-8 -*-
"""
test_using_referencetestcase.py: A simple example of how to use
                                 tdda.referencetest.ReferenceTestCase.

Source repository: http://github.com/tdda/tdda

License: MIT

Copyright (c) Stochastic Solutions Limited 2016-2018
"""

import sys
import os
import tempfile
import unittest

from tdda.referencetest import ReferenceTestCase, tag

# ensure we can import the generators module in the directory above
# (required here only because we want this example source code to be able
# to be copied to other locations, and still work there without needing
# any alterations to PYTHONPATH).
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# directory where reference results are kept
# (in real use, you would probably define this more directly; it is
# done like this here so that the example source code can be copied to
# any location, and still work, without needing any additional configuration).
reference_data_dir = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                                  '..', 'reference')

from generators import generate_string, generate_file

try:
    from dataframes import generate_dataframe
except ImportError:
    generate_dataframe = None


@unittest.skipIf(generate_dataframe is None, 'Pandas tests skipped')
class TestStructuredDataExample(ReferenceTestCase):

    def testExampleDataFrameGeneration(self):
        """
        This test uses generate_dataframe() from dataframes.py to
        generate a simple Pandas DataFrame.

        The test checks the DataFrame is as expected, in terms of both
        data content (the values) and metadata (the types, order, etc)
        of the columns.
        """
        df = generate_dataframe()
        columns = self.all_fields_except(['random'])
        self.assertDataFrameCorrect(df, 'dataframe_result.csv',
                                    check_data=columns, check_types=columns)

    def testExampleCSVGeneration(self):
        """
        This test uses generate_dataframe() from dataframes.py to
        generate a simple Pandas dataframe, and then saves it to a CSV file.

        The test checks the generated CSV file is as expected, in terms of both
        data content (the values) and metadata (the types, order, etc)
        of the columns.
        """
        outpath = os.path.join(self.tmp_dir, 'dataframe_result.csv')
        df = generate_dataframe()
        df.to_csv(outpath, index=False)
        columns = self.all_fields_except(['random'])
        self.assertOnDiskDataFrameCorrect(outpath, 'dataframe_result.csv',
                                          check_data=columns,
                                          check_types=columns)

    def testExampleParquetFileGeneration(self):
        """
        This test uses generate_dataframe() from dataframes.py to
        generate a simple Pandas dataframe, and then saves it to a parquet
        file.

        The test checks the generated parquet file is as expected,
        in terms of both
        data content (the values) and metadata (the types, order, etc)
        of the columns.
        """
        outpath = os.path.join(self.tmp_dir, 'dataframe_result.parquet')
        df = generate_dataframe()
        df.to_parquet(outpath, index=False)
        columns = self.all_fields_except(['random'])
        self.assertOnDiskDataFrameCorrect(outpath, 'dataframe_result.parquet',
                                          check_data=columns,
                                          check_types=columns)

    def testExampleMultipleCSVGeneration(self):
        """
        This test uses generate_dataframe() from dataframes.py to
        generate two simple Pandas dataframe, and then saves each to a CSV
        file.

        The test checks the generated CSV files are as expected, in terms of
        both data content (the values) and metadata (the types, order, etc)
        of the columns.
        """
        df1 = generate_dataframe(nrows=10)
        df2 = generate_dataframe(nrows=20)
        outpath1 = os.path.join(self.tmp_dir, 'dataframe_result1.csv')
        outpath2 = os.path.join(self.tmp_dir, 'dataframe_result2.csv')
        df1.to_csv(outpath1, index=False)
        df2.to_csv(outpath2, index=False)
        columns = self.all_fields_except(['random'])
        self.assertCSVFilesCorrect([outpath1, outpath2],
                                  ['dataframe_result.csv',
                                   'dataframe_result2.csv'],
                                  check_data=columns)

    def testExampleMultipleParquetFileGeneration(self):
        """
        This test uses generate_dataframe() from dataframes.py to
        generate two simple Pandas dataframe, and then saves each to
        a parquet file.

        The test checks the generated parquet files are as expected,
        in terms of both data content (the values) and metadata (the types,
        order, etc) of the columns.
        """
        df1 = generate_dataframe(nrows=10)
        df2 = generate_dataframe(nrows=20)
        outpath1 = os.path.join(self.tmp_dir, 'dataframe_result1.parquet')
        outpath2 = os.path.join(self.tmp_dir, 'dataframe_result2.parquet')
        df1.to_parquet(outpath1, index=False)
        df2.to_parquet(outpath2, index=False)
        columns = self.all_fields_except(['random'])
        self.assertOnDiskDataFramesCorrect([outpath1, outpath2],
                                           ['dataframe_result.parquet',
                                            'dataframe_result2.parquet'],
                                           check_data=columns)


class TestUnstructuredDataExample(ReferenceTestCase):
    """
    Test class for handling unstructured data.
    """

    def testExampleStringGeneration(self):
        """
        This test uses generate_string() from generators.py to generate
        some HTML as a string.

        It is similar to the reference HTML in
            tdda/referencetest/examples/reference/string_result.html
        except that the Copyright and Version lines are slightly different.

        As shipped, the test should pass, because the ignore_substrings
        parameter tell it to ignore any lines in the expected result that
        contain either of those strings.

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
        Copyright and Version lines are slightly different.

        As shipped, the test should pass, because the ignore_substrings
        tell it to ignore differences that match appropriate regular
        expressions for those cases.

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
        self.assertTextFileCorrect(outpath, 'file_result.html',
                                   ignore_patterns=[
            r'Copyright \(c\) Stochastic Solutions, [0-9]{4}',
            r'Version [0-9]{1,2}\.[0-9]{1,2}\.[0-9]{1,2}'
        ])


TestStructuredDataExample.set_default_data_location(reference_data_dir)
TestUnstructuredDataExample.set_default_data_location(reference_data_dir)


if __name__ == '__main__':
    ReferenceTestCase.main()

