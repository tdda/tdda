# -*- coding: utf-8 -*-
"""
TDDA constraint discovery and verification for databases, for supported
DB-API (PEP-0249) compliant databases , and also for a number of other
(NoSQL) databases.

The top-level functions are:

    :py:func:`discover_db_table`:
        Discover constraints from a single database table.

    :py:func:`verify_db_table`:
        Verify (check) a single database table, against a set of previously
        discovered constraints.
"""
from __future__ import division
from __future__ import print_function
from __future__ import absolute_import

import sys

from tdda.constraints.base import (
    verify,
    DatasetConstraints,
    FieldConstraints,
    Verification,
    TypeConstraint,
    MinConstraint, MaxConstraint, SignConstraint,
    MinLengthConstraint, MaxLengthConstraint,
    NoDuplicatesConstraint, MaxNullsConstraint,
    AllowedValuesConstraint, RexConstraint,
)
from tdda.constraints.baseconstraints import (
    BaseConstraintCalculator,
    BaseConstraintVerifier,
    BaseConstraintDiscoverer,
    MAX_CATEGORIES,
)

from tdda.constraints.db.dbbase import DatabaseHandler
from tdda import rexpy


class DatabaseConstraintCalculator(BaseConstraintCalculator):
    def __init__(self, tablename, testing=False):
        self.tablename = tablename
        self.testing = testing

    def is_null(self, value):
        return self.db_value_is_null(value)

    def to_datetime(self, value):
        return self.db_value_to_datetime(value)

    def get_column_names(self):
        return self.get_database_column_names(self.tablename)

    def get_nrecords(self):
        return self.get_database_nrows(self.tablename)

    def types_compatible(self, x, y, colname):
        return types_compatible(x, y, colname if not self.testing else None)

    def calc_min(self, colname):
        return self.get_database_min(self.tablename, colname)

    def calc_max(self, colname):
        return self.get_database_max(self.tablename, colname)

    def calc_min_length(self, colname):
        return self.get_database_min_length(self.tablename, colname)

    def calc_max_length(self, colname):
        return self.get_database_max_length(self.tablename, colname)

    def calc_tdda_type(self, colname):
        return self.get_database_column_type(self.tablename, colname)

    def calc_null_count(self, colname):
        return self.get_database_nnull(self.tablename, colname)

    def calc_non_null_count(self, colname):
        return self.get_database_nnonnull(self.tablename, colname)

    def calc_nunique(self, colname):
        return self.get_database_nunique(self.tablename, colname)

    def calc_unique_values(self, colname, include_nulls=True):
        return self.get_database_unique_values(self.tablename, colname,
                                               include_nulls=include_nulls)

    def calc_non_integer_values_count(self, colname):
        raise Exception('database should not require non_integer_values_count')

    def calc_all_non_nulls_boolean(self, colname):
        raise Exception('database should not require all_non_nulls_boolean')

    def find_rexes(self, colname, values=None):
        if not values:
            values = self.get_database_unique_values(self.tablename, colname)
        return rexpy.extract(values)

    def verify_rex_constraint(self, colname, constraint):
        return self.get_database_rex_match(self.tablename, colname,
                                           constraint.value)


class DatabaseConstraintVerifier(DatabaseConstraintCalculator,
                                 BaseConstraintVerifier, DatabaseHandler):
    """
    A :py:class:`DatabaseConstraintVerifier` object provides methods
    for verifying every type of constraint against a single database table.
    """
    def __init__(self, dbtype, db, tablename, epsilon=None,
                 type_checking='strict', testing=False):
        """
        Inputs:

            *dbtype*:
                    Type of database.
            *db*:
                    A DB-API database connection object (for example, as
                    obtained from a call to pgdb.connect() for PostGreSQL
                    or as a call to MySQLdb.connect() for MySQL).
            *tablename*:
                    A table name, referring to a table that exists in the
                    database and is accessible. It can either be a simple
                    name, or a schema-qualified name of the form `schema.name`.
        """
        DatabaseConstraintCalculator.__init__(self, tablename, testing)
        BaseConstraintVerifier.__init__(self, epsilon=epsilon,
                                        type_checking=type_checking)
        DatabaseHandler.__init__(self, dbtype, db)


