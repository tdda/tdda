# -*- coding: utf-8 -*-

"""
The ``tdda`` command-line utility provides built-in support for constraint
discovery and verification for tabular data stored in CSV files, Pandas
DataFrames saved in ``.parquet`` files, and for a tables in a variety of
different databases.

The utility can be extended to provide support for constraint discovery
and verification for other kinds of data, via its Python extension framework.

The framework will automatically use any extension implementations that
have been declared using the ``TDDA_EXTENSIONS`` environment variable. This
should be set to a list of class names, for Python classes that extend the
``ExtensionBase`` base class.

The class names in the ``TDDA_EXTENSIONS`` environment variable should be
colon-separated for Unix systems, or semicolon-separated for Microsoft
Windows. To be usable, the classes must be accessible by Python (either
by being installed in Pythons standard module directory, or by being
included in the ``PYTHONPATH`` environment variable.

For example::

    export TDDA_EXTENSIONS="mytdda.MySpecialExtension"
    export PYTHONPATH="/my/python/sources:$PYTHONPATH"

With these in place, the ``tdda`` command will include constraint discovery
and verification using the ``MySpecialExtension`` implementation class
provided in the Python file ``/my/python/sources/mytdda.py``.

An example of a simple extension is included with the set of standard
examples (see ``tdda examples``).

Extension Overview
------------------

An extension should provide:

 - an implementation (subclass) of ``ExtensionBase``, to
   provide a command-line interface, extending the ``tdda`` command
   to support a particular type of input data.

 - an implementation (subclass) of ``BaseConstraintCalculator``,
   to provide methods for computing individual constraint results.

 - an implementation (subclass) of ``BaseConstraintDetector``,
   to provide methods for generating detection results.


A typical implementation looks like::

    from tdda.constraints.flags import discover_parser, discover_flags
    from tdda.constraints.flags import verify_parser, verify_flags
    from tdda.constraints.flags import detect_parser, detect_flags
    from tdda.constraints.extension import ExtensionBase
    from tdda.constraints.base import DatasetConstraints, Detection
    from tdda.constraints.baseconstraints import (BaseConstraintCalculator,
                                                  BaseConstraintVerifier,
                                                  BaseConstraintDetector,
                                                  BaseConstraintDiscoverer)
    from tdda.rexpy import rexpy

    class MyExtension(ExtensionBase):
        def applicable(self):
            ...

        def help(self, stream=sys.stdout):
            print('...', file=stream)

        def spec(self):
            return '...'

        def discover(self):
            parser = discover_parser()
            parser.add_argument(...)
            params = {}
            flags = discover_flags(parser, self.argv[1:], params)
            data = ... get data source from flags ...
            discoverer = MyConstraintDiscoverer(data, **params)
            constraints = discoverer.discover()
            results = constraints.to_json()
            ... write constraints JSON to output file
            return results

        def verify(self):
            parser = verify_parser()
            parser.add_argument(...)
            params = {}
            flags = verify_flags(parser, self.argv[1:], params)
            data = ... get data source from flags ...
            verifier = MyConstraintVerifier(data, **params)
            constraints = DatasetConstraints(loadpath=...)
            results = verifier.verify(constraints)
            return results

        def detect(self):
            parser = detect_parser()
            parser.add_argument(...)
            params = {}
            flags = detect_flags(parser, self.argv[1:], params)
            data = ... get data source from flags ...
            detector = MyConstraintDetector(data, **params)
            constraints = DatasetConstraints(loadpath=...)
            results = detector.detect(constraints)
            return results

Extension API
-------------
"""

import sys


class ExtensionBase:
    """Base class for tdda command-line extensions.

    Subclass this to add support for new data sources to the ``tdda``
    command. The subclass must implement ``applicable()``, and should
    implement ``discover()``, ``verify()``, and ``detect()``.

    Args:
        argv: List of command-line argument strings (e.g. ``sys.argv``).
        verbose: If ``True``, enable verbose output. Default is
            ``False``.
    """

    def __init__(self, argv, verbose=False):
        self.argv = argv
        self.verbose = verbose

    def applicable(self):
        """Return ``True`` if this extension can handle the given arguments.

        For example, an extension for Excel files should return ``True``
        if any of the ``argv`` strings have a ``.xlsx`` suffix.
        """
        return False

    def help(self, stream=sys.stdout):
        """Write help text for this extension to ``stream``.

        Args:
            stream: Output stream. Default is ``sys.stdout``.
        """
        pass

    def spec(self):
        """Return a brief one-line string describing how to specify the
        input source.
        """
        return ''

    def discover(self):
        """Implement constraint discovery.

        Use ``self.argv`` to obtain the data source and output path for
        the discovered constraints.
        """
        pass

    def verify(self):
        """Implement constraint verification.

        Read constraints from a ``.tdda`` file specified in ``self.argv``
        and verify them against the specified data.
        """
        pass

    def detect(self):
        """Implement constraint detection.

        Read constraints from a ``.tdda`` file specified in ``self.argv``,
        verify them against the specified data, and write detection output.
        Use ``self.argv`` to get the data source, where the detection
        output should be written, and any detection-specific flags.
        """
        pass


