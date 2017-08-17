# -*- coding: utf-8 -*-

"""
The ``tdda`` command-line utility provides built-in support for constraint
discovery and verification for tabular data stored in CSV files, Pandas
DataFrames saved in ``.feather`` files, and for a tables in a variety of
different databases.

The utility can be extended to provide support for constraint discovery
and verification for other kinds of data, via its Python extension framework.

The framework will automatically use any extension implementations that
have been declared using the ``TDDA_EXTENSIONS`` environment variable. This
should be set to a list of class names, for Python classes that extend the
:py:class:`ExtensionBase` base class.

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

An  example of a simple extension is included with the set of standard
examples. See :ref:`examples`.

Extension API
-------------
"""

import sys


class ExtensionBase:
    """
    An extension must provide a class that is based on the
    :py:class:`ExtensionBase` class, providing implementations for its
    :py:meth:`applicable`, :py:meth:`help`, :py:meth:`discover` and
    :py:meth:`verify` methods.
    """
    def __init__(self, argv, verbose=False):
        self.argv = argv
        self.verbose = verbose

    def applicable(self):
        """
        The :py:meth:`applicable` method should return ``True`` if the
        :py:attr:`argv` property contains command-line parameters that
        can be used by this implementation.

        For example, if the extension can handle data stored in Excel
        ``.xlsx`` files, then its :py:meth:`applicable` method should
        return ``True`` if any of its parameters are filenames that have
        a ``.xlsx`` suffix.
        """
        return False

    def help(self, stream=sys.stdout):
        """
        help(self, stream=sys.stdout)
        The :py:meth:`help` method should document itself by writing
        lines to the given output stream.

        This is used by the ``tdda`` command's ``help`` option.
        """
        pass

    def spec(self):
        """
        The :py:meth:`spec` method should return a short one-line string
        describing, briefly, how to specify the input source.
        """
        return ''

    def discover(self):
        """
        The :py:meth:`discover` method should implement constraint
        discovery.

        It should allow whatever other optional or mandatory flags or
        parameters are required to specify the data from which constraints
        are to be discovered, and the name of the file to which the
        constraints are to be written.
        """
        pass

    def verify(self):
        """
        The :py:meth:`verify` method should implement constraint
        verification.

        It should read constraints from a ``.tdda`` file specified on
        the command line, and verify these constraints on the data
        specified.

        It should allow whatever other optional or mandatory flags or
        parameters are required to specify the data on which the constraints
        are to be verified.
        """
        pass


class BaseConstraintCalculator:
    """
    The :py:mod:`BaseConstraintCalculator` class defines a default or dummy
    implementation o fall of the methods that are required in order
    to implement a constraint discoverer or verifier using the
    :py:mod:`BaseConstraintDiscoverer` and :py:mod:`BaseConstraintVerifier`
    classes.
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

    def allowed_values_exclusions(self):
        """
        Get list of values to ignore when computing allowed values
        """
        return [None]

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

    def verify_rex_constraint(self, colname, constraint):
        """
        Verify whether a given column satisfies a given regular
        expression constraint (by matching at least one of the regular
        expressions given).
        """
        raise NotImplementedError('verify_rex')