class DatabaseVerification(Verification):
    """
    A :py:class:`DatabaseVerification` object is the variant of
    the :py:class:`tdda.constraints.base.Verification` object used for
    verification of constraints on a database table.
    """
    def __init__(self, *args, **kwargs):
        Verification.__init__(self, *args, **kwargs)


class DatabaseConstraintDiscoverer(DatabaseConstraintCalculator,
                                   BaseConstraintDiscoverer,
                                   DatabaseHandler):
    """
    A :py:class:`DatabaseConstraintDiscoverer` object is used to discover
    constraints on a single database table.
    """
    def __init__(self, dbtype, db, tablename, inc_rex=False):
        DatabaseConstraintCalculator.__init__(self, tablename)
        BaseConstraintDiscoverer.__init__(self, inc_rex=inc_rex)
        DatabaseHandler.__init__(self, dbtype, db)
        self.tablename = tablename

    def discover_field_constraints_database_specifically(self, fieldname):
        # TODO: REMOVE THIS, IT'S NOW DONE IN BASE TDDA
        min_constraint = max_constraint = None
        min_length_constraint = max_length_constraint = None
        sign_constraint = no_duplicates_constraint = None
        max_nulls_constraint = allowed_values_constraint = None
        rex_constraint = None

        type_ = self.get_database_column_type(self.tablename, fieldname)
        if type_ == 'other':
            return None         # Unrecognized or complex
        else:
            type_constraint = TypeConstraint(type_)
        length = self.get_database_nrows(self.tablename)

        if length > 0:  # Things are not very interesting when there is no data
            nNull = self.get_database_nnull(self.tablename, fieldname)
            nNonNull = self.get_database_nnonnull(self.tablename, fieldname)
            assert nNull + nNonNull == length
            if nNull < 2:
                max_nulls_constraint = MaxNullsConstraint(nNull)

            # Useful info:
            uniqs = None
            n_unique = -1   # won't equal number of non-nulls later on
            if type_ in ('string', 'int'):
                n_unique = self.get_database_nunique(self.tablename, fieldname)
                if type_ == 'string':
                    if n_unique <= MAX_CATEGORIES:
                        uniqs = self.get_database_unique_values(self.tablename,
                                                                fieldname)
                    if uniqs:
                        avc = AllowedValuesConstraint(uniqs)
                        allowed_values_constraint = avc

            if nNonNull > 0:
                if type_ == 'string':
                    # We don't generate a min, max or sign constraints for
                    # strings. But we do generate min and max length
                    # constraints
                    m = self.get_database_min_length(self.tablename, fieldname)
                    M = self.get_database_max_length(self.tablename, fieldname)
                    min_length_constraint = MinLengthConstraint(m)
                    max_length_constraint = MaxLengthConstraint(M)
                else:
                    # Non-string fields all potentially get min and max values
                    m = self.get_database_min(self.tablename, fieldname)
                    M = self.get_database_max(self.tablename, fieldname)
                    if type_ == 'date':
                        if not self.db_value_is_null(m):
                            m = self.to_datetime(m)
                        if not self.db_value_is_null(M):
                            m = self.to_datetime(M)
                    if not self.db_value_is_null(m):
                        min_constraint = MinConstraint(m)
                    if not self.db_value_is_null(M):
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
                    elif self.db_value_is_null(m) and type_ != 'date':
                        sign_constraint = SignConstraint(None)

            if n_unique == nNonNull and n_unique > 1 and type_ != 'real':
                no_duplicates_constraint = NoDuplicatesConstraint()

            if type_ == 'string' and self.inc_rex:
                if not uniqs:
                    uniqs = self.get_database_unique_values(self.tablename,
                                                            fieldname)
                rex_constraint = RexConstraint(rexpy.extract(uniqs))

        constraints = [c for c in [type_constraint,
                                   min_constraint, max_constraint,
                                   min_length_constraint, max_length_constraint,
                                   sign_constraint, max_nulls_constraint,
                                   no_duplicates_constraint,
                                   allowed_values_constraint,
                                   rex_constraint]
                         if c is not None]
        return FieldConstraints(fieldname, constraints)


