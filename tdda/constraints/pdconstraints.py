# -*- coding: utf-8 -*-
"""
TDDA constraint discovery and verification for Pandas.

The top-level functions are:

    :py:func:`discover_constraints`:
        Discover constraints from a Pandas DataFrame.

    :py:func:`verify_df`:
        Verify (check) a Pandas DataFrame, against a set of previously
        discovered constraints.

API
---

"""
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import datetime
import sys

from collections import OrderedDict

import pandas as pd
import numpy as np

from tdda.constraints.base import (
    PRECISIONS,
    SIGNS,
    STANDARD_FIELD_CONSTRAINTS,
    verify,
    DatasetConstraints,
    FieldConstraints,
    Verification,
    TypeConstraint,
    MinConstraint, MaxConstraint, SignConstraint,
    MinLengthConstraint, MaxLengthConstraint,
    NoDuplicatesConstraint, MaxNullsConstraint,
    AllowedValuesConstraint,
)

TYPE_CHECKING_OPTIONS = ('strict', 'sloppy')
DEFAULT_TYPE_CHECKING = 'sloppy'

MAX_CATEGORIES = 20     # String fields with up to 20 categories will
                        # generate AllowedValues constraints

EPSILON_DEFAULT = 0.01  # 1 per cent tolerance for min/max constraints for
                        # real (i.e. floating point) fields.


if sys.version_info.major >= 3:
    long = int


