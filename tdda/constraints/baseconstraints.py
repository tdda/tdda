# -*- coding: utf-8 -*-
"""
TDDA constraint discovery and verification, common underlying functionality.

API
---

"""
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import datetime
import re
import sys

from collections import OrderedDict

from tdda.constraints.base import (
    PRECISIONS,
    SIGNS,
    STANDARD_FIELD_CONSTRAINTS,
    verify,
    native_definite,
    DatasetConstraints,
    FieldConstraints,
    Verification,
    TypeConstraint,
    MinConstraint, MaxConstraint, SignConstraint,
    MinLengthConstraint, MaxLengthConstraint,
    NoDuplicatesConstraint, MaxNullsConstraint,
    AllowedValuesConstraint, RexConstraint,
    EPSILON_DEFAULT,
    fuzzy_greater_than, fuzzy_less_than
)
DEBUG = False

TYPE_CHECKING_OPTIONS = ('strict', 'sloppy')
DEFAULT_TYPE_CHECKING = 'sloppy'

MAX_CATEGORIES = 20     # String fields with up to 20 categories will
                        # generate AllowedValues constraints


class BaseConstraintCalculator:
    """
    These are all of the methods that need to be overridden in order
    to implement a constraint discoverer or verifier.
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
        raise NotImplementedError('min')

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
        Calculates the number of nulls in a columns
        """
        raise NotImplementedError('null_count')

    def calc_non_null_count(self, colname):
        """
        Calculates the number of nulls in a columns
        """
        raise NotImplementedError('non_null_count')

    def calc_nunique(self, colname):
        """
        Calculates the number of unique non-null values in a columns
        """
        raise NotImplementedError('nunique')

    def calc_unique_values(self, colname):
        """
        Calculates the set of unique non-null values in a columns
        """
        raise NotImplementedError('unique_values')

    def calc_non_integer_values_count(self, colname):
        """
        Calculates the number of unique non-integer values in a columns
        """
        raise NotImplementedError('non_integer_values_count')

    def calc_all_non_nulls_boolean(self, colname):
        """
        Checks whether all the non-null values in a column are boolean.
        Returns True of they are, and False otherwise.
        """
        raise NotImplementedError('all_non_nulls_boolean')

    def calc_rex_constraint(self, colname, constraint):
        """
        Verify whether a given column satisfies a given regular
        expression constraint (by matching at least one of the regular
        expressions given).
        """
        raise NotImplementedError('rex')


