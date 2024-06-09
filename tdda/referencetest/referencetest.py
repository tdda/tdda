# -*- coding: utf-8 -*-

__unittest = True


import os
import sys
import tempfile

from tdda.referencetest.checkpandas import PandasComparison
from tdda.referencetest.checkfiles import FilesComparison


# DEFAULT_FAIL_DIR is the default location for writing failing output
# if assertStringCorrect or assertTextFileCorrect fail with 'preprocessing'
# in place. This can be overridden using the set_defaults() class method.
DEFAULT_FAIL_DIR = os.environ.get('TDDA_FAIL_DIR', tempfile.gettempdir())


def tag(test):
    """
    Decorator for tests, so that you can specify you only want to
    run a tagged subset of tests, with the -1 or --tagged option.
    """
    test._tagged = True
    return test


class ReferenceTest(object):
    """
    The :py:class:`~tdda.referencetest.referencetest.ReferenceTest` class
    provides support for comparing results against a set of reference
    "known to be correct" results.

    The functionality provided by this class can be used with:

        - the standard Python :py:mod:`unittest` framework, using the
          :py:class:`~tdda.referencetest.referencetestcase.ReferenceTestCase`
          class. This is a subclass of, and therefore a drop-in replacement
          for, :py:class:`unittest.TestCase`. It extends that class with all
          of the methods from the
          :py:class:`~tdda.referencetest.referencetest.ReferenceTest` class.

        - the :py:mod:`pytest` framework, using the
          :py:mod:`~tdda.referencetest.referencepytest` module.
          This module provides all of the methods from the
          :py:class:`~tdda.referencetest.referencetest.ReferenceTest` class,
          exposed as functions that can be called directly from tests
          in a :py:mod:`pytest` suite.

    In addition to the various test-assertion methods, the module also
    provides some useful instance variables. All of these can be set
    explicitly in test setup code, using the :py:meth:`set_defaults`
    class method.
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
        """Set default parameters, at the class level. These defaults will
        apply to all instances of the class.

        The following parameters can be set:

            *verbose*:
                Sets the boolean verbose flag globally, to control
                reporting of errors while running tests. Reference
                tests tend to take longer to run than traditional
                unit tests, so it is often useful to be able to see
                information from failing tests as they happen, rather
                than waiting for the full report at the end. Verbose
                is set to ``True`` by default.

            *print_fn*: Sets the print function globally, to specify
                the function to use to display information while
                running tests.  The function have the same signature
                as Python3's standard print function, a default
                print function is used which writes unbuffered to
                ``sys.stdout``.

            *tmp_dir*:
                Sets the tmp_dir property globally, to specify the
                directory where temporary files are written.
                Temporary files are created whenever a text file
                check fails and a 'preprocess' function has been
                specified. It's useful to be able to see the contents
                of the files after preprocessing has taken place,
                so preprocessed versions of the files are written
                to this directory, and their pathnames are included
                in the failure messages. If not explicitly set by
                :py:meth:`set_defaults()`, the environment variable
                *TDDA_FAIL_DIR* is used, or, if that is not defined,
                it defaults to */tmp*, *c:\\temp* or whatever
                :py:func:`tempfile.gettempdir()` returns, as
                appropriate.
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
        globally, for all instances of the class.

        If the regenerate flag is set to ``True``, then the framework will
        regenerate reference data of that kind, rather than comparing.

        All of the regeneration flags are set to False by default.
        """
        cls.regenerate[kind] = regenerate

    @classmethod
    def set_default_data_location(cls, location, kind=None):
        """
        Declare the default filesystem location for reference files of a
        particular kind. This sets the location for all instances of the class
        it is called on. Subclasses will inherit this default (unless they
        explicitly override it).

        To set the location globally for all tests in all classes
        within an application, call this method on the
        :py:class:`ReferenceTest` class.

        The instance method :py:meth:`set_data_location()` can be used to set
        the per-kind data locations for an individual instance of a class.

        If calls to :py:meth:`assertTextFileCorrect()` (etc) are made for
        kinds of reference data that hasn't had their location defined
        explicitly, then the
        default location is used. This is the location declared for
        the ``None`` *kind* and this default **must** be specified.

        If you haven't even defined the ``None`` default, and you make calls
        to :py:meth:`assertTextFileCorrect()` (etc) using relative pathnames
        for the reference data files, then it can't check correctness, so it
        will raise an exception.

        """
        clsid = id(cls)
        if clsid not in cls.default_data_locations:
            cls.default_data_locations[clsid] = {}
        cls.default_data_locations[clsid][kind] = os.path.normpath(location)

    @staticmethod
    def _cls_dataloc(cls, d=None):
        """
        Internal function for obtaining the default data location settings
        for the given class, inheriting from all parent classes all the
        way up to the :py:class:`ReferenceTest` class root.
        """
        if d is None:
            d = {}
        for parentcls in cls.__bases__:
            if issubclass(parentcls, ReferenceTest):
                parentcls._cls_dataloc(parentcls, d)
        clsid = id(cls)
        if clsid in cls.default_data_locations:
            d.update(cls.default_data_locations[clsid])
        return d

    def __init__(self, assert_fn):
        """
        Initializer for a ReferenceTest instance.

            *assert_fn*:
                Function to be used to make assertions for
                unit-tests. It should take two parameters:

                    - a value (which should evaluate as ``True`` for
                      the test to pass)
                    - a string (to report details of how a test
                      failed, if the value does not evaluate as ``True``).
        """
        self.assert_fn = assert_fn
        self.reference_data_locations = self._cls_dataloc(self.__class__)
        self.pandas = PandasComparison(
            print_fn=self.call_print_fn, verbose=self.verbose
        )
        self.files = FilesComparison(
            print_fn=self.call_print_fn,
            verbose=self.verbose,
            tmp_dir=self.tmp_dir,
        )

    def all_fields_except(self, exclusions):
        """
        Helper function, for using with *check_data*, *check_types* and
        *check_order* parameters to assertion functions for Pandas DataFrames.
        It returns the names of all of the fields in the DataFrame being
        checked, apart from the ones given.

        *exclusions* is a list of field names.
        """
        return self.pandas.all_fields_except(exclusions)

    def set_data_location(self, location, kind=None):
        """
        Declare the filesystem location for reference files of a
        particular kind. Typically you would subclass
        ``ReferenceTestCase`` and pass in these locations though its
        ``__init__`` method when constructing an instance of
        ReferenceTestCase as a superclass.

        If calls to :py:meth:`assertTextFileCorrect()` (etc) are made for
        kinds of reference data that hasn't had their location defined
        explicitly, then the
        default location is used. This is the location declared for
        the ``None`` *kind* and this default **must** be specified.

        This method overrides any global defaults set from calls to the
        :py:meth:`ReferenceTest.set_default_data_location()` class-method.

        If you haven't even defined the ``None`` default, and you make calls
        to :py:meth:`assertTextFileCorrect()` (etc) using relative pathnames
        for the reference data files, then it can't check correctness, so it
        will raise an exception.

        """
        self.reference_data_locations[kind] = os.path.normpath(location)

    def assertDataFramesEqual(
        self,
        df,
        ref_df,
        actual_path=None,
        expected_path=None,
        check_data=None,
        check_types=None,
        check_order=None,
        condition=None,
        sortby=None,
        precision=None,
        type_matching=None,
    ):
        """Check that an in-memory Pandas `DataFrame` matches an in-memory
        reference one.

            *df*:
                Actual `DataFrame`.

            *ref_df*:
                Expected `DataFrame`.

            *actual_path*:
                (Optional) path for file where
                actual DataFrame originated, used for error messages.

            *expected_path*:
                (Optional) path for file where
                expected DataFrame originated, used for error messages.

            *check_data*:
                (Optional) restriction of fields whose values should
                be compared.
                Possible values are:

                    - ``None`` or ``True`` (to apply the comparison to
                      *all* fields; this is the default).
                    - ``False`` (to skip the comparison completely)
                    - a list of field names (to check only these fields)
                    - a function taking a ``DataFrame`` as its single
                      parameter,
                      and returning a list of field names to check.

            *check_types*:
                (Optional) restriction of fields whose types should be
                compared.
                See *check_data* (above) for possible values.

            *check_order*:
                (Optional) restriction of fields whose (relative)
                order should be compared.
                See *check_data* (above) for possible values.

            *check_extra_cols*:
                (Optional) restriction of extra fields in the actual dataset
                which, if found, will cause the check to fail.
                See *check_data* (above) for possible values.

            *sortby*:
                (Optional) specification of fields to sort by before comparing.

                    - ``None`` or ``False`` (do not sort; this is the default)
                    - ``True`` (to sort on all fields based on their
                      order in the reference datasets; you probably
                      don't want to use this option)
                    - a list of field names (to sort on these fields, in order)
                    - a function taking a ``DataFrame`` (which will be
                      the reference data frame) as its single
                      parameter,
                      and returning a list of field names to sort on.

            *condition*:
                (Optional) filter to be applied to datasets before comparing.
                It can be ``None``, or can be a function that
                takes a `DataFrame` as its single parameter and
                returns a vector of booleans (to specify which rows
                should be compared).

            *precision*:
                (Optional) number of decimal places to use for
                floating-point comparisons.  Default is not to perform
                rounding.

            *type_matching*  'strict', 'medium', 'permissive'

        Raises :py:class:`NotImplementedError` if Pandas is not available.

        """
        r = self.pandas.check_dataframe(
            df,
            ref_df,
            actual_path=actual_path,
            expected_path=expected_path,
            check_data=check_data,
            check_types=check_types,
            check_order=check_order,
            condition=condition,
            sortby=sortby,
            precision=precision,
            type_matching=type_matching,
        )
        (failures, msgs) = r
        self._check_failures(failures, msgs)

    def assertDataFrameCorrect(
        self,
        df,
        ref_path,
        actual_path=None,
        kind='csv',
        csv_read_fn=None,
        check_data=None,
        check_types=None,
        check_order=None,
        condition=None,
        sortby=None,
        precision=None,
        type_matching=None,
        **kwargs,
    ):
        """
        Check that an in-memory Pandas DataFrame matches a reference one
        from a save reference DataFrame on disk (parquet of CSV).

            *df*:
                Actual DataFrame.

            *ref_path*:
                Name of reference file, which can
                be a .parquet file or a CSV file. The location of the
                reference file is determined by the configuration
                via :py:meth:`set_data_location()`.
                **Renamed from csv_path in version 2.2**


            *actual_path*:
                Optional parameter, giving path for file where
                actual DataFrame originated, used for error
                messages.

            *kind*:
                (Optional) reference kind (a string; see above), used to locate
                the reference CSV file.

            *csv_read_fn*:
                (Optional) function to read a CSV file to obtain
                a pandas DataFrame. If ``None``, then a default
                CSV loader is used.

                The default CSV loader function is a wrapper around Pandas
                :py:func:`pd.read_csv()`, with default options as follows:

                    - ``index_col`` is ``None``
                    - ``infer_datetime_format`` is ``True``
                    - ``quotechar`` is ``"``
                    - ``quoting`` is :py:const:`csv.QUOTE_MINIMAL`
                    - ``escapechar`` is ``\\`` (backslash)
                    - ``na_values`` are the empty string, ``"NaN"``,
                      and ``"NULL"``
                    - ``keep_default_na`` is ``False``

        It also accepts the ``check_data``, ``check_types``, ``check_order``,
        ``check_extra_cols``, ``sortby``, ``condition`` and ``precision``
        optional parameters described in :py:meth:`assertDataFramesEqual()`.

        Raises :py:class:`NotImplementedError` if Pandas is not available.

        """
        expected_path = self._resolve_reference_path(ref_path, kind=kind)
        if self._should_regenerate(kind):
            self.pandas._write_reference_dataframe(df, expected_path)
        else:
            ref_df = self.pandas.load_serialized_dataframe(
                expected_path, actual_df=df, loader=csv_read_fn
            )
            self.assertDataFramesEqual(
                df,
                ref_df,
                actual_path=actual_path,
                expected_path=expected_path,
                check_data=check_data,
                check_types=check_types,
                check_order=check_order,
                condition=condition,
                sortby=sortby,
                precision=precision,
                type_matching=type_matching,
            )

    def assertOnDiskDataFrameCorrect(
        self,
        actual_path,
        ref_path,
        kind='parquet',
        csv_read_fn=None,
        check_data=None,
        check_types=None,
        check_order=None,
        condition=None,
        sortby=None,
        precision=None,
        **kwargs,
    ):
        """Check that a DataFrame on disk (as a parquet file,
           or possible a CSV file, reference DataFrame, also on disk.

           Args:

            *actual_path*:
                File containing actual serialized DataFrame

            *ref_path*:
                File containing reference serialized DataFrame.
                The location of the
                reference file is determined by the configuration
                via :py:meth:`set_data_location()`.

            *kind*:
                (Optional) reference kind (a string; see above), used to locate
                the reference file. CSV is used here, and applies, for now,
                to parqet as well as CSV.

            *csv_read_fn*:
                (Optional) function to read a CSV file to obtain
                a pandas DataFrame. If ``None``, then a default
                CSV loader is used if it is a CSV file.

                The default CSV loader function is a wrapper around Pandas
                :py:func:`pd.read_csv()`, with default options as follows:

                    - ``index_col`` is ``None``
                    - ``infer_datetime_format`` is ``True``
                    - ``quotechar`` is ``"``
                    - ``quoting`` is :py:const:`csv.QUOTE_MINIMAL`
                    - ``escapechar`` is ``\\`` (backslash)
                    - ``na_values`` are the empty string, ``"NaN"``,
                       and ``"NULL"``
                    - ``keep_default_na`` is ``False``

            *\*\*kwargs*:
                Any additional named parameters are passed
                straight through to the *csv_read_fn* function.

        It also accepts the ``check_data``, ``check_types``, ``check_order``,
        ``check_extra_cols``, ``sortby``, ``condition`` and ``precision``
        optional parameters described in :py:meth:`assertDataFramesEqual()`.

        Raises :py:class:`NotImplementedError` if Pandas is not available.
        """
        if kind == 'parquet':
            kind = 'csv'  # it's just a key; can be parquet
        expected_path = self._resolve_reference_path(ref_path, kind=kind)
        if self._should_regenerate(kind):
            self.pandas._write_reference_dataframe_from_file(actual_path,
                                                             expected_path)
        else:
            r = self.pandas.check_serialized_dataframe(
                actual_path,
                expected_path,
                check_data=check_data,
                check_types=check_types,
                check_order=check_order,
                condition=condition,
                sortby=sortby,
                precision=precision,
                loader=csv_read_fn,
                **kwargs,
            )
            (failures, msgs) = r
            self._check_failures(failures, msgs)

    def assertCSVFileCorrect(
        self,
        actual_path,
        ref_csv,
        kind='csv',
        csv_read_fn=None,
        check_data=None,
        check_types=None,
        check_order=None,
        condition=None,
        sortby=None,
        precision=None,
        **kwargs,
    ):
        """
        Legacy convenience method with second parameter called ref_csv.
        Just calls assertOnDiskDataFrameCorrect.
        """
        return self.assertOnDiskDataFrameCorrect(
            actual_path,
            ref_csv,
            kind='kind',
            csv_read_fn=csv_read_fn,
            check_data=check_data,
            check_types=check_types,
            check_order=check_order,
            condition=condition,
            sortby=sortby,
            precision=precision,
            **kwargs,
        )

    def assertOnDiskDataFramesCorrect(
        self,
        actual_paths,
        ref_paths,
        kind='csv',
        csv_read_fn=None,
        check_data=None,
        check_types=None,
        check_order=None,
        condition=None,
        sortby=None,
        precision=None,
        **kwargs,
    ):
        """Check that a set of serialized datafames in files
           match corresponding reference ones.

            *actual_paths*:
                List of actual serialized data frames (Parquet or CSV)

            *ref_paths*:
                List of names of matching reference serialized data frames
                (Parquet or CSV). The
                location of the reference files is determined by
                the configuration via :py:meth:`set_data_location()`.

            *kind*:
                (Optional) reference kind (a string; see above), used to locate
                the reference CSV or Paerquet file.

            *csv_read_fn*:
                (Optional) function to read a CSV file to obtain
                a pandas DataFrame. If ``None``, then a default
                CSV loader is used.

                The default CSV loader function is a wrapper around Pandas
                :py:func:`pd.read_csv()`, with default options as follows:

                    - ``index_col`` is ``None``
                    - ``infer_datetime_format`` is ``True``
                    - ``quotechar`` is ``"``
                    - ``quoting`` is :py:const:`csv.QUOTE_MINIMAL`
                    - ``escapechar`` is ``\\`` (backslash)
                    - ``na_values`` are the empty string, ``"NaN"``,
                      and ``"NULL"``
                    - ``keep_default_na`` is ``False``

            *\*\*kwargs*:
                Any additional named parameters are passed straight
                through to the *csv_read_fn* function.

        It also accepts the ``check_data``, ``check_types``, ``check_order``,
        ``check_extra_cols``, ``sortby``, ``condition`` and ``precision``
        optional parameters described in :py:meth:`assertDataFramesEqual()`.

        Raises :py:class:`NotImplementedError` if Pandas is not available.

        """
        if kind == 'parquet':
            kind = 'csv'  # it's just a key; can be parquet

        expected_paths = self._resolve_reference_paths(ref_paths, kind=kind)
        if self._should_regenerate(kind):
            self.pandas._write_reference_dataframes_from_files(actual_paths,
                                                               expected_paths)
        else:
            r = self.pandas.check_serialized_dataframes(
                actual_paths,
                expected_paths,
                check_data=check_data,
                check_types=check_types,
                check_order=check_order,
                condition=condition,
                sortby=sortby,
                precision=precision,
                loader=csv_read_fn,
                **kwargs,
            )
            (failures, msgs) = r
            self._check_failures(failures, msgs)

    def assertCSVFilesCorrect(
        self,
        actual_paths,
        ref_csvs,
        kind='csv',
        csv_read_fn=None,
        check_data=None,
        check_types=None,
        check_order=None,
        condition=None,
        sortby=None,
        precision=None,
        **kwargs,
    ):
        """
        Legacy method that just calls assertOnDiskDataFramesCorrect.
        """
        return self.assertOnDiskDataFramesCorrect(
            actual_paths,
            ref_csvs,
            kind=kind,
            csv_read_fn=csv_read_fn,
            check_data=check_data,
            check_types=check_types,
            check_order=check_order,
            condition=condition,
            sortby=sortby,
            precision=precision,
            **kwargs,
        )

    def assertStringCorrect(
        self,
        string,
        ref_path,
        kind=None,
        lstrip=False,
        rstrip=False,
        ignore_substrings=None,
        ignore_patterns=None,
        remove_lines=None,
        ignore_lines=None,
        preprocess=None,
        max_permutation_cases=0,
    ):
        """
        Check that an in-memory string matches the contents from a reference
        text file.

            *string*:
                The actual string.

            *ref_path*:
                The name of the reference file. The
                location of the reference file is
                determined by the configuration via
                :py:meth:`set_data_location()`.

            *kind*:
                The reference *kind*, used to locate the reference file.

            *lstrip*:
                If set to ``True``, both strings are
                left-stripped before the comparison is carried out.
                Note: the stripping is on a per-line basis.

            *rstrip*:
                If set to ``True``, both strings are
                right-stripped before the comparison is carried out.
                Note: the stripping is on a per-line basis.

            *ignore_substrings*:
                An optional list of substrings; lines
                containing any of these substrings will be
                ignored in the comparison.

            *ignore_patterns*:
                An optional list of regular expressions;
                lines will be considered to be the same if
                they only differ in substrings that match
                one of these regular expressions.
                The expressions should only include explicit anchors if they
                need to refer to the whole line.
                Only the matched expression within the line is ignored; any text
                to the left or right of the matched expression must either be
                **exactly** the same on both sides, or be ignorable.

            *remove_lines*
                An optional list of substrings; lines
                containing any of these substrings will be
                completely removed before carrying out the
                comparison. This is the means by which you
                would exclude 'optional' content.

            *preprocess*:
                An optional function that takes a list of
                strings and preprocesses it in some way; this
                function will be applied to both the actual and expected.

            *max_permutation_cases*:
                An optional number specifying the maximum
                number of permutations allowed; if the actual
                and expected lists differ only in that their
                lines are permutations of each other, and
                the number of such permutations does not
                exceed this limit, then the two are considered to be identical.

        The *ignore_lines* parameter exists for backwards compatibility as
        an alias for *remove_lines*.
        """
        expected_path = self._resolve_reference_path(ref_path, kind=kind)
        if self._should_regenerate(kind):
            self._write_reference_result(
                string, expected_path, lstrip=lstrip, rstrip=rstrip
            )
        else:
            ilc = ignore_substrings
            ip = ignore_patterns
            mpc = max_permutation_cases
            rl = remove_lines or ignore_lines
            r = self.files.check_string_against_file(
                string,
                expected_path,
                actual_path=None,
                lstrip=lstrip,
                rstrip=rstrip,
                ignore_substrings=ilc,
                ignore_patterns=ip,
                remove_lines=rl,
                preprocess=preprocess,
                max_permutation_cases=mpc,
            )
            (failures, msgs) = r
            self._check_failures(failures, msgs)

    def assertTextFileCorrect(
        self,
        actual_path,
        ref_path,
        kind=None,
        lstrip=False,
        rstrip=False,
        ignore_substrings=None,
        ignore_patterns=None,
        remove_lines=None,
        ignore_lines=None,
        preprocess=None,
        max_permutation_cases=0,
        encoding=None,
    ):
        """
        Check that a text file matches the contents from a reference text file.

            *actual_path*:
                A path for a text file.

            *ref_path*:
                The name of the reference file. The
                location of the reference file is determined by
                the configuration via
                :py:meth:`set_data_location()`.

        It also accepts the ``kind``, ``lstrip``, ``rstrip``,
        ``ignore_substrings``, ``ignore_patterns``, ``remove_lines``,
        ``preprocess`` and ``max_permutation_cases``
        optional parameters described in :py:meth:`assertStringCorrect()`.

        This should be used for unstructured data such as logfiles, etc.
        For CSV files, use :py:meth:`assertOnDiskDataFramCorrect` instead.

        The *ignore_lines* parameter exists for backwards compatibility as
        an alias for *remove_lines*.

        The :py:meth:`assertFileCorrect()` method can be used as an alias for
        :py:meth:`assertTextFileCorrect()`, retained for backwards
        compatibility.
        """
        expected_path = self._resolve_reference_path(ref_path, kind=kind)
        if self._should_regenerate(kind):
            self._write_reference_file(
                actual_path, expected_path, lstrip=lstrip, rstrip=rstrip
            )
        else:
            mpc = max_permutation_cases
            rl = remove_lines or ignore_lines
            r = self.files.check_file(
                actual_path,
                expected_path,
                lstrip=lstrip,
                rstrip=rstrip,
                ignore_substrings=ignore_substrings,
                ignore_patterns=ignore_patterns,
                remove_lines=rl,
                preprocess=preprocess,
                max_permutation_cases=mpc,
                encoding=encoding,
            )
            (failures, msgs) = r
            self._check_failures(failures, msgs)

    def assertTextFilesCorrect(
        self,
        actual_paths,
        ref_paths,
        kind=None,
        lstrip=False,
        rstrip=False,
        ignore_substrings=None,
        ignore_patterns=None,
        remove_lines=None,
        ignore_lines=None,
        preprocess=None,
        max_permutation_cases=0,
        encodings=None,
    ):
        """
        Check that a collection of text files matche the contents from
        matching collection of reference text files.

            *actual_paths*:
                A list of paths for text files.

            *ref_paths*:
                A list of names of the matching reference
                files.  The location of the reference files
                is determined by the configuration via
                :py:meth:`set_data_location()`.

        This should be used for unstructured data such as logfiles, etc.
        For CSV files, use :py:meth:`assertOnDiskDataFramesCorrect` instead.

        It also accepts the ``kind``, ``lstrip``, ``rstrip``,
        ``ignore_substrings``, ``ignore_patterns``, ``remove_lines``,
        ``preprocess`` and ``max_permutation_cases``
        optional parameters described in :py:meth:`assertStringCorrect()`.

        The :py:meth:`assertFilesCorrect()` metohd can be used as an alias for
        :py:meth:`assertTextFilesCorrect()`, retained for backwards
        compatibility.
        """
        expected_paths = self._resolve_reference_paths(ref_paths, kind=kind)
        if self._should_regenerate(kind):
            self._write_reference_files(
                actual_paths, expected_paths, lstrip=strip, rstrip=rstrip
            )
        else:
            mpc = max_permutation_cases
            rl = remove_lines or ignore_lines
            r = self.files.check_files(
                actual_paths,
                expected_paths,
                lstrip=lstrip,
                rstrip=rstrip,
                ignore_substrings=ignore_substrings,
                ignore_patterns=ignore_patterns,
                remove_lines=rl,
                preprocess=preprocess,
                max_permutation_cases=mpc,
                encodings=encodings,
            )
            (failures, msgs) = r
            self._check_failures(failures, msgs)

    # DEPRECATED
    assertFileCorrect = assertTextFileCorrect
    assertFilesCorrect = assertTextFilesCorrect

    def assertBinaryFileCorrect(self, actual_path, ref_path, kind=None):
        """
        Check that a binary file matches the contents from a reference
        binary file.

            *actual_path*:
                A path for a binary file.

            *ref_path*:
                The name of the reference binary file. The
                location of the reference file is determined by
                the configuration via
                :py:meth:`set_data_location()`.

            *kind*:
                The reference *kind*, used to locate the reference file.
        """
        expected_path = self._resolve_reference_path(ref_path, kind=kind)
        if self._should_regenerate(kind):
            self._write_reference_file(actual_path, expected_path, binary=True)
        else:
            r = self.files.check_binary_file(actual_path, expected_path)
            (failures, msgs) = r
            self._check_failures(failures, msgs)

    def _resolve_reference_path(self, path, kind=None):
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

    def _resolve_reference_paths(self, paths, kind=None):
        """
        Internal method for resolving a list of reference data files,
        all of the same kind.
        """
        return [self._resolve_reference_path(p, kind=kind) for p in paths]

    def _should_regenerate(self, kind):
        """
        Internal method to determine if a particular kind of file
        should be regenerated.
        """
        if kind not in self.regenerate:
            kind = None
        return kind in self.regenerate and self.regenerate[kind]

    def _write_reference_file(
        self,
        actual_path,
        reference_path,
        binary=False,
        lstrip=False,
        rstrip=False,
    ):
        """
        Internal method for regenerating reference data.
        """
        mode = 'rb' if binary else 'r'
        with open(actual_path, mode) as fin:
            actual = fin.read()
        self._write_reference_result(actual, reference_path, binary=binary)

    def _write_reference_files(
        self, actual_paths, reference_paths, lstrip=False, rstrip=False
    ):
        """
        Internal method for regenerating reference data for a list of
        files.
        """
        for actual_path, expected_path in zip(actual_paths, reference_paths):
            self._write_reference_file(
                actual_path, expected_path, lstrip=lstrip, rstrip=rstrip
            )

    def _write_reference_dataset(self, df, reference_path):
        """
        Internal method for regenerating reference data for a Pandas dataset
        """
        self.pandas._write_reference_dataframe(df, reference_path)

    def _write_reference_result(
        self, result, reference_path, binary=False, lstrip=False, rstrip=False
    ):
        """
        Internal method for regenerating reference data from in-memory
        results.
        """
        mode = 'wb' if binary else 'w'
        with open(reference_path, mode) as fout:
            fout.write(result)
        if self.verbose and self.print_fn:
            self.print_fn('Written %s' % reference_path)

    def _check_failures(self, failures, msgs):
        """
        Internal method for check for failures and reporting them.
        """
        self.assert_fn(failures == 0, msgs.message())

    def call_print_fn(self, *args, **kwargs):
        fn = self.print_fn or self._default_print_fn
        fn(*args, **kwargs)

    @staticmethod
    def _default_print_fn(*args, **kwargs):
        # Sometimes the framework needs to print messages. By default, it
        # will use this print function, but you can override it by passing
        # in a print_fn parameter to __init__.
        print(*args, **kwargs)
        outfile = kwargs.get('file', sys.stdout)
        outfile.flush()

    # Default print function
    print_fn = _default_print_fn


# Magic so that an instance of this class can masquerade as a module,
# so that all of its methods can be made available as top-level functions,
# to work will with frameworks like pytest.
ReferenceTest.__all__ = dir(ReferenceTest)