class PandasConstraintVerifier:
    def __init__(self, df, epsilon=None, type_checking=None):
        self.df = df
        self.epsilon = EPSILON_DEFAULT if epsilon is None else epsilon
        self.type_checking = type_checking or DEFAULT_TYPE_CHECKING
        assert self.type_checking in TYPE_CHECKING_OPTIONS
        self.cache = {}

    def verifiers(self):
        """
        Returns a dictionary mapping constraint types to their callable
        (bound) verification methods.
        """
        return {
            'type': self.verify_tdda_type_constraint,
            'min': self.verify_min_constraint,
            'max': self.verify_max_constraint,
            'min_length': self.verify_min_length_constraint,
            'max_length': self.verify_max_length_constraint,
            'sign': self.verify_sign_constraint,
            'max_nulls': self.verify_max_nulls_constraint,
            'no_duplicates': self.verify_no_duplicates_constraint,
            'allowed_values': self.verify_allowed_values_constraint,
        }

    def verify_min_constraint(self, colname, constraint):
        """
        Verify whether a given column satisfies the minimum value
        constraint specified.
        """
        value = constraint.value
        precision = getattr(constraint, 'precision', 'closed') or 'closed'
        assert precision in PRECISIONS

        if pd.isnull(value):      # a null minimum is not considered to be an
            return True           # active constraint, so is always satisfied

        m = self.get_min(colname)
        if pd.isnull(m):          # If there are no values, no value can
            return True           # the minimum constraint

        if isinstance(value, datetime.datetime):
            m = pd.to_datetime(m)

        if not types_compatible(m, value, colname):
            return False

        if precision == 'closed':
            return m >= value
        elif precision == 'open':
            return m > value
        else:
            return self.fuzzy_greater_than(m, value)


    def verify_max_constraint(self, colname, constraint):
        """
        Verify whether a given column satisfies the maximum value
        constraint specified.
        """
        value = constraint.value
        precision = getattr(constraint, 'precision', 'closed') or 'closed'
        assert precision in ('open', 'closed', 'fuzzy')

        if pd.isnull(value):      # a null maximum is not considered to be an
            return True           # active constraint, so is always satisfied

        M = self.get_max(colname)
        if pd.isnull(M):          # If there are no values, no value can
            return True           # the maximum constraint

        if isinstance(value, datetime.datetime):
            M = pd.to_datetime(M)
        if not types_compatible(M, value, colname):
            return False

        if precision == 'closed':
            return M <= value
        elif precision == 'open':
            return M < value
        else:
            return self.fuzzy_less_than(M, value)

    def verify_min_length_constraint(self, colname, constraint):
        """
        Verify whether a given (string) column satisfies the minimum length
        constraint specified.
        """
        value = constraint.value

        if pd.isnull(value):      # a null minimum length is not considered
            return True           # to be an active constraint, so is always
                                  # satisfied

        m = self.get_min_length(colname)
        if pd.isnull(m):          # If there are no values, no value can
            return True           # the minimum length constraint

        return m >= value

    def verify_max_length_constraint(self, colname, constraint):
        """
        Verify whether a given (string) column satisfies the maximum length
        constraint specified.
        """
        value = constraint.value

        if pd.isnull(value):      # a null minimum length is not considered
            return True           # to be an active constraint, so is always
                                  # satisfied

        M = self.get_max_length(colname)
        if pd.isnull(M):          # If there are no values, no value can
            return True           # the maximum length constraint

        return M <= value

    def verify_tdda_type_constraint(self, colname, constraint):
        """
        Verify whether a given column satisfies the supplied type constraint.
        """
        required_type = constraint.value
        allowed_types = (required_type if type(required_type) in (list, tuple)
                         else [required_type])
        if len(allowed_types) == 1 and pd.isnull(allowed_types[0]):
            return True  # a null type is not considered to be an
                         # active constraint, so is always satisfied

        actual_type = self.get_tdda_type(colname)
        if self.type_checking == 'strict':
            return actual_type in allowed_types
        else:
            if actual_type in allowed_types:
                return True       # definitely OK of the types actuall match
            elif 'int' in allowed_types and actual_type == 'real':
                return self.get_non_integer_values_count(colname) == 0
            elif 'bool' in allowed_types and actual_type == 'string':
                # boolean columns with nulls get converted to dtype
                # object, which is usually used for strings
                return self.get_all_non_nulls_boolean(colname)
            else:
                return False

    def verify_sign_constraint(self, colname, constraint):
        """
        Verify whether a given column satisfies the supplied sign constraint.
        """
        value = constraint.value
        if pd.isnull(value):      # a null value (as opposed to the string
                                  # 'null') is not considered to be an
            return True           # active constraint, so is always satisfied

        m = self.get_min(colname)
        M = self.get_max(colname)
        if pd.isnull(m):
            return True  # no values: cannot violate constraint
        if value == 'null':
            return False
        elif value == 'positive':
            return m > 0
        elif value == 'non-negative':
            return m >= 0
        elif value == 'zero':
            return m == M == 0
        elif value == 'non-positive':
            return M <= 0
        elif value == 'negative':
            return M < 0
        assert value in SIGNS

    def verify_max_nulls_constraint(self, colname, constraint):
        """
        Verify whether a given column satisfies the supplied constraint
        that it should contain no nulls.
        """
        value = constraint.value
        if pd.isnull(value):      # a null value is not considered to be an
            return True           # active constraint, so is always satisfied
        return self.get_null_count(colname) <= value

    def verify_no_duplicates_constraint(self, colname, constraint):
        """
        Verify whether a given column satisfies the constraint supplied,
        that it should contain no duplicate (non-null) values.
        """
        value = constraint.value
        if pd.isnull(value):      # a null value is not considered to be an
            return True           # active constraint, so is always satisfied

        assert value == True      # value not really used; but should be True

        non_nulls = len(self.df) - self.get_null_count(colname)
        return self.get_nunique(colname) == non_nulls

    def verify_allowed_values_constraint(self, colname, constraint):
        """
        Verify whether a given column satisfies the constraint on allowed
        (string) values provided.
        """
        allowed_values = constraint.value
        if allowed_values is None:      # a null value is not considered
            return True                 # to be an active constraint,
                                        # so is always satisfied

        n_allowed_values = len(allowed_values)
        n_actual_values = self.get_nunique(colname)

        if n_actual_values > n_allowed_values:
            return False

        actual_values = self.get_unique_values(colname)

        violations = (set(actual_values) - set(allowed_values)
                      - set([None, np.nan, pd.NaT]))  # remarkably, Pandas
                                                      # returns various kinds
                                                      # of nulls as unique
                                                      # values, despite not
                                                      # counting them with
                                                      # .nunique()
        return len(violations) == 0

    def fuzzy_greater_than(self, a, b):
        """
        Returns a >~ b (a is greater than or approximately equal to b)

        At the moment, this simply reduces b by 1% if it is positive,
        and makes it 1% more negative if it is negative.
        """
        if a >= b:
            return True
        return (a >= self.fuzz_down(b))


    def fuzzy_less_than(self, a, b):
        """
        Returns a <~ b (a is greater than or approximately equal to b)

        At the moment, this increases b by 1% if it is positive,
        and makes it 1% less negative if it is negative.
        """
        if a <= b:
            return True
        return (a <= self.fuzz_up(b))

    def fuzz_down(self, v):
        """
        Adjust v downwards, by a proportion controlled by self.epsilon.
        This is typically used for fuzzy minimum constraints.

        By default, positive values of v are reduced by 1% so that slightly
        smaller values can pass the fuzzy minimum constraint.

        Similarly, negative values are made 1% more negative, so that
        slightly more negative values can still pass a fuzzy minimum
        constraint.
        """
        return v * ((1 - self.epsilon) if v >= 0 else (1 + self.epsilon))

    def fuzz_up(self, v):
        """
        Adjust v upwards, by a proportion controlled by self.epsilon.
        This is typically used for fuzzy maximum constraints.

        By default, positive values of v are increased by 1% so that
        slightly larger values can pass the fuzzy maximum constraint.

        Similarly, negative values are made 1% less negative, so that
        slightly less negative values can still pass a fuzzy maximum
        constraint.
        """
        return v * ((1 + self.epsilon) if v >= 0 else (1 - self.epsilon))

    def get_min(self, colname):
        """Looks up cached minimum of column, or calculates and caches it"""
        return self.get_cached_value('min', colname, self.calc_min)

    def calc_min(self, colname):
        """
        Calculates the minimum (non-null) value in the named column.
        """
        if self.df[colname].dtype == np.dtype('O'):
            return self.df[colname].dropna().min()  # Otherwise -inf!
        else:
            return self.df[colname].min()

    def get_max(self, colname):
        """Looks up cached maximum of column, or calculates and caches it"""
        return self.get_cached_value('max', colname, self.calc_max)

    def calc_max(self, colname):
        """
        Calculates the maximum (non-null) value in the named column.
        """
        if self.df[colname].dtype == np.dtype('O'):
            return self.df[colname].dropna().max()
        else:
            return self.df[colname].max()

    def get_min_length(self, colname):
        """
        Looks up cached minimum string length in column,
        or calculates and caches it
        """
        return self.get_cached_value('min_length', colname,
                                     self.calc_min_length)

    def calc_min_length(self, colname):
        """
        Calculates the length of the shortest string(s) in the named column.
        """
        return min(len(s) for s in list(self.df[colname].unique())
                          if not pd.isnull(s))

    def get_max_length(self, colname):
        """
        Looks up cached maximum string length in column,
        or calculates and caches it
        """
        return self.get_cached_value('max_length', colname,
                                     self.calc_max_length)

    def calc_max_length(self, colname):
        """
        Calculates the length of the longest string(s) in the named column.
        """
        return max(len(s) for s in list(self.df[colname].unique())
                          if not pd.isnull(s))

    def get_tdda_type(self, colname):
        """
        Looks up cached tdda type of a column,
        or calculates and caches it
        """
        return self.get_cached_value('tdda_type', colname,
                                     lambda x: tdda_type(self.df[colname]))

    def get_null_count(self, colname):
        """
        Looks up or caches the number of nulls in a column,
        or calculates and caches it
        """
        f = lambda x: len(self.df) - self.df[colname].count()
        return self.get_cached_value('null_count', colname, f)

    def get_nunique(self, colname):
        """
        Looks up or caches the number of unique (distinct) values in a column,
        or calculates and caches it.
        """
        return self.get_cached_value('nunique', colname,
                                     lambda x: self.df[colname].nunique())

    def get_unique_values(self, colname):
        """
        Looks up or caches the list of unique (distinct) values in a column,
        or calculates and caches it.
        """
        return self.get_cached_value('uniques', colname,
                                     lambda x: self.df[colname].unique())

    def get_non_integer_values_count(self, colname):
        """
        Looks up or caches the number of non-integer values in a real column,
        or calculates and caches it.
        """
        return self.get_cached_value('non_integer_values_count', colname,
                                     self.calc_non_integer_values_count)

    def calc_non_integer_values_count(self, colname):
        values = self.df[colname].dropna()
        non_nulls = self.df[colname].count()
        return non_nulls - (values.astype(int) == values).astype(int).sum()

    def get_all_non_nulls_boolean(self, colname):
        """
        Looks up or caches the number of non-integer values in a real column,
        or calculates and caches it.
        """
        return self.get_cached_value('all_non_nulls_boolean', colname,
                                     self.calc_all_non_nulls_boolean)

    def calc_all_non_nulls_boolean(self, colname):
        """
        Checks whether all the non-null values in a column are boolean.
        Returns True of they are, and False otherwise.
        """
        nn = self.df[colname].dropna()
        return all([type(v) is bool for i, v in nn.iteritems()])

    def get_cached_value(self, value, colname, f):
        """
        Return cached value of colname, calculating it and caching it
        first, if it is not already there.
        """
        col_cache = self.cache_values(colname)
        if not value in col_cache:
            col_cache[value] = f(colname)
        return col_cache[value]

    def cache_values(self, colname):
        """
        Returns the dictionary for colname from the cache, first creating
        it if there isn't one on entry.
        """
        if not colname in self.cache:
            self.cache[colname] = {}
        return self.cache[colname]


