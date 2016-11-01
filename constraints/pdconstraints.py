# -*- coding: utf-8 -*-
"""
pdconstraints.py: TDDA constraint checking for pandas.
"""
from __future__ import division
from __future__ import print_function

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
MAX_CATEGORIES = 20


if sys.version_info.major >= 3:
    long = int


class PandasConstraintVerifier:
    def __init__(self, df, epsilon=None, type_checking=None):
        self.df = df
        self.epsilon = 0.01 if epsilon is None else epsilon
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
        if self.df[colname].dtype == np.dtype('O'):
            return self.df[colname].dropna().min()  # Otherwise -inf!
        else:
            return self.df[colname].min()

    def get_max(self, colname):
        """Looks up cached maximum of column, or calculates and caches it"""
        return self.get_cached_value('max', colname, self.calc_max)

    def calc_max(self, colname):
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
    def __init__(self, *args, **kwargs):
        Verification.__init__(self, *args, **kwargs)

    def to_frame(self):
        return verification_to_dataframe(self)

    to_dataframe = to_frame


def types_compatible(x, y, colname=None):
    ok = coarse_type(x) == coarse_type(y)
    if not ok and colname:
        print('Warning: Failing incompatible types constraint for field %s '
              'of type %s.\n(Constraint value %s of type %s.)'
              % (colname, type(x), y, type(y)), file=sys.stderr)
    return ok


def coarse_type(x):
    t = tdda_type(x)
    return 'number' if t in ('bool', 'int', 'real') else t


def tdda_type(x):
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


def discover_constraints(df):
    field_constraints = []
    for col in df:
        constraints = discover_field_constraints(df[col])
        if constraints:
            field_constraints.append(constraints)
    if field_constraints:
        return DatasetConstraints(field_constraints)
    else:
        return None


def discover_field_constraints(field):
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
        nNull = field.isnull().sum().astype(int)
        nNonNull = field.notnull().sum().astype(int)
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
                    uniqs = list(field.dropna().unique())   # need them now
                if uniqs:
                    m = min(len(v) for v in uniqs)
                    M = max(len(v) for v in uniqs)
                    min_length_constraint = MinLengthConstraint(m)
                    max_length_constraint = MaxLengthConstraint(M)
            else:
                # Non-string fields all potentially get min and max values
                m = field.min()
                M = field.max()
                if pd.notnull(m):
                    min_constraint = MinConstraint(m)
                if pd.notnull(M):
                    max_constraint = MaxConstraint(M)

                # Non-date fields potentiall get a sign constraint too.
                if min_constraint and max_constraint and type != 'date':
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
                elif pd.isnull(m) and type != 'date':
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


def verify_df(df, constraints_path, epsilon=None, type_checking=None, **kwargs):
    pdv = PandasConstraintVerifier(df, epsilon=epsilon,
                                   type_checking=type_checking)
    constraints = DatasetConstraints(loadpath=constraints_path)
    return verify(constraints, pdv.verifiers(),
                  VerificationClass=PandasVerification, **kwargs)