class BaseConstraintCalculator:
    """
    Default or dummy implementation of all methods required to implement
    a constraint discoverer or verifier via subclasses of
    ``BaseConstraintDiscoverer`` and ``BaseConstraintVerifier``.
    """

    def is_null(self, value):
        """
        Determine whether a value is null
        """
        return value is None

    def to_datetime(self, value):
        """
        Convert a value to a datetime
        """
        return value

    def column_exists(self, colname):
        """
        Returns whether this column exists in the dataset
        """
        return colname in self.get_column_names()

    def get_column_names(self):
        """
        Returns a list containing the names of all the columns
        """
        raise NotImplementedError('column_names')

    def get_nrecords(self):
        """
        Return total number of records
        """
        raise NotImplementedError('nrecords')

    def types_compatible(self, x, y, colname):
        """
        Determine whether the types of two values are compatible
        """
        raise NotImplementedError('types_compatible')

    # def allowed_values_exclusions(self):
    #     """
    #     Get list of values to ignore when computing allowed values
    #     """
    #     return [None]

    def filter_out_nulls(self, values):
        return {v for v in values if not v is None}

    def calc_tdda_type(self, colname):
        """
        Calculates the TDDA type of a column
        """
        raise NotImplementedError('type')

    def calc_min(self, colname):
        """
        Calculates the minimum (non-null) value in the named column.
        """
        raise NotImplementedError('min')

    def calc_max(self, colname):
        """
        Calculates the maximum (non-null) value in the named column.
        """
        raise NotImplementedError('max')

    def calc_min_length(self, colname):
        """
        Calculates the length of the shortest string(s) in the named column.
        """
        raise NotImplementedError('min_length')

    def calc_max_length(self, colname):
        """
        Calculates the length of the longest string(s) in the named column.
        """
        raise NotImplementedError('max_length')

    def calc_null_count(self, colname):
        """
        Calculates the number of nulls in a column
        """
        raise NotImplementedError('null_count')

    def calc_non_null_count(self, colname):
        """
        Calculates the number of nulls in a column
        """
        raise NotImplementedError('non_null_count')

    def calc_nunique(self, colname):
        """
        Calculates the number of unique non-null values in a column
        """
        raise NotImplementedError('nunique')

    def calc_unique_values(self, colname, include_nulls=True):
        """
        Calculates the set of unique values (including or excluding nulls)
        in a column
        """
        raise NotImplementedError('unique_values')

    def calc_non_integer_values_count(self, colname):
        """
        Calculates the number of unique non-integer values in a column

        This is only required for implementations where a dataset column
        may contain values of mixed type.
        """
        raise NotImplementedError('non_integer_values_count')

    def calc_all_non_nulls_boolean(self, colname):
        """
        Checks whether all the non-null values in a column are boolean.
        Returns True of they are, and False otherwise.

        This is only required for implementations where a dataset column
        may contain values of mixed type.
        """
        raise NotImplementedError('all_non_nulls_boolean')

    def find_rexes(self, colname, values=None):
        """
        Generate a list of regular expressions that cover all of
        the patterns found in the (string) column.
        """
        raise NotImplementedError('find_rexes')

    def calc_rex_constraint(self, colname, constraint, detect=False):
        """
        Verify whether a given column satisfies a given regular
        expression constraint (by matching at least one of the regular
        expressions given).

        Returns:
            A truthy value (typically the set of strings that do not
            match any of the regular expressions) on failure, or a falsy
            value (False, None, or empty set) if there are no failures.
            Any contents are used when detect is set, by the corresponding
            extension method for recording detection results.
        """
        raise NotImplementedError('verify_rex')


class BaseConstraintDetector:
    """
    Default or dummy implementation of all methods required to implement
    constraint detection via a subclass of ``BaseConstraintVerifier``.
    """

    def detect_min_constraint(self, colname, value, precision, epsilon):
        """
        Detect failures for a min constraint.
        """
        pass

    def detect_max_constraint(self, colname, value, precision, epsilon):
        """
        Detect failures for a max constraint.
        """
        pass

    def detect_min_length_constraint(self, colname, value):
        """
        Detect failures for a min_length constraint.
        """
        pass

    def detect_max_length_constraint(self, colname, value):
        """
        Detect failures for a max_length constraint.
        """
        pass

    def detect_tdda_type_constraint(self, colname, value):
        """
        Detect failures for a type constraint.
        """
        pass

    def detect_sign_constraint(self, colname, value):
        """
        Detect failures for a sign constraint.
        """
        pass

    def detect_max_nulls_constraint(self, colname, value):
        """
        Detect failures for a max_nulls constraint.
        """
        pass

    def detect_no_duplicates_constraint(self, colname, value):
        """
        Detect failures for a no_duplicates constraint.
        """
        pass

    def detect_allowed_values_constraint(self, colname, value, violations):
        """
        Detect failures for an allowed_values constraint.
        """
        pass

    def detect_rex_constraint(self, colname, violations):
        """
        Detect failures for a rex constraint.
        """
        pass

    def write_detected_records(
        self,
        outpath=None,
        write_all_records=False,
        per_constraint=False,
        output_fields=None,
        index=False,
        in_place=False,
        rownumber_is_index=True,
        boolean_ints=False,
        **kwargs,
    ):
        """
        Write out a detection dataset.

        Returns:
            ``tdda.constraints.base.Detection`` object, or ``None``.
        """
        pass