class PandasVerification(Verification):
    """
    A :py:class:`PandasVerification` object adds a :py:meth:`to_frame()`
    method to a :py:class:`tdda.constraints.base.Verification` object.

    This allows the result of constraint verification to be converted to a
    Pandas DataFrame, including columns for the field (column) name,
    the numbers of passes and failures and boolean columns for each
    constraint, with values:

        - ``True``       --- if the constraint was satified for the column
        - ``False``      --- if column failed to satisfy the constraint
        - ``pd.np.NaN``  --- if there was no constraint of this kind for this field.
    """
    def __init__(self, *args, **kwargs):
        Verification.__init__(self, *args, **kwargs)

    def to_frame(self):
        """
        Converts object to a Pandas DataFrame.
        """
        return verification_to_dataframe(self)

    to_dataframe = to_frame


def types_compatible(x, y, colname=None):
    """
    Returns boolean indicating whether the coarse_type of *x* and *y* are
    the same.

    If *colname* is provided, and the check fails, a warning is issued
    to stderr.
    """
    ok = coarse_type(x) == coarse_type(y)
    if not ok and colname:
        print('Warning: Failing incompatible types constraint for field %s '
              'of type %s.\n(Constraint value %s of type %s.)'
              % (colname, type(x), y, type(y)), file=sys.stderr)
    return ok


