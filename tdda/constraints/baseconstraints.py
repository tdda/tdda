# -*- coding: utf-8 -*-

"""
TDDA constraint discovery and verification, common underlying functionality.
"""

import datetime
import re
import sys

from collections import OrderedDict

from tdda.constraints.base import (
    PRECISIONS,
    SIGNS,
    STANDARD_FIELD_CONSTRAINTS,
    verify, detect,
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

from tdda.constraints.extension import (BaseConstraintCalculator,
                                        BaseConstraintDetector)

if sys.version_info[0] >= 3:
    unicode_string = str
    byte_string = bytes
    long_type = int
else:
    unicode_string = unicode
    byte_string = str
    long_type = long

DEBUG = False

TYPE_CHECKING_OPTIONS = ('strict', 'sloppy')
DEFAULT_TYPE_CHECKING = 'sloppy'

MAX_CATEGORIES = 20     # String fields with up to 20 categories will
                        # generate AllowedValues constraints


class BaseConstraintVerifier(BaseConstraintCalculator, BaseConstraintDetector):
    """
    The :py:mod:`BaseConstraintVerifier` class provides a generic
    framework for verifying constraints.

    A concrete implementation of this class is constructed by creating
    a mix-in subclass which inherits both from :py:mod:`BaseConstraintVerifier`
    and from specific implementations of :py:mod:`BaseConstraintCalculator`
    and :py:mod:`BaseConstraintDetector`.
    """
    def __init__(self, epsilon=None, type_checking=None, **kwargs):
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

    def verify(self, constraints, VerificationClass=Verification, **kwargs):
        """
        Apply verifiers to a set of constraints, for reporting
        """
        return verify(constraints, self.get_column_names(), self.verifiers(),
                      VerificationClass=VerificationClass,
                      detected_records_writer=self.write_detected_records,
                      **kwargs)

    def detect(self, constraints, VerificationClass=Verification,
               outpath=None, write_all=False, per_constraint=False,
               output_fields=None, index=False, in_place=False,
               rownumber_is_index=True, boolean_ints=False, **kwargs):
        """
        Apply verifiers to a set of constraints, for detection.

        Note that if there is a constraint for a field that does not exist,
        then it fails verification, but there are no records to detect
        against. Similarly if the field exists but the dataset has no
        records.
        """
        return detect(constraints, self.get_column_names(), self.verifiers(),
                      VerificationClass=VerificationClass,
                      detect_outpath=outpath, detect_write_all=write_all,
                      detect_per_constraint=per_constraint,
                      detect_output_fields=output_fields,
                      detect_index=index,
                      detect_in_place=in_place,
                      detected_records_writer=self.write_detected_records,
                      rownumber_is_index=rownumber_is_index,
                      boolean_ints=boolean_ints,
                      **kwargs)

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

    def verify_min_constraint(self, colname, constraint, detect=False):
        """
        Verify whether a given column satisfies the minimum value
        constraint specified.
        """
        if not self.column_exists(colname):
            return False

        value = constraint.value
        precision = getattr(constraint, 'precision', 'fuzzy') or 'fuzzy'
        assert precision in PRECISIONS

        if self.is_null(value):   # a null minimum is not considered to be an
            return True           # active constraint, so is always satisfied

        m = self.get_min(colname)
        if self.is_null(m):       # If there are no values, no value can
            return True           # the minimum constraint

        if (isinstance(value, datetime.datetime)
                or isinstance(value, datetime.date)):
            m = self.to_datetime(m)

        if not self.types_compatible(m, value):
            result = False
        elif (precision == 'closed' or isinstance(value, datetime.datetime)
                                    or isinstance(value, datetime.date)):
            result = m >= value
        elif precision == 'open':
            result = m > value
        else:
            result = fuzzy_greater_than(m, value, self.epsilon)

        if detect and not bool(result):
            self.detect_min_constraint(colname, value, precision, self.epsilon)
        return result

    def verify_max_constraint(self, colname, constraint, detect=False):
        """
        Verify whether a given column satisfies the maximum value
        constraint specified.
        """
        if not self.column_exists(colname):
            return False

        value = constraint.value
        precision = getattr(constraint, 'precision', 'fuzzy') or 'fuzzy'
        assert precision in PRECISIONS

        if self.is_null(value):   # a null maximum is not considered to be an
            return True           # active constraint, so is always satisfied

        M = self.get_max(colname)
        if self.is_null(M):       # If there are no values, no value can
            return True           # the maximum constraint

        if (isinstance(value, datetime.datetime)
                or isinstance(value, datetime.date)):
            M = self.to_datetime(M)

        if not self.types_compatible(M, value):
            result = False
        elif (precision == 'closed' or isinstance(value, datetime.datetime)
                                    or isinstance(value, datetime.date)):
            result = M <= value
        elif precision == 'open':
            result = M < value
        else:
            result = fuzzy_less_than(M, value, self.epsilon)

        if detect and not bool(result):
            self.detect_max_constraint(colname, value, precision, self.epsilon)
        return result

    def verify_min_length_constraint(self, colname, constraint, detect=False):
        """
        Verify whether a given (string) column satisfies the minimum length
        constraint specified.
        """
        if not self.column_exists(colname):
            return False

        value = constraint.value
        if self.is_null(value):   # a null minimum length is not considered
            return True           # to be an active constraint, so is always
                                  # satisfied

        if self.get_tdda_type(colname) != 'string':
            return False

        m = self.get_min_length(colname)
        if self.is_null(m):       # If there are no values, no value can
            return True           # the minimum length constraint

        result = m >= value

        if detect and not bool(result):
            self.detect_min_length_constraint(colname, value)
        return result

    def verify_max_length_constraint(self, colname, constraint, detect=False):
        """
        Verify whether a given (string) column satisfies the maximum length
        constraint specified.
        """
        if not self.column_exists(colname):
            return False

        value = constraint.value
        if self.is_null(value):   # a null minimum length is not considered
            return True           # to be an active constraint, so is always
                                  # satisfied

        if self.get_tdda_type(colname) != 'string':
            return False

        M = self.get_max_length(colname)
        if self.is_null(M):       # If there are no values, no value can
            return True           # the maximum length constraint

        result = M <= value

        if detect and not bool(result):
            self.detect_max_length_constraint(colname, value)
        return result

    def verify_tdda_type_constraint(self, colname, constraint, detect=False):
        """
        Verify whether a given column satisfies the supplied type constraint.
        """
        if not self.column_exists(colname):
            return False

        required_type = constraint.value
        allowed_types = (required_type if type(required_type) in (list, tuple)
                         else [required_type])
        if len(allowed_types) == 1 and self.is_null(allowed_types[0]):
            return True  # a null type is not considered to be an
                         # active constraint, so is always satisfied

        actual_type = self.get_tdda_type(colname)
        if self.type_checking == 'strict':
            result = actual_type in allowed_types
        else:
            if actual_type in allowed_types:
                result = True       # definitely OK if the types actually match
            elif 'int' in allowed_types and actual_type == 'real':
                result = self.get_non_integer_values_count(colname) == 0
            elif 'bool' in allowed_types and actual_type == 'real':
                result = self.get_non_integer_values_count(colname) == 0
            elif 'bool' in allowed_types and actual_type == 'string':
                # boolean columns with nulls get converted to dtype
                # object, which is usually used for strings
                result =  self.get_all_non_nulls_boolean(colname)
            else:
                result = False

        if detect and not bool(result):
            self.detect_tdda_type_constraint(colname, required_type)
        return result

    def verify_sign_constraint(self, colname, constraint, detect=False):
        """
        Verify whether a given column satisfies the supplied sign constraint.
        """
        if not self.column_exists(colname):
            return False

        value = constraint.value
        if self.is_null(value):   # a null value (as opposed to the string
                                  # 'null') is not considered to be an
            return True           # active constraint, so is always satisfied

        m = self.get_min(colname)
        M = self.get_max(colname)
        if self.is_null(m):
            return True  # no values: cannot violate constraint

        if type(m) not in (bool, int, long_type, float):
            result = False
        elif type(M) not in (bool, int, long_type, float):
            result = False
        elif value == 'null':
             result = False
        elif value == 'positive':
            result = m > 0
        elif value == 'non-negative':
            result = m >= 0
        elif value == 'zero':
            result = m == M == 0
        elif value == 'non-positive':
            result = M <= 0
        elif value == 'negative':
            result = M < 0
        assert value in SIGNS

        if detect and not bool(result):
            self.detect_sign_constraint(colname, value)
        return result

    def verify_max_nulls_constraint(self, colname, constraint, detect=False):
        """
        Verify whether a given column satisfies the supplied constraint
        that it should contain no nulls.
        """
        if not self.column_exists(colname):
            return False

        value = constraint.value
        if self.is_null(value):   # a null value is not considered to be an
            return True           # active constraint, so is always satisfied
        result = self.get_null_count(colname) <= value

        if bool(result) or not detect:
            return result
        self.detect_max_nulls_constraint(colname, value)
        return False

    def verify_no_duplicates_constraint(self, colname, constraint,
                                        detect=False):
        """
        Verify whether a given column satisfies the constraint supplied,
        that it should contain no duplicate (non-null) values.
        """
        if not self.column_exists(colname):
            return False

        value = constraint.value
        if value is False or self.is_null(value):
            # a null value is not considered to be an active constraint,
            # so is always satisfied
            return True

        assert value == True      # value not really used; but should be True

        non_nulls = self.get_non_null_count(colname)
        result = self.get_nunique(colname) == non_nulls

        if detect and not bool(result):
            self.detect_no_duplicates_constraint(colname, value)
        return result

    def verify_allowed_values_constraint(self, colname, constraint,
                                         detect=False):
        """
        Verify whether a given column satisfies the constraint on allowed
        (string) values provided.
        """
        if not self.column_exists(colname):
            return False

        exclusions = self.allowed_values_exclusions()
        allowed_values = constraint.value
        if allowed_values is None:      # a null value is not considered
            return True                 # to be an active constraint,
                                        # so is always satisfied

        n_allowed_values = len(allowed_values)
        n_actual_values = self.get_nunique(colname)

        if not detect and n_actual_values > n_allowed_values:
            # can know the result without actually identifying values
            result = False
        else:
            actual_values = self.get_unique_values(colname)
            exclusions = exclusions or []

            violations = (set(actual_values) - set(allowed_values)
                                             - set(exclusions))
            result = len(violations) == 0

        if detect and not bool(result):
            self.detect_allowed_values_constraint(colname, allowed_values,
                                                  violations)
        return result

    def verify_rex_constraint(self, colname, constraint, detect=False):
        """
        Verify whether a given column satisfies a given regular
        expression constraint (by matching at least one of the regular
        expressions given).
        """
        if not self.column_exists(colname):
            return False
        if self.get_tdda_type(colname) != 'string':
            return False

        violations = self.calc_rex_constraint(colname, constraint,
                                              detect=detect)
        if bool(violations):
            # a truthy result means some values failed the constraint
            if detect:
                self.detect_rex_constraint(colname, violations)
            return False
        else:
            return True

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


class BaseConstraintDiscoverer(BaseConstraintCalculator):
    """
    The :py:mod:`BaseConstraintDiscoverer` class provides a generic
    framework for discovering constraints.

    A concrete implementation of this class is constructed by creating
    a mix-in subclass which inherits both from :py:mod:`BaseConstraintDiscover`
    and from a specific implementation of :py:mod:`BaseConstraintCalculator`.
    """
    def __init__(self, inc_rex=False, seed=None, **kwargs):
        self.inc_rex = inc_rex
        self.seed = seed

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
        min_constraint = max_constraint = None
        min_length_constraint = max_length_constraint = None
        sign_constraint = no_duplicates_constraint = None
        max_nulls_constraint = allowed_values_constraint = None
        rex_constraint = None

        type_ = self.calc_tdda_type(fieldname)
        if type_ == 'other':
            return None         # Unrecognized or complex
        else:
            type_constraint = TypeConstraint(type_)
        length = self.get_nrecords()

        if length > 0:  # Things are not very interesting when there is no data
            nNull = self.calc_null_count(fieldname)
            nNonNull = self.calc_non_null_count(fieldname)
            assert nNull + nNonNull == length
            if nNull < 2:
                max_nulls_constraint = MaxNullsConstraint(nNull)

            # Useful info:
            uniqs = None
            n_unique = -1   # won't equal number of non-nulls later on
            if type_ in ('string', 'int'):
                n_unique = self.calc_nunique(fieldname)
                if type_ == 'string':
                    if n_unique <= MAX_CATEGORIES:
                        uniqs = self.calc_unique_values(fieldname,
                                                        include_nulls=False)
                    if uniqs:
                        avc = AllowedValuesConstraint(uniqs)
                        allowed_values_constraint = avc

            if nNonNull > 0:
                if type_ == 'string':
                    # We don't generate a min, max or sign constraints for
                    # strings. But we do generate min and max length
                    # constraints
                    if (uniqs is None and n_unique > 0):
                        # There were too many for us to have bothered getting
                        # them all before, but we need them now.
                        uniqs = self.calc_unique_values(fieldname,
                                                        include_nulls=False)
                    if uniqs:
                        if type(uniqs[0]) is unicode_string:
                            L = [len(v) for v in uniqs]
                        else:
                            L = [len(v.decode('UTF-8')) for v in uniqs]
                        m = min(L)
                        M = max(L)
                        min_length_constraint = MinLengthConstraint(m)
                        max_length_constraint = MaxLengthConstraint(M)
                else:
                    # Non-string fields all potentially get min and max values
                    m = self.calc_min(fieldname)
                    M = self.calc_max(fieldname)
                    if not self.is_null(m):
                        min_constraint = MinConstraint(m)
                    if not self.is_null(M):
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
                    elif self.is_null(m) and type_ != 'date':
                        sign_constraint = SignConstraint('null')

            if n_unique == nNonNull and n_unique > 1 and type_ != 'real':
                # all values are unique
                no_duplicates_constraint = NoDuplicatesConstraint()

        if type_ == 'string' and self.inc_rex:
            rex_constraint = RexConstraint(self.find_rexes(fieldname,
                                                           values=uniqs,
                                                           seed=self.seed))

        constraints = [c for c in [type_constraint,
                                   min_constraint, max_constraint,
                                   min_length_constraint,
                                   max_length_constraint,
                                   sign_constraint, max_nulls_constraint,
                                   no_duplicates_constraint,
                                   allowed_values_constraint,
                                   rex_constraint]
                         if c is not None]
        return FieldConstraints(fieldname, constraints)