class BaseConstraintVerifier(BaseConstraintCalculator):
    def __init__(self, epsilon=None, type_checking=None):
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
            'rex': self.verify_rex_constraint,
        }

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

    def verify_min_constraint(self, colname, constraint):
        """
        Verify whether a given column satisfies the minimum value
        constraint specified.
        """
        value = constraint.value
        precision = getattr(constraint, 'precision', 'closed') or 'closed'
        assert precision in PRECISIONS

        if self.is_null(value):   # a null minimum is not considered to be an
            return True           # active constraint, so is always satisfied

        m = self.get_min(colname)
        if self.is_null(m):       # If there are no values, no value can
            return True           # the minimum constraint

        if isinstance(value, datetime.datetime):
            m = self.to_datetime(m)
        if not self.types_compatible(m, value, colname):
            return False

        if precision == 'closed':
            return m >= value
        elif precision == 'open':
            return m > value
        else:
            return fuzzy_greater_than(m, value, self.epsilon)

    def verify_max_constraint(self, colname, constraint):
        """
        Verify whether a given column satisfies the maximum value
        constraint specified.
        """
        value = constraint.value
        precision = getattr(constraint, 'precision', 'closed') or 'closed'
        assert precision in ('open', 'closed', 'fuzzy')

        if self.is_null(value):   # a null maximum is not considered to be an
            return True           # active constraint, so is always satisfied

        M = self.get_max(colname)
        if self.is_null(M):       # If there are no values, no value can
            return True           # the maximum constraint

        if isinstance(value, datetime.datetime):
            M = self.to_datetime(M)
        if not self.types_compatible(M, value, colname):
            return False

        if precision == 'closed':
            return M <= value
        elif precision == 'open':
            return M < value
        else:
            return fuzzy_less_than(M, value, self.epsilon)

    def verify_min_length_constraint(self, colname, constraint):
        """
        Verify whether a given (string) column satisfies the minimum length
        constraint specified.
        """
        value = constraint.value

        if self.is_null(value):   # a null minimum length is not considered
            return True           # to be an active constraint, so is always
                                  # satisfied

        m = self.get_min_length(colname)
        if self.is_null(m):       # If there are no values, no value can
            return True           # the minimum length constraint

        return m >= value

    def verify_max_length_constraint(self, colname, constraint):
        """
        Verify whether a given (string) column satisfies the maximum length
        constraint specified.
        """
        value = constraint.value

        if self.is_null(value):   # a null minimum length is not considered
            return True           # to be an active constraint, so is always
                                  # satisfied

        M = self.get_max_length(colname)
        if self.is_null(M):       # If there are no values, no value can
            return True           # the maximum length constraint

        return M <= value

    def verify_tdda_type_constraint(self, colname, constraint):
        """
        Verify whether a given column satisfies the supplied type constraint.
        """
        required_type = constraint.value
        allowed_types = (required_type if type(required_type) in (list, tuple)
                         else [required_type])
        if len(allowed_types) == 1 and self.is_null(allowed_types[0]):
            return True  # a null type is not considered to be an
                         # active constraint, so is always satisfied

        actual_type = self.get_tdda_type(colname)
        if self.type_checking == 'strict':
            return actual_type in allowed_types
        else:
            if actual_type in allowed_types:
                return True       # definitely OK of the types actually match
            elif 'int' in allowed_types and actual_type == 'real':
                return self.get_non_integer_values_count(colname) == 0
            elif 'bool' in allowed_types and actual_type == 'real':
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
        if self.is_null(value):   # a null value (as opposed to the string
                                  # 'null') is not considered to be an
            return True           # active constraint, so is always satisfied

        m = self.get_min(colname)
        M = self.get_max(colname)
        if self.is_null(m):
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
        if self.is_null(value):   # a null value is not considered to be an
            return True           # active constraint, so is always satisfied
        return self.get_null_count(colname) <= value

    def verify_no_duplicates_constraint(self, colname, constraint):
        """
        Verify whether a given column satisfies the constraint supplied,
        that it should contain no duplicate (non-null) values.
        """
        value = constraint.value
        if self.is_null(value):   # a null value is not considered to be an
            return True           # active constraint, so is always satisfied

        assert value == True      # value not really used; but should be True

        non_nulls = self.get_non_null_count(colname)
        return self.get_nunique(colname) == non_nulls

    def verify_allowed_values_constraint(self, colname, constraint):
        """
        Verify whether a given column satisfies the constraint on allowed
        (string) values provided.
        """
        exclusions = self.allowed_values_exclusions()
        allowed_values = constraint.value
        if allowed_values is None:      # a null value is not considered
            return True                 # to be an active constraint,
                                        # so is always satisfied

        n_allowed_values = len(allowed_values)
        n_actual_values = self.get_nunique(colname)

        if n_actual_values > n_allowed_values:
            return False

        actual_values = self.get_unique_values(colname)
        exclusions = exclusions or []

        violations = set(actual_values) - set(allowed_values) - set(exclusions)
        return len(violations) == 0

    def verify_rex_constraint(self, colname, constraint):
        """
        Verify whether a given column satisfies a given regular
        expression constraint (by matching at least one of the regular
        expressions given).
        """
        return self.calc_rex_constraint(colname, constraint)

    def get_min(self, colname):
        """Looks up cached minimum of column, or calculates and caches it"""
        return self.get_cached_value('min', colname, self.calc_min)

    def get_max(self, colname):
        """Looks up cached maximum of column, or calculates and caches it"""
        return self.get_cached_value('max', colname, self.calc_max)

    def get_min_length(self, colname):
        """
        Looks up cached minimum string length in column,
        or calculates and caches it
        """
        return self.get_cached_value('min_length', colname,
                                     self.calc_min_length)

    def get_max_length(self, colname):
        """
        Looks up cached maximum string length in column,
        or calculates and caches it
        """
        return self.get_cached_value('max_length', colname,
                                     self.calc_max_length)

    def get_tdda_type(self, colname):
        """
        Looks up cached tdda type of a column,
        or calculates and caches it
        """
        return self.get_cached_value('tdda_type', colname, self.calc_tdda_type)

    def get_null_count(self, colname):
        """
        Looks up or caches the number of nulls in a column,
        or calculates and caches it
        """
        return self.get_cached_value('null_count', colname,
                                     self.calc_null_count)

    def get_non_null_count(self, colname):
        """
        Looks up or caches the number of non-null values in a column,
        or calculates and caches it
        """
        return self.get_cached_value('non_null_count', colname,
                                     self.calc_non_null_count)

    def get_nunique(self, colname):
        """
        Looks up or caches the number of unique (distinct) values in a column,
        or calculates and caches it.
        """
        return self.get_cached_value('nunique', colname, self.calc_nunique)

    def get_unique_values(self, colname):
        """
        Looks up or caches the list of unique (distinct) values in a column,
        or calculates and caches it.
        """
        return self.get_cached_value('uniques', colname,
                                     self.calc_unique_values)

    def get_non_integer_values_count(self, colname):
        """
        Looks up or caches the number of non-integer values in a real column,
        or calculates and caches it.
        """
        return self.get_cached_value('non_integer_values_count', colname,
                                     self.calc_non_integer_values_count)

    def get_all_non_nulls_boolean(self, colname):
        """
        Looks up or caches the number of non-integer values in a real column,
        or calculates and caches it.
        """
        return self.get_cached_value('all_non_nulls_boolean', colname,
                                     self.calc_all_non_nulls_boolean)


class BaseConstraintDiscoverer:
    """
    A :py:class:`BaseConstraintDiscoverer` object is used to discover
    constraints.

    It needs to do the same calculations as a BaseConstraintCalculator,
    but it isn't just a matter of providing override definitions for all
    of those methods. Instead, you need to override two methods:
        - get_column_names
        - discover_field_constraints
    """
    def __init__(self, inc_rex=False):
        self.inc_rex = inc_rex

    def get_column_names(self):
        """
        Returns a list containing the names of all the columns
        """
        raise NotImplementedError('get_column_names')

    def discover(self):
        field_constraints = []
        for col in self.get_column_names():
            constraints = self.discover_field_constraints(col)
            if constraints:
                field_constraints.append(constraints)
        if field_constraints:
            return DatasetConstraints(field_constraints)
        else:
            return None

    def discover_field_constraints(self, fieldname):
        """
        Discover constraints for a single field (column).

        Input:

            *fieldname*:
                a single field name, which must exist.

        Returns:

            - :py:class:`tdda.base.FieldConstraints` object,
              if any constraints were found.
            - ``None``, otherwise.

        """
        raise NotImplementedError('discover_field_constraints')