def coarse_type(x):
    """
    Returns the TDDA coarse type of *x*, a column or scalar.
    The coarse types combine 'bool', 'int' and 'real' into 'number'.

    Obviously, some people will dislike treating booleans as numbers.
    But it is necessary here.
    """
    t = tdda_type(x)
    return 'number' if t in ('bool', 'int', 'real') else t


def tdda_type(x):
    """
    Returns the TDDA type of a column or scalar.

    Basic TDDA types are one of 'bool', 'int', 'real', 'string' or 'date'.

    If *x* is ``None`` or something Pandas classes as null, 'null' is returned.

    If *x* is not recognized as one of these, 'other' is returned.
    """
    dt = getattr(x, 'dtype', None)
    if type(x) == str or dt == np.dtype('O'):
        return 'string'
    dts = str(dt)
    if type(x) == bool or 'bool' in dts:
        return 'bool'
    if type(x) in (int, long) or 'int' in dts:
        return 'int'
    if type(x) == float or 'float' in dts:
        return 'real'
    if (type(x) == datetime.datetime or 'datetime' in dts
                or type(x) == pd.tslib.Timestamp):
        return 'date'
    if x is None or (not isinstance(x, pd.core.series.Series)
                     and pd.isnull(x)):
        return 'null'
    # Everything else is other, for now, including compound types,
    # unicode in Python2, bytes in Python3 etc.
    return 'other'


