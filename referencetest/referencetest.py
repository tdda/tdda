# -*- coding: utf-8 -*-

"""
referencetest.py: refererence testing for test-driven data analysis.

Source repository: http://github.com/tdda/tdda

License: MIT

Copyright (c) Stochastic Solutions Limited 2016
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import os
import sys
import tempfile

from tdda.referencetest.checkpandas import PandasComparison
from tdda.referencetest.checkfiles import FilesComparison


# DEFAULT_FAIL_DIR is the default location for writing failing output
# if assertStringCorrect or assertFileCorrect fail with 'preprocessing'
# in place. This can be overridden using the set_defaults() class method.
DEFAULT_FAIL_DIR = os.environ.get('TDDA_FAIL_DIR', tempfile.gettempdir())


class ReferenceTest(object):
    """
    Class for comparing results against saved "known to be correct" reference
    results.

    This is typically useful when software produces either a (text or csv)
    file or a string as output.

    The main features are:

        - If the comparison between a string and a file fails,
          the actual string is written to a file and a diff
          command is suggested for seeing the differences between
          the actual output and the expected output.

        - There is support for ignoring lines within the strings/files
          that contain particular patterns or regular expressions.
          This is typically useful for filtering out things like
          version numbers and timestamps that vary in the output
          from run to run, but which do not indicate a problem.

        - There is support for re-writing the reference output
          with the actual output. This, obviously, should be used
          only after careful checking that the new output is correct,
          either because the previous output was in fact wrong,
          or because the intended behaviour has changed.

    The functionality provided by this class is available through python's
    standard unittest framework, via the referencetestcase module. This
    provides the ReferenceTestCase class, which is a subclass of, and drop-in
    replacement for unittest.TestCase. It extends that class with all of
    the methods from ReferenceTest.

    The functionality is also available through the pytest framework, via
    the referencepytest module. This module provides all of the methods from
    ReferenceTest, as functions that can be called directly as part of a
    pytest suite.
    """

    # Verbose flag
    verbose = True

    # Temporary directory
    tmp_dir = DEFAULT_FAIL_DIR

    # Dictionary describing which kinds of reference files should be
    # regenerated when the tests are run. This should be set using the
    # set_regeneration() class-method. Can be initialized via the -w option.
    regenerate = {}

    # Dictionary describing default location for reference data, for
    # each kind. Can be initialized by set_default_data_location().
    default_data_locations = {}

    @classmethod
    def set_defaults(cls, **kwargs):
        """
        Set default parameters, at the class level. These defaults will
        apply to all instances of ReferenceTest subsequently created.

        The following parameters can be set:

        verbose         Sets the boolean verbose flag globally, to control
                        reporting of errors while running tests. Reference
                        tests tend to take longer to run than traditional
                        unit tests, so it is often useful to be able to see
                        information from failing tests as they happen, rather
                        than waiting for the full report at the end. Verbose
                        is set to True by default.

        print_fn        Sets the print function globally, to specify the
                        function to use to display information while running
                        tests.  The function should have the same signature
                        as python's __future__ print function. If not
                        specified, a default print function is used which
                        writes unbuffered to sys.stdout.

        tmp_dir         Sets the tmp_dir property globally, to specify the
                        directory where temporary files are written. 
                        Temporary files are created whenever a text file
                        check fails and a 'preprocess' function has been
                        specified. It's useful to be able to see the contents
                        of the files after preprocessing has taken place,
                        so preprocessed versions of the files are written
                        to this directory, and their pathnames are included
                        in the failure messages. If not explicitly set by
                        set_defaults(), the environment variable TDDA_FAIL_DIR
                        is used, or, if that is not defined, it defaults to
                        /tmp, c:\temp or whatever tempfile.gettempdir()
                        returns, as appropriate.

        """
        for k in kwargs:
            if k == 'verbose':
                cls.verbose = kwargs[k]
            elif k == 'print_fn':
                cls.print_fn = kwargs[k]
            elif k == 'tmp_dir':
                cls.tmp_dir = kwargs[k]
            else:
                raise Exception('set_defaults: Unrecogized option %s' % k)

    @classmethod
    def set_regeneration(cls, kind=None, regenerate=True):
        """
        Set the regeneration flag for a particular kind of reference file,
        globally, for all instances of the ReferenceTest class.

        If the regenerate flag is set to True, then the framework will
        regenerate reference data of that kind, rather than comparing.

        All of the regenerate flags are set to False by default.
        """
        cls.regenerate[kind] = regenerate

    @classmethod
    def set_default_data_location(self, location, kind=None):
        """
        Declare the default filesystem location for reference files of a
        particular kind. This sets the location globally, and will affect
        all instances of the ReferenceTest class subsequently created.

        The instance method set_data_location() can be used to set
        the per-kind data locations for an individual instance of the class.

        If calls to assertFileCorrect() (etc) are made for kinds of reference
        data that hasn't had its location defined explicitly, then the
        default location is used. This is the location declared for kind=None,
        which *must* be specified.

        If you haven't even defined the None default, and you make calls to
        assertFileCorrect() (etc) using relative pathnames for the reference
        data files, then it can't check correctness, so it will raise an
        exception.
        """
        self.default_data_locations[kind] = location

    def __init__(self, assert_fn):
        """
        Initializer for a ReferenceTest instance.

        assert_fn           Function to be used to make assertions for
                            unit-tests. It should take two parameters:
                                - a value (which should evaluate as true for
                                  the test to pass)
                                - a string (to report details of how a test
                                  failed, if the value does not evaluate as
                                  true).
        """
        self.assert_fn = assert_fn
        self.reference_data_locations = dict(self.default_data_locations)
        self.pandas = PandasComparison(print_fn=self.print_fn,
                                       verbose=self.verbose)
        self.files = FilesComparison(print_fn=self.print_fn,
                                     verbose=self.verbose,
                                     tmp_dir=self.tmp_dir)

    def set_data_location(self, location, kind=None):
        """
        Declare the filesystem location for reference files of a particular
        kind. Typically you would subclass ReferenceTestCase and pass in these
        locations though its __init__ method when constructing an instance
        of ReferenceTestCase as a superclass.

        If calls to assertFileCorrect() (etc) are made for kinds of reference
        data that hasn't had its location defined explicitly, then the
        default location is used. This is the location declared for kind=None,
        which *must* be specified.

        This method overrides any global defaults set from calls to the
        set_default_data_location class-method.

        If you haven't even defined the  None default, and you make calls to
        assertFileCorrect() (etc) using relative pathnames for the reference
        data files, then it can't check correctness, so it will raise an
        exception.
        """
        self.reference_data_locations[kind] = location

    def assertDatasetsEqual(self, df, ref_df,
                            actual_path=None, expected_path=None,
                            check_data=None, check_types=None,
                            check_order=None, condition=None, sortby=None,
                            precision=None):
        """
        Check that an in-memory Pandas dataframe matches an in-memory
        reference one.

        df                Actual dataframe.
        ref_df            Expected dataframe.
        actual_path       Optional parameter, giving path for file where
                          actual dataframe originated, used for error
                          messages.
        expected_path     Optional parameter, giving path for file where
                          expected dataframe originated, used for error
                          messages.
        check_data        Option to specify fields to compare values.
        check_types       Option to specify fields to compare typees.
        check_order       Option to specify fields to compare field order.
        check_extra_cols  Option to specify fields in the actual dataset
                          to use to check that there are no unexpected
                          extra columns.
        sortby            Option to specify fields to sort by before comparing.
        condition         Filter to be applied to datasets before comparing.
                          It can be None, or can be a function that takes
                          a dataframe as its single parameter and returns
                          a vector of booleans (to specify which rows should
                          be compared).
        precision         Number of decimal places to compare float values.

        The check_* comparison flags can be of any of the following:
            - None (to apply that kind of comparison to all fields)
            - False (to skip that kind of comparison completely)
            - a list of field names
            - a function taking a dataframe as its single parameter, and
              returning a list of field names to use.

        Raises NotImplementedError if Pandas is not available.

        """
        r = self.pandas.check_dataframe(df, ref_df,
                                        actual_path=actual_path,
                                        expected_path=expected_path,
                                        check_data=check_data,
                                        check_types=check_types,
                                        check_order=check_order,
                                        condition=condition,
                                        sortby=sortby,
                                        precision=precision)
        (failures, msgs) = r
        self.check_failures(failures, msgs)

    def assertDatasetCorrect(self, df, ref_csv, actual_path=None,
                             kind='csv', csv_read_fn=None,
                             check_data=None, check_types=None,
                             check_order=None, condition=None, sortby=None,
                             precision=None, **kwargs):
        """
        Check that an in-memory  Pandas dataset matches a reference one from
        a saved reference csv file.

        df                Actual dataframe.
        ref_csv           Name of reference csv file. The location of the
                          reference file is determined by the configuration
                          via set_data_location().
        actual_path       Optional parameter, giving path for file where
                          actual dataframe originated, used for error
                          messages.
        kind              Reference kind, used to locate the reference csv
                          file.
        check_data        Option to specify fields to compare values.
        check_types       Option to specify fields to compare typees.
        check_order       Option to specify fields to compare field order.
        check_extra_cols  Option to specify fields in the actual dataset
                          to use to check that there are no unexpected
                          extra columns.
        sortby            Option to specify fields to sort by before comparing.
        condition         Filter to be applied to datasets before comparing.
                          It can be None, or can be a function that takes
                          a dataframe as its single parameter and returns
                          a vector of booleans (to specify which rows should
                          be compared).
        precision         Number of decimal places to compare float values.
        loader            Function to use to read a csv file to obtain
                          a pandas dataframe. If None, then a default csv
                          loader is used.

        The check_* comparison flags can be of any of the following:
            - None (to apply that kind of comparison to all fields)
            - False (to skip that kind of comparison completely)
            - a list of field names
            - a function taking a dataframe as its single parameter, and
              returning a list of field names to use.

        The default csv loader function is a wrapper around pandas
        pd.read_csv(), with default options as follows:
            index_col             is None
            infer_datetime_format is True
            quotechar             is ""
            quoting               is csv.QUOTE_MINIMAL
            escapechar            is \
            na_values             are the empty string, NaN, and NULL
            keep_default_na       is False

        Raises NotImplementedError if Pandas is not available.

        """
        expected_path = self.resolve_reference_path(ref_csv, kind=kind)
        if self.should_regenerate(kind):
            self.write_reference_file(actual_path, expected_path)
        else:
            ref_df = self.pandas.load_csv(expected_path, loader=csv_read_fn)
            self.assertDatasetsEqual(df, ref_df,
                                     actual_path=actual_path,
                                     expected_path=expected_path,
                                     check_data=check_data,
                                     check_types=check_types,
                                     check_order=check_order,
                                     condition=condition,
                                     sortby=sortby,
                                     precision=precision)

    def assertCSVFileCorrect(self, actual_path, ref_csv,
                             kind='csv', csv_read_fn=None,
                             check_data=None, check_types=None,
                             check_order=None, condition=None, sortby=None,
                             precision=None, **kwargs):
        """
        Check that a csv file matches a reference one.

        actual_path       Actual csv file.
        ref_csv           Name of reference csv file. The location of the
                          reference file is determined by the configuration
                          via set_data_location().
        kind              Reference kind, used to locate the reference csv
                          file.
        csv_read_fn       A function to use to read a csv file to obtain
                          a pandas dataframe. If None, then a default csv
                          loader is used, which takes the same parameters
                          as the standard pandas pd.read_csv() function.
        check_data        Option to specify fields to compare values.
        check_types       Option to specify fields to compare typees.
        check_order       Option to specify fields to compare field order.
        check_extra_cols  Option to specify fields in the actual dataset
                          to use to check that there are no unexpected
                          extra columns.
        sortby            Option to specify fields to sort by before comparing.
        condition         Filter to be applied to datasets before comparing.
                          It can be None, or can be a function that takes
                          a dataframe as its single parameter and returns
                          a vector of booleans (to specify which rows should
                          be compared).
        precision         Number of decimal places to compare float values.
        **kwargs          Any additional named parameters are passed straight
                          through to the csv_read_fn function.

        The check_* comparison flags can be of any of the following:
            - None (to apply that kind of comparison to all fields)
            - False (to skip that kind of comparison completely)
            - a list of field names
            - a function taking a dataframe as its single parameter, and
              returning a list of field names to use.

        The default csv loader function is a wrapper around pandas
        pd.read_csv(), with default options as follows:
            index_col             is None
            infer_datetime_format is True
            quotechar             is ""
            quoting               is csv.QUOTE_MINIMAL
            escapechar            is \
            na_values             are the empty string, NaN, and NULL
            keep_default_na       is False

        Raises NotImplementedError if Pandas is not available.

        """
        expected_path = self.resolve_reference_path(ref_csv, kind=kind)
        if self.should_regenerate(kind):
            self.write_reference_file(actual_path, expected_path)
        else:
            r = self.pandas.check_csv_file(actual_path, expected_path,
                                           check_types=check_types,
                                           check_order=check_order,
                                           condition=condition,
                                           sortby=sortby,
                                           precision=precision)
            (failures, msgs) = r
            self.check_failures(failures, msgs)

    def assertCSVFilesCorrect(self, actual_paths, ref_csvs,
                              kind='csv', csv_read_fn=None,
                              check_data=None, check_types=None,
                              check_order=None, condition=None, sortby=None,
                              precision=None, **kwargs):
        """
        Check that a csv file matches a reference one.

        actual_paths      List of Actual csv files.
        ref_csvs          List of names of matching reference csv file. The
                          location of the reference files is determined by
                          the configuration via set_data_location().
        kind              Reference kind, used to locate the reference csv
                          files.
        csv_read_fn       A function to use to read a csv file to obtain
                          a pandas dataframe. If None, then a default csv
                          loader is used, which takes the same parameters
                          as the standard pandas pd.read_csv() function.
        check_data        Option to specify fields to compare values.
        check_types       Option to specify fields to compare typees.
        check_order       Option to specify fields to compare field order.
        check_extra_cols  Option to specify fields in the actual dataset
                          to use to check that there are no unexpected
                          extra columns.
        sortby            Option to specify fields to sort by before comparing.
        condition         Filter to be applied to datasets before comparing.
                          It can be None, or can be a function that takes
                          a dataframe as its single parameter and returns
                          a vector of booleans (to specify which rows should
                          be compared).
        precision         Number of decimal places to compare float values.
        **kwargs          Any additional named parameters are passed straight
                          through to the csv_read_fn function.

        The check_* comparison flags can be of any of the following:
            - None (to apply that kind of comparison to all fields)
            - False (to skip that kind of comparison completely)
            - a list of field names
            - a function taking a dataframe as its single parameter, and
              returning a list of field names to use.

        The default csv loader function is a wrapper around pandas
        pd.read_csv(), with default options as follows:
            index_col             is None
            infer_datetime_format is True
            quotechar             is ""
            quoting               is csv.QUOTE_MINIMAL
            escapechar            is \
            na_values             are the empty string, NaN, and NULL
            keep_default_na       is False

        Raises NotImplementedError if Pandas is not available.

        """
        expected_paths = self.resolve_reference_paths(ref_csvs, kind=kind)
        if self.should_regenerate(kind):
            self.write_reference_files(actual_paths, expected_paths)
        else:
            r = self.pandas.check_csv_files(actual_paths, expected_paths,
                                            check_types=check_types,
                                            check_order=check_order,
                                            condition=condition,
                                            sortby=sortby,
                                            precision=precision)
            (failures, msgs) = r
            self.check_failures(failures, msgs)

    def assertStringCorrect(self, string, ref_csv, kind=None,
                            lstrip=False, rstrip=False,
                            ignore_substrings=None,
                            ignore_patterns=None, preprocess=None,
                            max_permutation_cases=0):
        """
        Check that an in-memory string matches the contents from a reference
        text file.

        string                 is the actual string.
        ref_csv                is the name of the reference csv file. The
                               location of the reference file is determined by
                               the configuration via set_data_location().
        kind                   is the reference kind, used to locate the
                               reference csv file.
        lstrip                 if set to true, both strings are left stripped
                               before the comparison is carried out.
                               Note: the stripping on a per-line basis.
        rstrip                 if set to true, both strings are right stripped
                               before the comparison is carried out.
                               Note: the stripping on a per-line basis.
        ignore_substrings      is an optional list of substrings; lines
                               containing any of these substrings will be
                               ignored in the comparison.
        ignore_patterns        is an optional list of regular expressions;
                               lines will be considered to be the same if
                               they only differ in substrings that match one
                               of these regular expressions. The expressions
                               must not contain parenthesised groups, and
                               should only include explicit anchors if they
                               need refer to the whole line.
        preprocess             is an optional function that takes a list of
                               strings and preprocesses it in some way; this
                               function will be applied to both the actual
                               and expected.
        max_permutation_cases  is an optional number specifying the maximum
                               number of permutations allowed; if the actual
                               and expected lists differ only in that their
                               lines are permutations of each other, and
                               the number of such permutations does not
                               exceed this limit, then the two are considered
                               to be identical.
        """
        expected_path = self.resolve_reference_path(ref_csv, kind=kind)
        if self.should_regenerate(kind):
            self.write_reference_result(string, expected_path)
        else:
            ilc = ignore_substrings
            ip = ignore_patterns
            mpc = max_permutation_cases
            r = self.files.check_string_against_file(string, expected_path,
                                                     actual_path=None,
                                                     lstrip=lstrip,
                                                     rstrip=rstrip,
                                                     ignore_substrings=ilc,
                                                     ignore_patterns=ip,
                                                     preprocess=preprocess,
                                                     max_permutation_cases=mpc)
            (failures, msgs) = r
            self.check_failures(failures, msgs)

    def assertFileCorrect(self, actual_path, ref_path, kind=None,
                          lstrip=False, rstrip=False,
                          ignore_substrings=None,
                          ignore_patterns=None, preprocess=None,
                          max_permutation_cases=0):
        """
        Check that a file matches the contents from a reference text file.

        actual_path            is a path for a text file.
        ref_path               is the name of the reference file. The
                               location of the reference file is determined by
                               the configuration via set_data_location().
        kind                   is the reference kind, used to locate the
                               reference file.
        lstrip                 if set to true, both strings are left stripped
                               before the comparison is carried out.
                               Note: the stripping on a per-line basis.
        rstrip                 if set to true, both strings are right stripped
                               before the comparison is carried out.
                               Note: the stripping on a per-line basis.
        ignore_substrings      is an optional list of substrings; lines
                               containing any of these substrings will be
                               ignored in the comparison.
        ignore_patterns        is an optional list of regular expressions;
                               lines will be considered to be the same if
                               they only differ in substrings that match one
                               of these regular expressions. The expressions
                               must not contain parenthesised groups, and
                               should only include explicit anchors if they
                               need refer to the whole line.
        preprocess             is an optional function that takes a list of
                               strings and preprocesses it in some way; this
                               function will be applied to both the actual
                               and expected.
        max_permutation_cases  is an optional number specifying the maximum
                               number of permutations allowed; if the actual
                               and expected lists differ only in that their
                               lines are permutations of each other, and
                               the number of such permutations does not
                               exceed this limit, then the two are considered
                               to be identical.

        This should be used for unstructured data such as logfiles, etc.
        For csv files, use assertCSVFileCorrect instead.
        """
        expected_path = self.resolve_reference_path(ref_path, kind=kind)
        if self.should_regenerate(kind):
            self.write_reference_file(actual_path, expected_path)
        else:
            mpc = max_permutation_cases
            r = self.files.check_file(actual_path, expected_path,
                                      lstrip=lstrip, rstrip=rstrip,
                                      ignore_substrings=ignore_substrings,
                                      ignore_patterns=ignore_patterns,
                                      preprocess=preprocess,
                                      max_permutation_cases=mpc)
            (failures, msgs) = r
            self.check_failures(failures, msgs)

    def assertFilesCorrect(self, actual_paths, ref_paths, kind=None,
                           lstrip=False, rstrip=False,
                           ignore_substrings=None,
                           ignore_patterns=None, preprocess=None,
                           max_permutation_cases=0):
        """
        Check that a collection of files matche the contents from
        matching collection of reference text files.

        actual_paths           is a list of paths for text files.
        ref_paths              is a list of names of the matching reference
                               files.  The location of the reference files
                               is determined by the configuration via
                               set_data_location().
        kind                   is the reference kind, used to locate the
                               reference files.
        lstrip                 if set to true, both strings are left stripped
                               before the comparison is carried out.
                               Note: the stripping on a per-line basis.
        rstrip                 if set to true, both strings are right stripped
                               before the comparison is carried out.
                               Note: the stripping on a per-line basis.
        ignore_substrings      is an optional list of substrings; lines
                               containing any of these substrings will be
                               ignored in the comparison.
        ignore_patterns        is an optional list of regular expressions;
                               lines will be considered to be the same if
                               they only differ in substrings that match one
                               of these regular expressions. The expressions
                               must not contain parenthesised groups, and
                               should only include explicit anchors if they
                               need refer to the whole line.
        preprocess             is an optional function that takes a list of
                               strings and preprocesses it in some way; this
                               function will be applied to both the actual
                               and expected.
        max_permutation_cases  is an optional number specifying the maximum
                               number of permutations allowed; if the actual
                               and expected lists differ only in that their
                               lines are permutations of each other, and
                               the number of such permutations does not
                               exceed this limit, then the two are considered
                               to be identical.

        This should be used for unstructured data such as logfiles, etc.
        For csv files, use assertCSVFileCorrect instead.
        """
        expected_paths = self.resolve_reference_paths(ref_paths, kind=kind)
        if self.should_regenerate(kind):
            self.write_reference_files(actual_paths, expected_paths)
        else:
            mpc = max_permutation_cases
            r = self.files.check_files(actual_paths, expected_paths,
                                       lstrip=lstrip, rstrip=rstrip,
                                       ignore_substrings=ignore_substrings,
                                       ignore_patterns=ignore_patterns,
                                       preprocess=preprocess,
                                       max_permutation_cases=mpc)
            (failures, msgs) = r
            self.check_failures(failures, msgs)

    def resolve_reference_path(self, path, kind=None):
        """
        Internal method for deciding where a reference data file should
        be looked for, if it has been specified using a relative path.
        """
        if self.reference_data_locations and not os.path.isabs(path):
            if kind not in self.reference_data_locations:
                kind = None
            if kind in self.reference_data_locations:
                path = os.path.join(self.reference_data_locations[kind], path)
            else:
                raise Exception('No reference data location for "%s"' % kind)
        return path

    def resolve_reference_paths(self, paths, kind=None):
        """
        Internal method for resolving a list of reference data files,
        all of the same kind.
        """
        return [self.resolve_reference_path(p, kind=kind) for p in paths]

    def should_regenerate(self, kind):
        """
        Internal method to determine if a particular kind of file
        should be regenerated.
        """
        if kind not in self.regenerate:
            kind = None
        return kind in self.regenerate and self.regenerate[kind]

    def write_reference_file(self, actual_path, reference_path):
        """
        Internal method for regenerating reference data.
        """
        with open(actual_path) as fin:
            actual = fin.read()
        self.write_reference_result(actual, reference_path)

    def write_reference_files(self, actual_paths, reference_paths):
        """
        Internal method for regenerating reference data for a list of
        files.
        """
        for (actual_path, expected_path) in zip(actual_paths, reference_paths):
            self.write_reference_file(actual_path, reference_path)

    def write_reference_result(self, result, reference_path):
        """
        Internal method for regenerating reference data from in-memory
        results.
        """
        with open(reference_path, 'w') as fout:
            fout.write(result)
        if self.verbose and self.print_fn:
            self.print_fn('Written %s' % reference_path)

    def check_failures(self, failures, msgs):
        """
        Internal method for check for failures and reporting them.
        """
        self.assert_fn(failures == 0, '\n'.join(msgs))

    @staticmethod
    def default_print_fn(*args, **kwargs):
        """
        Sometimes the framework needs to print messages. By default, it
        will use this print function, but you can override it by passing
        in a print_fn parameter to __init__.
        """
        print(*args, **kwargs)
        outfile = kwargs.get('file', sys.stdout)
        outfile.flush()

    # Default print function
    print_fn = default_print_fn


# Magic so that an instance of this class can masquerade as a module,
# so that all of its methods can be made available as top-level functions,
# to work will with frameworks like pytest.
ReferenceTest.__all__ = dir(ReferenceTest)

