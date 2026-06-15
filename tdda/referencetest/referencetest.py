__unittest = True


import json
import os
import re
import sys
import tempfile

from tdda.referencetest.basecomparison import diffcmd
from tdda.referencetest.utils import (
    apply_preprocess,
    normalize_json,
    normalize_json_for_comparison,
    norm_paths_in_json,
    remove_dict_keys,
    to_posix_newlines,
)
from tdda.referencetest.checkpandas import PandasComparison
from tdda.referencetest.checkpolars import PolarsComparison
from tdda.referencetest.checkfiles import FilesComparison
from tdda.state import get_config
from tdda.utils import TDDAError, nvl, error
from tdda.abstractdf import (
    all_fields_except,
    df_type,
    df_definite,
    is_pandas_df,
    is_polars_df,
)


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


def windows_paths_to_posix(lines):
    """Normalise Windows-style paths to POSIX paths in a list of lines.

    Replaces drive-letter prefixes (e.g. ``C:\\``) with ``/`` and
    remaining backslashes with ``/``.

    Args:
        lines (list): Lines of text to normalise.

    Returns:
        list: Lines with Windows path separators replaced by ``/``.
    """
    normed = []
    for line in lines:
        line = re.sub(r'[A-Za-z]:\\', '/', line)
        line = line.replace('\\', '/')
        normed.append(line)
    return normed