def discover_field_constraints(field):
    """
    Discover constraints for a single field (column) from a Pandas DataFrame.

    Input:

        *field*:
            a single field (column; Series) object, usually from
            a Pandas DataFrame.

    Returns:

        - :py:class:`tdda.base.FieldConstraints` object,
          if any constraints were found.
        - ``None``, otherwise.

    """
    min_constraint = max_constraint = None
    min_length_constraint = max_length_constraint = None
    sign_constraint = no_duplicates_constraint = None
    max_nulls_constraint = allowed_values_constraint = None

    type_ = tdda_type(field)
    if type_ == 'other':
        return None         # Unrecognized or complex
    else:
        type_constraint = TypeConstraint(type_)
    length = len(field)

    if length > 0:  # Things are not very interesting when there is no data
        nNull = int(field.isnull().sum().astype(int))
        nNonNull = int(field.notnull().sum().astype(int))
        assert nNull + nNonNull == length
        if nNull < 2:
            max_nulls_constraint = MaxNullsConstraint(nNull)

        # Useful info:
        uniqs = None
        n_unique = -1   # won't equal number of non-nulls later on
        if type_ in ('string', 'int'):
            n_unique = field.nunique()          # excludes NaN
            if type_ == 'string':
                if n_unique <= MAX_CATEGORIES:
                    uniqs = list(field.dropna().unique())
                if uniqs:
                    allowed_values_constraint = AllowedValuesConstraint(uniqs)

        if nNonNull > 0:
            if type_ == 'string':
                # We don't generate a min, max or sign constraints for strings
                # But we do generate min and max length constraints
                if (uniqs is None         # There were too many for us to have
                    and n_unique > 0):    # bothered getting them all
                    uniqs = list(field.dropna().unique())  # need them now
                if uniqs:
                    m = min(len(v) for v in uniqs)
                    M = max(len(v) for v in uniqs)
                    min_length_constraint = MinLengthConstraint(m)
                    max_length_constraint = MaxLengthConstraint(M)
            else:
                # Non-string fields all potentially get min and max values
                if type_ == 'date':
                    m = field.min()
                    M = field.max()
                    if pd.notnull(m):
                        m = m.to_pydatetime()
                    if pd.notnull(M):
                        M = M.to_pydatetime()
                else:
                    m = field.min().item()
                    M = field.max().item()
                if pd.notnull(m):
                    min_constraint = MinConstraint(m)
                if pd.notnull(M):
                    max_constraint = MaxConstraint(M)

                # Non-date fields potentially get a sign constraint too.
                if min_constraint and max_constraint and type_ != 'date':
                    if m == M == 0:
                        sign_constraint = SignConstraint('zero')
                    elif m >= 0:
                        sign = 'positive' if m > 0 else 'non-negative'
                        sign_constraint = SignConstraint(sign)
                    elif M <= 0:
                        sign = 'negative' if M < 0 else 'non-positive'
                        sign_constraint = SignConstraint(sign)
                    # else:
                        # mixed
                elif pd.isnull(m) and type_ != 'date':
                    sign_constraint = SignConstraint('null')

        if n_unique == nNonNull and n_unique > 1 and type_ != 'real':
            no_duplicates_constraint = NoDuplicatesConstraint()

    constraints = [c for c in [type_constraint,
                               min_constraint, max_constraint,
                               min_length_constraint, max_length_constraint,
                               sign_constraint, max_nulls_constraint,
                               no_duplicates_constraint,
                               allowed_values_constraint]
                     if c is not None]
    return FieldConstraints(field.name, constraints)


def verification_to_dataframe(ver):
    """
    Convert a :py:class:`PandasVerification` object to a Pandas DataFrame.
    """
    fields = ver.fields
    df = pd.DataFrame(OrderedDict((
        ('field', list(fields.keys())),
        ('failures', [v.failures for k, v in fields.items()]),
        ('passes', [v.passes for k, v in fields.items()]),
    )))
    kinds_used = set([])
    for field, constraints in fields.items():
        kinds_used = kinds_used.union(set(list(constraints.keys())))
    base_kinds = [k for k in STANDARD_FIELD_CONSTRAINTS if k in kinds_used]
    other_kinds = [k for k in kinds_used if not k in base_kinds]
    for kind in base_kinds + other_kinds:
        df[kind] = [fields[field].get(kind, np.nan) for field in fields]
    return df