def types_compatible(x, y, colname):
    """
    Returns boolean indicating whether the coarse_type of *x* and *y* are
    the same, for scalar values. The int and long types are considered to
    be the same.

    For databases, coarse types are pretty much the same as the column types,
    except that different sizes of integer are all considered to be ints.

    If *colname* is provided, and the check fails, a warning is issued
    to stderr.
    """
    tx = int if type(x) is long else type(x)
    ty = int if type(y) is long else type(y)
    ok = tx == ty
    if not ok and colname:
        print('Warning: Failing incompatible types constraint for field %s '
              'of type %s.\n(Constraint value %s of type %s.)'
              % (colname, type(x), y, type(y)), file=sys.stderr)
    return ok


def verify_db_table(dbtype, db, tablename, constraints_path, epsilon=None,
                    type_checking='strict', testing=False, **kwargs):
    """
    Verify that (i.e. check whether) the database table provided
    satisfies the constraints in the JSON .tdda file provided.

    Mandatory Inputs:

        *dbtype*:
                            Type of database.
        *db*:
                            A database object
        *tablename*:
                            A database table name, to be checked.

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
                            'strict' or 'sloppy'. For databases (unlike
                            Pandas DataFrames), this defaults to 'strict'.

                            If this is set to sloppy, a database "real"
                            column c will only be allowed to satisfy a
                            an "int" type constraint.

        *report*:
                            'all' or 'fields'.
                            This controls the behaviour of the
                            :py:meth:`~DatabaseVerification.__str__`
                            method on the resulting
                            :py:class:`~DatabaseVerification`
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

        *testing*:
                            Boolean flag. Should only be set to ``True``
                            when being run as part of an automated test.
                            It suppresses type-compatibility warnings.

    Returns:

        :py:class:`~DatabaseVerification` object.

        This object has attributes:

            - *passed*      --- Number of passing constriants
            - *failures*    --- Number of failing constraints

    Example usage::

        import pgdb
        from tdda.constraints.dbconstraints import verify_db_table

        dbspec = 'localhost:databasename:username:password'
        tablename = 'schemaname.tablename'
        db = pgdb.connect(dbspec)
        v = verify_db_table('postgres' db, tablename, 'myconstraints.tdda')

        print('Passes:', v.passes)
        print('Failures: %d\\n' % v.failures)
        print(str(v))
        print(v.to_frame())

    """
    dbv = DatabaseConstraintVerifier(dbtype, db, tablename, epsilon=epsilon,
                                     type_checking=type_checking,
                                     testing=testing)
    if not dbv.check_table_exists(tablename):
        print('No table %s' % tablename, file=sys.stderr)
        sys.exit(1)
    constraints = DatasetConstraints(loadpath=constraints_path)
    return verify(constraints, dbv.verifiers(),
                  VerificationClass=DatabaseVerification, **kwargs)


def discover_db_table(dbtype, db, tablename, inc_rex=False):
    """
    Automatically discover potentially useful constraints that characterize
    the database table provided.

    Input:

        *dbtype*:
            Type of database.
        *db*:
            a database object
        *tablename*:
            a table name

    Possible return values:

       -  :py:class:`~tdda.constraints.base.DatasetConstraints` object
       -  ``None``    --- (if no constraints were found).

    This function goes through each column in the table and, where
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

        import pgdb
        from tdda.constraints.dbconstraints import discover_db_table_constraints

        dbspec = 'localhost:databasename:username:password'
        tablename = 'schemaname.tablename'
        db = pgdb.connect(dbspec)
        constraints = discover_db_table_constraints('postgres', db, tablename)

        with open('myconstraints.tdda', 'w') as f:
            f.write(constraints.to_json())

    """
    disco = DatabaseConstraintDiscoverer(dbtype, db, tablename,
                                         inc_rex=inc_rex)
    return disco.discover()