class ReferenceTest(object):
    """Provides support for comparing results against reference
    “known to be correct” results.

    Can be used with:

    - the standard Python ``unittest`` framework, via the
      ``ReferenceTestCase`` class, which is a drop-in replacement for
      ``unittest.TestCase`` extended with all ``ReferenceTest`` methods.
    - the ``pytest`` framework, via the ``referencepytest`` module, which
      exposes all ``ReferenceTest`` methods as functions callable directly
      from pytest tests.

    In addition to the assertion methods, the class provides useful instance
    variables that can be set via the ``set_defaults`` class method.
    """

    # Verbose flag
    verbose = True

    # Temporary directory
    tmp_dir = DEFAULT_FAIL_DIR

    # If set to True on a subclass, all text assertions will normalise
    # Windows-style paths to POSIX paths before comparison (only active
    # on Windows).
    norm_paths = False

    # Platform-appropriate diff command prefixes for use with ignore_lines.
    # Includes 'fc ' on Windows in addition to 'diff '.
    _diffcmd = diffcmd()
    _diff_cmds = ['diff '] + ([] if _diffcmd == 'diff' else [f'{_diffcmd} '])

    # Dictionary describing which kinds of reference files should be
    # regenerated when the tests are run. This should be set using the
    # set_regeneration() class-method. Can be initialized via the -w option.
    regenerate = {}

    # Dictionary describing default location for reference data, for
    # each kind. Can be initialized by set_default_data_location().
    default_data_locations = {}

    @classmethod
    def set_defaults(cls, **kwargs):
        """Set default parameters at the class level, applying to all
        instances.

        Args:
            **kwargs: Keyword arguments. Supported keys are:

                - ``verbose``: Boolean flag controlling reporting of errors
                  while running tests. Reference tests tend to take longer
                  than traditional unit tests, so seeing failures as they
                  happen is often useful. Default is ``True``.
                - ``print_fn``: Function to use to display information
                  while running tests. Must have the same signature as
                  Python's built-in ``print``. Defaults to unbuffered
                  output to ``sys.stdout``.
                - ``tmp_dir``: Directory where temporary files are written.
                  Temporary files are created when a text file check fails
                  and a ``preprocess`` function has been specified, so the
                  preprocessed versions can be inspected. If not set, the
                  ``TDDA_FAIL_DIR`` environment variable is used, or
                  ``tempfile.gettempdir()`` as a fallback.
                - ``norm_paths``: If ``True``, normalise Windows-style paths
                  to POSIX paths in all text assertions (only active on
                  Windows). Default is ``False``.
        """
        for k in kwargs:
            if k == 'verbose':
                cls.verbose = kwargs[k]
            elif k == 'print_fn':
                cls.print_fn = kwargs[k]
            elif k == 'tmp_dir':
                cls.tmp_dir = kwargs[k]
            elif k == 'norm_paths':
                cls.norm_paths = kwargs[k]
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
        """Declare the default filesystem location for reference files of a
        particular kind, applying to all instances of the class.

        Subclasses inherit this default unless they explicitly override it.
        To set the location globally for all test classes in an application,
        call this on the ``ReferenceTest`` class directly.

        Use the instance method ``set_data_location()`` to set per-kind
        locations for an individual instance.

        If an assertion is made for a kind whose location has not been
        defined explicitly, the default location (declared for kind
        ``None``) is used. This default **must** be specified. If it is
        not set and relative pathnames are used, an exception is raised.

        Args:
            location: Filesystem path to the directory containing
                reference files of this kind.
            kind: The reference kind this location applies to.
                ``None`` sets the default location used when no
                specific kind is matched.
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
        """Initializer for a ReferenceTest instance.

        Args:
            assert_fn: Function used to make assertions. Should take two
                parameters: a value (which should evaluate as ``True`` for
                the test to pass) and a string (to report details of how
                the test failed).
        """
        self.assert_fn = assert_fn
        self.reference_data_locations = self._cls_dataloc(self.__class__)
        self.pandas = PandasComparison(
            print_fn=self.call_print_fn, verbose=self.verbose
        )
        self.polars = PolarsComparison(
            print_fn=self.call_print_fn, verbose=self.verbose
        )
        self.files = FilesComparison(
            print_fn=self.call_print_fn,
            verbose=self.verbose,
            tmp_dir=self.tmp_dir,
        )

    def all_fields_except(self, exclusions):
        """Return all field names in the DataFrame except those specified.

        Helper for use with the ``check_data``, ``check_types`` and
        ``check_order`` parameters of the DataFrame assertion methods.

        Args:
            exclusions: A list of field names to exclude.
        """
        return all_fields_except(exclusions)

    def set_data_location(self, location, kind=None):
        """Declare the filesystem location for reference files of a
        particular kind for this instance.

        Overrides any global defaults set via
        ``ReferenceTest.set_default_data_location()``.

        If an assertion is made for a kind whose location has not been
        defined explicitly, the default location (declared for kind
        ``None``) is used. This default **must** be specified. If it is
        not set and relative pathnames are used, an exception is raised.

        Args:
            location: Filesystem path to the directory containing
                reference files of this kind.
            kind: The reference kind this location applies to.
                ``None`` sets the default location used when no
                specific kind is matched.
        """
        self.reference_data_locations[kind] = os.path.normpath(location)

    def assertDataFramesEquivalent(
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
        fuzzy_nulls=False,
        engine=None,
        backend=None,
        preprocess=None,
    ):
        """Check that an in-memory DataFrame matches an in-memory reference one.

        Both ``df`` and ``ref_df`` may be Pandas or Polars DataFrames. If they
        are of different types, both are converted to the engine specified by
        the ``engine`` parameter, or to the default engine from configuration
        if ``engine`` is not supplied.

        Args:
            df: Actual DataFrame (Pandas or Polars).
            ref_df: Expected DataFrame (Pandas or Polars).
            actual_path: Optional path for the file where the actual
                DataFrame originated, used for error messages.
            expected_path: Optional path for the file where the expected
                DataFrame originated, used for error messages.
            check_data: Optional restriction of fields whose values should
                be compared. Possible values are:

                - ``None`` or ``True`` to apply the comparison to all
                  fields (this is the default).
                - ``False`` to skip the comparison completely.
                - a list of field names to check only those fields.
                - a function taking a DataFrame as its single parameter
                  and returning a list of field names to check.

            check_types: Optional restriction of fields whose types should
                be compared. See ``check_data`` for possible values.
            check_order: Optional restriction of fields whose (relative)
                order should be compared. See ``check_data`` for possible
                values.
            check_extra_cols: Optional restriction of extra fields in the
                actual dataset which, if found, will cause the check to
                fail. See ``check_data`` for possible values.
            sortby: Optional specification of fields to sort by before
                comparing. Possible values are:

                - ``None`` or ``False`` to not sort (this is the default).
                - ``True`` to sort on all fields based on their order in
                  the reference dataset (rarely useful).
                - a list of field names to sort on, in order.
                - a function taking the reference DataFrame as its single
                  parameter and returning a list of field names to sort on.

            condition: Optional filter to apply to datasets before
                comparing. Can be ``None``, or a function that takes a
                DataFrame as its single parameter and returns a vector of
                booleans specifying which rows to compare.
            precision: Optional number of decimal places to use for
                floating-point comparisons. Default is 7.
            type_matching: How to match field types: ``'strict'``,
                ``'medium'``, or ``'loose'`` (also ``'permissive'``).
                Default is ``'strict'``.
            engine: DataFrame engine to use for comparison: ``'pandas'`` or
                ``'polars'``. Required when ``df`` and ``ref_df`` are of
                different types; otherwise inferred from the DataFrames.
            fuzzy_nulls: If ``True``, treat different null types (such as
                ``pd.NaN`` and ``None``) as equivalent when comparing.
                Default is ``False``.
            backend: Pandas backend: ``'numpy_nullable'``, ``'pyarrow'``,
                or ``'original'``.

            preprocess: An optional function (or list of functions) applied
                to both DataFrames before comparison. If a list `[f, g]`
                is given, `g(f(·))` is computed, where `·` is the DataFrame.

        Note:
            ``assertDataFramesEqual`` and ``assertDataFramesEquivalent``
            are identical; two names are provided for flexibility and as
            legacy support.
        """
        df = apply_preprocess(df, preprocess)
        ref_df = apply_preprocess(ref_df, preprocess)
        df, ref_df, lib = self.choose_common_df_lib(df, ref_df, engine)
        r = lib.check_dataframe(
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
            fuzzy_nulls=fuzzy_nulls,
            engine=engine,
            backend=backend,
        )
        (failures, msgs) = r
        self._check_failures(failures, msgs)

    assertDataFramesEqual = assertDataFramesEquivalent

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
        fuzzy_nulls=False,
        engine=None,
        backend=None,
        preprocess=None,
        **kwargs,
    ):
        """Check that an in-memory DataFrame matches a saved reference
        DataFrame on disk (parquet or CSV).

        The actual DataFrame may be Pandas or Polars; the engine is inferred
        from it unless overridden by the ``engine`` parameter.

        Args:
            df: Actual DataFrame (Pandas or Polars).
            ref_path: Name of the reference file, which can be a .parquet
                file or a CSV file. The location of the reference file is
                determined by the configuration via ``set_data_location()``.
                Renamed from ``csv_path`` in version 2.2.
            actual_path: Optional path for the file where the actual
                DataFrame originated, used for error messages.
            kind: Optional reference kind (a string), used to locate the
                reference file.
            csv_read_fn: Optional function to read a CSV file to obtain a
                DataFrame. If ``None``, a default CSV loader is used.

                The default CSV loader is a wrapper around
                ``pd.read_csv()`` with the following options:

                - ``index_col`` is ``None``
                - ``infer_datetime_format`` is ``True``
                - ``quotechar`` is ``"``
                - ``quoting`` is ``csv.QUOTE_MINIMAL``
                - ``escapechar`` is ``\\`` (backslash)
                - ``na_values`` are the empty string, ``"NaN"`` and
                  ``"NULL"``
                - ``keep_default_na`` is ``False``

            check_data: See ``assertDataFramesEquivalent`` for details.
            check_types: See ``assertDataFramesEquivalent`` for details.
            check_order: See ``assertDataFramesEquivalent`` for details.
            check_extra_cols: See ``assertDataFramesEquivalent`` for
                details.
            sortby: See ``assertDataFramesEquivalent`` for details.
            condition: See ``assertDataFramesEquivalent`` for details.
            precision: See ``assertDataFramesEquivalent`` for details.
            type_matching: See ``assertDataFramesEquivalent`` for details.
            fuzzy_nulls: See ``assertDataFramesEquivalent`` for details.
            engine: See ``assertDataFramesEquivalent`` for details.
            backend: See ``assertDataFramesEquivalent`` for details.
            preprocess: See ``assertDataFramesEquivalent`` for details.
            **kwargs: Additional keyword arguments passed to ``csv_read_fn``.
        """
        expected_path = self._resolve_reference_path(ref_path, kind=kind)
        lib = self.get_comparison_lib(df=df, engine=engine)
        if self._should_regenerate(kind):
            lib._write_reference_dataframe(df, expected_path)
        else:
            ref_df = lib.load_serialized_dataframe(
                expected_path,
                actual_df=df,
                loader=csv_read_fn,
                backend=backend,
            )
            if type_matching is None and not str(expected_path).lower().endswith(
                '.parquet'
            ):
                type_matching = 'medium'
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
                fuzzy_nulls=fuzzy_nulls,
                engine=engine,
                backend=backend,
                preprocess=preprocess,
            )

    def assertStoredDataFrameCorrect(
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
        type_matching=None,
        fuzzy_nulls=False,
        preprocess=None,
        engine=None,
        **kwargs,
    ):
        """Check that a DataFrame stored on disk (as a parquet or CSV file)
        matches a reference DataFrame, also stored on disk.

        Args:
            actual_path: Path to the actual serialized DataFrame.
            ref_path: Path to the reference serialized DataFrame. The
                location of the reference file is determined by the
                configuration via ``set_data_location()``.
            kind: Optional reference kind (a string), used to locate the
                reference file.
            csv_read_fn: Optional function to read a CSV file to obtain a
                DataFrame. If ``None``, a default CSV loader is used.

                The default CSV loader is a wrapper around
                ``pd.read_csv()`` with the following options:

                - ``index_col`` is ``None``
                - ``infer_datetime_format`` is ``True``
                - ``quotechar`` is ``"``
                - ``quoting`` is ``csv.QUOTE_MINIMAL``
                - ``escapechar`` is ``\\`` (backslash)
                - ``na_values`` are the empty string, ``"NaN"`` and
                  ``"NULL"``
                - ``keep_default_na`` is ``False``

            check_data: See ``assertDataFramesEquivalent`` for details.
            check_types: See ``assertDataFramesEquivalent`` for details.
            check_order: See ``assertDataFramesEquivalent`` for details.
            check_extra_cols: See ``assertDataFramesEquivalent`` for
                details.
            sortby: See ``assertDataFramesEquivalent`` for details.
            condition: See ``assertDataFramesEquivalent`` for details.
            precision: See ``assertDataFramesEquivalent`` for details.
            type_matching: See ``assertDataFramesEquivalent`` for details.
            fuzzy_nulls: See ``assertDataFramesEquivalent`` for details.
            preprocess: See ``assertDataFramesEquivalent`` for details.
            engine: See ``assertDataFramesEquivalent`` for details.
            **kwargs: Additional keyword arguments passed to
                ``csv_read_fn``.

        Note:
            ``assertOnDiskDataFrameCorrect`` is a legacy alias for
            ``assertStoredDataFrameCorrect``.

        Note:
            If the format is CSV, the CSV file is loaded as a DataFrame
            using the default engine, or whichever is supplied (pandas
            or polars), with tdda.serial.csv_to_polars
            or tdda.serial.csv_to_pandas.
        """
        if kind == 'parquet':
            kind = 'csv'  # it's just a key; can be parquet
        expected_path = self._resolve_reference_path(ref_path, kind=kind)
        lib = self.get_comparison_lib(engine=engine)
        if self._should_regenerate(kind):
            lib._write_reference_dataframe_from_file(
                actual_path, expected_path
            )
        else:
            if type_matching is None and not str(expected_path).lower().endswith(
                '.parquet'
            ):
                type_matching = 'medium'
            r = lib.check_serialized_dataframe(
                actual_path,
                expected_path,
                check_data=check_data,
                check_types=check_types,
                check_order=check_order,
                condition=condition,
                sortby=sortby,
                precision=precision,
                type_matching=type_matching,
                fuzzy_nulls=fuzzy_nulls,
                preprocess=preprocess,
                loader=csv_read_fn,
                **kwargs,
            )
            (failures, msgs) = r
            self._check_failures(failures, msgs)

    assertOnDiskDataFrameCorrect = assertStoredDataFrameCorrect

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
        type_matching=None,
        fuzzy_nulls=False,
        preprocess=None,
        engine=None,
        **kwargs,
    ):
        """Legacy convenience method with second parameter called ref_csv.
        Just calls ``assertStoredDataFrameCorrect``.
        """
        return self.assertStoredDataFrameCorrect(
            actual_path,
            ref_csv,
            kind=kind,
            csv_read_fn=csv_read_fn,
            check_data=check_data,
            check_types=check_types,
            check_order=check_order,
            condition=condition,
            sortby=sortby,
            precision=precision,
            type_matching=type_matching,
            fuzzy_nulls=fuzzy_nulls,
            preprocess=preprocess,
            engine=engine,
            **kwargs,
        )

    def assertStoredDataFramesCorrect(
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
        type_matching=None,
        fuzzy_nulls=False,
        preprocess=None,
        engine=None,
        **kwargs,
    ):
        """Check that a set of serialized DataFrames in files match
        corresponding reference ones.

        Args:
            actual_paths: List of paths to actual serialized DataFrames
                (parquet or CSV).
            ref_paths: List of paths to matching reference serialized
                DataFrames (parquet or CSV). The location of the reference
                files is determined by the configuration via
                ``set_data_location()``.
            kind: Optional reference kind (a string), used to locate the
                reference files.
            csv_read_fn: Optional function to read a CSV file to obtain a
                DataFrame. If ``None``, a default CSV loader is used.

                The default CSV loader is a wrapper around
                ``pd.read_csv()`` with the following options:

                - ``index_col`` is ``None``
                - ``infer_datetime_format`` is ``True``
                - ``quotechar`` is ``"``
                - ``quoting`` is ``csv.QUOTE_MINIMAL``
                - ``escapechar`` is ``\\`` (backslash)
                - ``na_values`` are the empty string, ``"NaN"`` and
                  ``"NULL"``
                - ``keep_default_na`` is ``False``

            check_data: See ``assertDataFramesEquivalent`` for details.
            check_types: See ``assertDataFramesEquivalent`` for details.
            check_order: See ``assertDataFramesEquivalent`` for details.
            check_extra_cols: See ``assertDataFramesEquivalent`` for
                details.
            sortby: See ``assertDataFramesEquivalent`` for details.
            condition: See ``assertDataFramesEquivalent`` for details.
            precision: See ``assertDataFramesEquivalent`` for details.
            type_matching: See ``assertDataFramesEquivalent`` for details.
            fuzzy_nulls: See ``assertDataFramesEquivalent`` for details.
            preprocess: See ``assertDataFramesEquivalent`` for details.
            engine: See ``assertDataFramesEquivalent`` for details.
            **kwargs: Additional keyword arguments passed to
                ``csv_read_fn``.

        Note:
            ``assertOnDiskDataFramesCorrect`` is a legacy alias for
            ``assertStoredDataFramesCorrect``.

        Note:
            If the format is CSV, the CSV file is loaded as a DataFrame
            using the default engine, or whichever is supplied (pandas
            or polars), with tdda.serial.csv_to_polars
            or tdda.serial.csv_to_pandas.
        """
        if kind == 'parquet':
            kind = 'csv'  # it's just a key; can be parquet

        expected_paths = self._resolve_reference_paths(ref_paths, kind=kind)
        lib = self.get_comparison_lib(engine=engine)
        if self._should_regenerate(kind):
            lib._write_reference_dataframes_from_files(
                actual_paths, expected_paths
            )
        else:
            r = lib.check_serialized_dataframes(
                actual_paths,
                expected_paths,
                check_data=check_data,
                check_types=check_types,
                check_order=check_order,
                condition=condition,
                sortby=sortby,
                precision=precision,
                type_matching=type_matching,
                loader=csv_read_fn,
                fuzzy_nulls=fuzzy_nulls,
                preprocess=preprocess,
                **kwargs,
            )
            (failures, msgs) = r
            self._check_failures(failures, msgs)

    assertOnDiskDataFramesCorrect = assertStoredDataFramesCorrect

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
        type_matching=None,
        fuzzy_nulls=False,
        preprocess=None,
        engine=None,
        **kwargs,
    ):
        """Legacy method that just calls ``assertStoredDataFramesCorrect``."""
        return self.assertStoredDataFramesCorrect(
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
            type_matching=type_matching,
            fuzzy_nulls=fuzzy_nulls,
            preprocess=preprocess,
            engine=engine,
            **kwargs,
        )

    def assertStringsEquivalent(
        self,
        string,
        expected,
        lstrip=False,
        rstrip=False,
        ignore_substrings=None,
        ignore_patterns=None,
        remove_lines=None,
        ignore_lines=None,
        preprocess=None,
        norm_paths=None,
        max_permutation_cases=0,
        norm_line_endings=True,
    ):
        """Check that two in-memory strings are equivalent.

        Like `assertStringCorrect` but compares two in-memory strings
        rather than comparing against a reference file. The strings are
        considered equivalent if they match after applying any
        normalizations specified via the kwargs.

        On failure, both strings are written to temporary files and a
        diff command is suggested.

        Args:
            string: The actual string.
            expected: The expected string.
            lstrip: See `assertStringCorrect` for details.
            rstrip: See `assertStringCorrect` for details.
            ignore_substrings: See `assertStringCorrect` for details.
            ignore_patterns: See `assertStringCorrect` for details.
            remove_lines: See `assertStringCorrect` for details.
            preprocess: See `assertStringCorrect` for details.
            norm_paths: See `assertStringCorrect` for details.
            max_permutation_cases: See `assertStringCorrect` for details.

        Note:
            The `ignore_lines` parameter is a backwards-compatible alias
            for `remove_lines`.
        """
        preprocess = self._resolve_preprocess(preprocess, norm_paths)
        rl = remove_lines or ignore_lines
        if norm_line_endings and isinstance(string, str):
            string = to_posix_newlines(string)
        if norm_line_endings and isinstance(expected, str):
            expected = to_posix_newlines(expected)
        actual = string.splitlines() if isinstance(string, str) else string
        exp = expected.splitlines() if isinstance(expected, str) else expected
        r = self.files.check_strings(
            actual,
            exp,
            actual_path=None,
            expected_path=None,
            lstrip=lstrip,
            rstrip=rstrip,
            ignore_substrings=ignore_substrings,
            ignore_patterns=ignore_patterns,
            remove_lines=rl,
            preprocess=preprocess,
            max_permutation_cases=max_permutation_cases,
            norm_line_endings=norm_line_endings,
        )
        (failures, msgs) = r
        self._check_failures(failures, msgs)

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
        norm_paths=None,
        max_permutation_cases=0,
        norm_line_endings=True,
    ):
        """Check that an in-memory string matches the contents from a
        reference text file.

        Args:
            string: The actual string.
            ref_path: The name of the reference file. The location of the
                reference file is determined by the configuration via
                `set_data_location()`.
            kind: The reference kind, used to locate the reference file.
            lstrip: If `True`, whitespace is stripped from the start of
                each line before comparison.
            rstrip: If `True`, whitespace is stripped from the end of
                each line before comparison.
            ignore_substrings: An optional list of substrings; lines
                containing any of these substrings will be ignored in the
                comparison.
            ignore_patterns: An optional list of regular expressions; lines
                will be considered the same if they differ only in
                substrings that match one of these expressions. Expressions
                should only include explicit anchors if they need to refer
                to the whole line. Only the matched portion is ignored; any
                text to the left or right must be identical in both strings.
            remove_lines: An optional list of substrings; lines containing
                any of these substrings will be removed before comparison.
            preprocess: An optional function (or list of functions) that
                takes a list of strings and preprocesses it; applied to both
                the actual and expected strings before comparison.
                If a list `[f, g]` is given, `g(f(·))` is computed, where
                `·` is the list of strings.
            norm_paths: If `True`, normalise Windows-style paths to
                POSIX paths before comparison (only active on Windows).
                Applied after `preprocess` if both are specified.
            max_permutation_cases: An optional number specifying the
                maximum number of permutations to allow; if the actual and
                expected lists differ only in line order, and the number of
                such permutations does not exceed this limit, the two are
                considered identical.

        Note:
            The `ignore_lines` parameter is a backwards-compatible alias
            for `remove_lines`.
        """
        preprocess = self._resolve_preprocess(preprocess, norm_paths)
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
                norm_line_endings=norm_line_endings,
            )
            (failures, msgs) = r
            self._check_failures(failures, msgs)

    def assertJSONCorrect(
        self,
        json_data,
        ref_path,
        kind=None,
        remove_keys=None,
        norm_paths=None,
        preprocess=None,
    ):
        """Check that a JSON string matches the contents of a reference file.

        The JSON is normalized before comparison: keys are sorted, indentation
        is standardized to 2 spaces, and Unicode characters are preserved
        (not ASCII-escaped). This means key ordering and whitespace differences
        are ignored; only semantic differences are reported.

        Args:
            json_data: The actual JSON, as a string or parsed object.
            ref_path: The name of the reference file.
            kind: See `assertStringCorrect` for details.
            remove_keys: An optional set/list of key names to remove from
                the JSON at any depth before comparison.
            norm_paths: If `True`, normalise Windows-style path separators
                to POSIX in all string values. If a string or list of
                strings, treat as fnmatch-style key globs and only normalise
                values of matching keys.
            preprocess: An optional function (or list of functions) applied
                to the JSON string before parsing. If a list `[f, g]` is
                given, `g(f(·))` is computed, where `·` is the JSON string.
        """
        if not isinstance(json_data, str):
            json_data = json.dumps(
                json_data, indent=2, sort_keys=True, ensure_ascii=False
            )
        normalizer = lambda lines: normalize_json_for_comparison(
            lines,
            remove_keys=remove_keys,
            norm_paths=norm_paths,
            preprocess=preprocess,
        )
        self.assertStringCorrect(
            json_data, ref_path, kind=kind, preprocess=normalizer
        )

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
        norm_paths=None,
        max_permutation_cases=0,
        encoding=None,
        norm_line_endings=True,
    ):
        """Check that a text file matches the contents from a reference
        text file.

        For CSV files, use ``assertStoredDataFrameCorrect`` instead.

        Args:
            actual_path: Path to the actual text file.
            ref_path: The name of the reference file. The location of the
                reference file is determined by the configuration via
                ``set_data_location()``.
            kind: See ``assertStringCorrect`` for details.
            lstrip: See ``assertStringCorrect`` for details.
            rstrip: See ``assertStringCorrect`` for details.
            ignore_substrings: See ``assertStringCorrect`` for details.
            ignore_patterns: See ``assertStringCorrect`` for details.
            remove_lines: See ``assertStringCorrect`` for details.
            preprocess: See ``assertStringCorrect`` for details.
            norm_paths: See ``assertStringCorrect`` for details.
            max_permutation_cases: See ``assertStringCorrect`` for details.
            encoding: Optional character encoding for reading the file.

        Note:
            ``ignore_lines`` is a legacy alias for ``remove_lines``.
            ``assertFileCorrect`` is a legacy alias for this method.
        """
        preprocess = self._resolve_preprocess(preprocess, norm_paths)
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
                norm_line_endings=norm_line_endings,
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
        norm_paths=None,
        max_permutation_cases=0,
        encodings=None,
        norm_line_endings=True,
    ):
        """Check that a collection of text files match the contents from a
        matching collection of reference text files.

        For CSV files, use ``assertStoredDataFramesCorrect`` instead.

        Args:
            actual_paths: A list of paths for text files.
            ref_paths: A list of names of the matching reference files.
                The location of the reference files is determined by the
                configuration via ``set_data_location()``.
            kind: See ``assertStringCorrect`` for details.
            lstrip: See ``assertStringCorrect`` for details.
            rstrip: See ``assertStringCorrect`` for details.
            ignore_substrings: See ``assertStringCorrect`` for details.
            ignore_patterns: See ``assertStringCorrect`` for details.
            remove_lines: See ``assertStringCorrect`` for details.
            preprocess: See ``assertStringCorrect`` for details.
            norm_paths: See ``assertStringCorrect`` for details.
            max_permutation_cases: See ``assertStringCorrect`` for details.
            encodings: Optional list of character encodings, one per file.

        Note:
            ``ignore_lines`` is a legacy alias for ``remove_lines``.
            ``assertFilesCorrect`` is a legacy alias for this method.
        """
        preprocess = self._resolve_preprocess(preprocess, norm_paths)
        expected_paths = self._resolve_reference_paths(ref_paths, kind=kind)
        if self._should_regenerate(kind):
            self._write_reference_files(
                actual_paths, expected_paths, lstrip=lstrip, rstrip=rstrip
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
                norm_line_endings=norm_line_endings,
            )
            (failures, msgs) = r
            self._check_failures(failures, msgs)

    # DEPRECATED
    assertFileCorrect = assertTextFileCorrect
    assertFilesCorrect = assertTextFilesCorrect

    def assertBinaryFileCorrect(self, actual_path, ref_path, kind=None):
        """Check that a binary file matches the contents from a reference
        binary file.

        Args:
            actual_path: Path to the actual binary file.
            ref_path: The name of the reference binary file. The location
                of the reference file is determined by the configuration
                via ``set_data_location()``.
            kind: The reference kind, used to locate the reference file.
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
        lib = self.get_comparison_lib(df)
        lib._write_reference_dataframe(df, reference_path)

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

    def _resolve_preprocess(self, preprocess, norm_paths):
        """Return effective preprocess function combining preprocess and
        norm_paths.

        If norm_paths is True (or set on the class) and we're on Windows,
        windows_paths_to_posix is applied after preprocess (or alone if
        preprocess is None). A per-call norm_paths value of None defers to
        the class setting; an explicit True or False overrides it.
        """
        use = self.norm_paths if norm_paths is None else norm_paths
        if not use or os.sep != '\\':
            return preprocess
        if preprocess is None:
            return windows_paths_to_posix
        return lambda lines: windows_paths_to_posix(preprocess(lines))

    def call_print_fn(self, *args, **kwargs):
        fn = self.print_fn or self._default_print_fn
        fn(*args, **kwargs)

    def choose_common_df_lib(self, ldf, rdf, engine=None):
        le, re = df_type(ldf), df_type(rdf)
        if le == re == 'pandas':
            return ldf, rdf, self.pandas
        if le == re == 'polars':
            return ldf, rdf, self.polars

        engine = get_preferred_engine(engine)
        lib = self.polars if engine == 'polars' else self.pandas
        return df_definite(ldf, engine), df_definite(rdf, engine), lib

    def get_comparison_lib(self, df=None, engine=None):
        if df is None:
            engine = get_preferred_engine(engine)
            return self.polars if engine == 'polars' else self.pandas
        else:
            return self.pandas if is_pandas_df(df) else self.polars

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


def get_preferred_engine(engine):
    if engine is None:
        config = get_config(None)
        engine = config.get('engine')
    if not engine in ('polars', 'pandas'):
        error(f'Unknown dataframe engine: {engine}')
    return engine


# Magic so that an instance of this class can masquerade as a module,
# so that all of its methods can be made available as top-level functions,
# to work will with frameworks like pytest.
ReferenceTest.__all__ = dir(ReferenceTest)