def verify_df(df, constraints_path, epsilon=None, type_checking=None,
              **kwargs):
    """
    Verify that (i.e. check whether) the Pandas DataFrame provided
    satisfies the constraints in the JSON .tdda file provided.

    Mandatory Inputs:

        *df*:
                            A Pandas DataFrame, to be checked.

        *constraints_path*:
                            The path to a JSON .tdda file (possibly
                            generated by the discover_constraints
                            function, below) containing constraints
                            to be checked.

    Optional Inputs:

        *epsilon*:
                            When checking minimum and maximum values
                            for numeric fields, this provides a
                            tolerance. The tolerance is a proportion
                            of the constraint value by which the
                            constraint can be exceeded without causing
                            a constraint violation to be issued.
                            With the default value of epsilon
                            (:py:const:`EPSILON_DEFAULT` = 0.01, i.e. 1%),
                            values can be up to 1% larger than a max constraint
                            without generating constraint failure,
                            and minimum values can be up to 1% smaller
                            that the minimum constraint value without
                            generating a constraint failure. (These
                            are modified, as appropraite, for negative
                            values.)

                            NOTE: A consequence of the fact that these
                            are proportionate is that min/max values
                            of zero do not have any tolerance, i.e.
                            the wrong sign always generates a failure.

        *type_checking*:
                            'strict' or 'sloppy'.
                            Because Pandas silently, routinely and
                            automatically "promotes" integer and boolean
                            columns to reals and objects respectively
                            if they contain nulls, strict type checking
                            can be problematical in Pandas. For this reason,
                            type_checking defaults to 'sloppy', meaning
                            that type changes that could plausibly be
                            attriuted to Pandas type promotion will not
                            generate constraint values.

                            If this is set to strict, a Pandas "float"
                            column c will only be allowed to satisfy a
                            an "int" type constraint if:

                                `c.dropnulls().astype(int) == c.dropnulls()`

                            Similarly, Object fields will satisfy a
                            'bool' constraint only if:

                                `c.dropnulls().astype(bool) == c.dropnulls()`

        *report*:
                            'all' or 'fields'.
                            This controls the behaviour of the
                            :py:meth:`~PandasVerification.__str__` method on
                            the resulting :py:class:`~PandasVerification`
                            object (but not its content).

                            The default is 'all', which means that
                            all fields are shown, together with the
                            verification status of each constraint
                            for that field.

                            If report is set to 'fields', only fields for
                            which at least one constraint failed are shown.

                            NOTE: The method also accepts two further
                            parameters to control (not yet implemented)
                            behaviour. 'constraints', will be used to
                            indicate that only failing constraints for
                            failing fields should be shown.
                            'one_per_line' will indicate that each constraint
                            failure should be reported on a separate line.

    Returns:

        :py:class:`~PandasVerification` object.

        This object has attributes:

            - *passed*      --- Number of passing constriants
            - *failures*    --- Number of failing constraints

        It also has a :py:meth:`~PandasVerification.to_frame()` method for
        converting the results of the verification to a Pandas DataFrame,
        and a :py:meth:`~PandasVerification.__str__` method to print
        both the detailed and summary results of the verification.

    Example usage::

        import pandas as pd
        from tdda.constraints.pdconstraints import verify_df

        df = pd.DataFrame({'a': [0, 1, 2, 10, pd.np.NaN],
                           'b': ['one', 'one', 'two', 'three', pd.np.NaN]})
        v = verify_df(df, 'example_constraints.tdda')

        print('Passes:', v.passes)
        print('Failures: %d\\n' % v.failures)
        print(str(v))
        print(v.to_frame())

    See *simple_verification.py* in the :ref:`constraint_examples`
    for a slightly fuller example.

    """
    pdv = PandasConstraintVerifier(df, epsilon=epsilon,
                                   type_checking=type_checking)
    constraints = DatasetConstraints(loadpath=constraints_path)
    return verify(constraints, pdv.verifiers(),
                  VerificationClass=PandasVerification, **kwargs)


def discover_constraints(df):
    """
    Automatically discover potentially useful constraints that characterize
    the Pandas DataFrame provided.

    Input:

        *df*:
            any Pandas DataFrame.

    Possible return values:

       -  :py:class:`~tdda.constraints.base.DatasetConstraints` object
       -  ``None``    --- (if no constraints were found).

    This function goes through each column in the DataFrame and, where
    appropriate, generates constraints that describe (and are satisified
    by) this dataframe.

    Assuming it generates at least one constraint for at least one field
    it returns a :py:class:`tdda.constraints.base.DatasetConstraints` object.

    This includes a 'fields' attribute, keyed on the column name.

    The returned :py:class:`~tdda.constraints.base.DatasetConstraints` object
    includes a :py:meth:`~tdda.constraints.base.DatasetContraints.to_json`
    method, which converts the constraints into JSON for saving as a tdda
    constraints file. By convention, such JSON files use a '.tdda'
    extension.

    The JSON constraints file can be used to check whether other datasets
    also satisfy the constraints.

    The kinds of constraints (potentially) generated for each field (column)
    are:

        *type*:
                the (coarse, TDDA) type of the field. One of
                'bool', 'int', 'real', 'string' or 'date'.


        *min*:
                for non-string fields, the minimum value in the column.
                Not generated for all-null columns.

        *max*:
                for non-string fields, the maximum value in the column.
                Not generated for all-null columns.

        *min_length*:
                For string fields, the length of the shortest string(s)
                in the field. N.B. In Python3, this is of course,
                a unicode string length; in Python2, it is an encoded
                string length, which may be less meaningful.

        *max_length*:
                For string fields, the length of the longest string(s)
                in the field.  N.B. In Python3, this is of course,
                a unicode string length; in Python2, it is an encoded
                string length, which may be less meaningful.

        *sign*:
                If all the values in a numeric field have consistent sign,
                a sign constraint will be written with a value chosen from:

                    - positive     --- For all values *v* in field: `v > 0`
                    - non-negative --- For all values *v* in field: `v >= 0`
                    - zero         --- For all values *v* in field: `v == 0`
                    - non-positive --- For all values *v* in field: `v <= 0`
                    - negative     --- For all values *v* in field: `v < 0`
                    - null         --- For all values *v* in field: `v is null`

        *max_nulls*:
                The maximum number of nulls allowed in the field.

                    - If the field has no nulls, a constraint
                      will be written with max_nulls set to zero.
                    - If the field has a single null, a constraint will
                      be written with max_nulls set to one.
                    - If the field has more than 1 null, no constraint
                      will be generated.

        *no_duplicates*:
                For string fields (only, for now), if every
                non-null value in the field is different,
                this constraint will be generated (with value ``True``);
                otherwise no constraint will be generated. So this constraint
                indicates that all the **non-null** values in a string
                field are distinct (unique).

        *allowed_values*:
                 For string fields only, if there are
                 :py:const:`MAX_CATEGORIES` or fewer distinct string
                 values in the dataframe, an AllowedValues constraint
                 listing them will be generated.
                 :py:const:`MAX_CATEGORIES` is currently "hard-wired" to 20.

    Example usage::

        import pandas as pd
        from tdda.constraints.pdconstraints import discover_constraints

        df = pd.DataFrame({'a': [1, 2, 3], 'b': ['one', 'two', pd.np.NaN]})
        constraints = discover_constraints(df)
        with open('example_constraints.tdda', 'w') as f:
            f.write(constraints.to_json())

    See *simple_generation.py* in the :ref:`constraint_examples`
    for a slightly fuller example.

    """
    field_constraints = []
    for col in df:
        constraints = discover_field_constraints(df[col])
        if constraints:
            field_constraints.append(constraints)
    if field_constraints:
        return DatasetConstraints(field_constraints)
    else:
        return None
