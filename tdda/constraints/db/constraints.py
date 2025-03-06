# -*- coding: utf-8 -*-
"""
TDDA constraint discovery and verification is provided for a number
of DB-API (PEP-0249) compliant databases, and also for a number of other
(NoSQL) databases.

The top-level functions are:

    :py:func:`tdda.constraints.discover_db_table`:
        Discover constraints from a single database table.

    :py:func:`tdda.constraints.verify_db_table`:
        Verify (check) a single database table, against a set of previously
        discovered constraints.

    :py:func:`tdda.constraints.detect_db_table`:
        For detection of failing records in a single database table,
        but not yet implemented for databases.

"""
import sys

from tdda.constraints.base import (
    DatasetConstraints,
    Verification,
    constraints_from_path_or_dict,
)
from tdda.constraints.baseconstraints import (
    BaseConstraintCalculator,
    BaseConstraintDetector,
    BaseConstraintVerifier,
    BaseConstraintDiscoverer,
    MAX_CATEGORIES,
)

from tdda.constraints.db.drivers import DatabaseHandler
from tdda.utils import squote
from tdda import rexpy


if sys.version_info[0] >= 3:
    long = int


SIGN_OP = {
    'positive': '>',
    'non-negative': '>=',
    'zero': '==',
    'non-positive': '<=',
    'negative': '<',
}

BAD_SIGN_OP = {
    'positive': '<=',
    'non-negative': '<',
    'zero': '!=',
    'non-positive': '>',
    'negative': '>=',
}


class DatabaseConstraintCalculator(BaseConstraintCalculator):
    def __init__(self, tablename, testing=False):
        self.tablename = tablename
        self.testing = testing

    def is_null(self, value):
        return self.db_value_is_null(value)

    def to_datetime(self, value):
        return self.db_value_to_datetime(value)

    def column_exists(self, colname):
        return colname in self.get_column_names()

    def get_column_names(self):
        return self.get_database_column_names(self.tablename)

    def get_nrecords(self):
        return self.get_database_nrows(self.tablename)

    def types_compatible(self, x, y, colname=None):
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

    def find_rexes(self, colname, values=None, seed=None):
        if not values:
            values = self.get_database_unique_values(self.tablename, colname)
        return rexpy.extract(sorted(values), seed=seed, tag=self.group_rexes)

    def calc_rex_constraint(self, colname, constraint, detect=False):
        return not self.get_database_rex_match(self.tablename, colname,
                                               constraint.value)


class DatabaseConstraintDetector(BaseConstraintDetector,
                                 DatabaseHandler):
    """
    """
    def __init__(self, dbtype, dbc, tablename,
                 epsilon=None, type_checking='strict', **kwargs):
        DatabaseHandler.__init__(self, dbtype, dbc)
        self.dbtype = dbtype
        self.source_table = self.resolve_table(tablename)
        self.detect_passes = True  # False for _bad fields
        self.out_field_suffix = 'ok' if self.detect_passes else 'bad'
        self.interleave = True
        self.n_failures_field = 'n_failures'

    def detect(self, constraints, dest_pair, execute=True):
        dest_name, dest_dbtype = dest_pair
        dest_name = self.quoted(self.resolve_table(dest_name))
        if dest_dbtype != self.dbtype:
            raise Exception('Detect from RDBMS currently only supports'
                            'writing to same RDBMS.')
        self.drop_table_if_exists(dest_name)
        exprs = [] if self.interleave else [
            self.quoted(field) for f in constraints.fields
        ]
        detection_fields = []
        for fc in constraints.fields.values():
            if self.interleave:
                exprs.append(self.quoted(fc.name))
            exprs.extend(self.detection_field_expressions(fc))
            detection_fields.extend(self.detection_field_names(fc))
        n_failures_field = self.failures_field(detection_fields)
        exprstr = ',\n'.join(exprs)
        sql = f'''
CREATE TABLE {dest_name}
AS
WITH BASE AS (
    SELECT {indent(exprstr, 11)}
    FROM {self.source_table}
)
SELECT *,
       {n_failures_field}
FROM BASE
'''.strip()
        if execute:
            self.execute_commit(sql)
            return f'{dest_name} created'
        else:
            return sql


    def detection_field_expressions(self, fc):
        detect_field = (
            self.detect_ok_field
            if self.detect_passes
            else self.detect_bad_field
        )
        return [
            detect_field(fc.name, cname, c)
            for cname, c in fc.constraints.items()
        ]

    def detection_field_names(self, fc):
        return [
            self.quoted(self.out_field_name(fc.name, kind))
            for kind in fc.constraints
        ]

    def failures_field(self, out_fields):
        if self.detect_passes:
            joint = '\n          + '
            return (
                str(len(out_fields))
              + '\n       - ('
              + (joint.join(f'{self.cast_bool_to_int(field)}'
                     for field in out_fields))
              + f'\n        ) AS {self.n_failures_field}'
            )
        else:
            joint = '\n       + '
            return (
                (joint.join(f'{field}::INT' for field in out_fields))
                + f'\nAS {self.n_failures_field}'
            )

    def detect_ok_field(self, field, kind, constraint):
        outname = self.quoted(self.out_field_name(field, kind))
        field = self.quoted(field)
        val = constraint.value
        a = lambda s: f'{s} AS {outname}'
        ornull = f'OR {field} IS NULL)'
        mm_op = '<=' if 'max' in kind else '>=' if 'min' in kind else None
        if kind == 'type':
            return a('true')
        if kind in ('min', 'max'):
            return (
                a(f'({field} {mm_op} {val} {ornull}')
            )
        if kind in ('min_length', 'max_length'):
            return (
                a(f'(LENGTH({field}) {mm_op} {val} {ornull}')
            )
        if kind == 'sign':
            op = SIGN_OP.get(val, None)
            return (
                a(f'({field} {op} 0 {ornull}')
            )
        if kind == 'max_nulls':
            if val > 0:
                maxcond = f'((COUNT(*) OVER ()) <= {val}) OR '
            else:
                maxcond = ''
            return a(
                f'({maxcond}{field} IS NOT NULL)'
            )
        if kind == 'no_duplicates':
            return a(f'(((COUNT(*) OVER (PARTITION BY {field})) = 1) {ornull}')
        if kind == 'allowed_values':
            return a(f"({field} IN ({', '.join(squote(x) for x in val)}) "
                     f"{ornull}")
        if kind == 'rex':
            rex_sql = rex_match_sql(field, v)
            if rex_sql:
                return a(f'{rex_sql} {ornull}')
            else:
                return 'true'
        raise Exception(f'Internal error: unknown constraint: {kind}')

    def detect_bad_field(self, field, kind, constraint):
        outname = self.quoted(self.out_field_name(field, kind))
        field = self.quoted(field)
        val = constraint.value
        a = lambda s: f'{s} AS {outname}'
        andnn = f'AND {field} IS NOT NULL)'
        mm_op = '>' if 'max' in kind else '<' if 'min' in kind else None
        if kind == 'type':
            return a('false')
        if kind in ('min', 'max'):
            return (
                a(f'(({field} {mm_op} {val}) {andnn}')
            )
        if kind in ('min_length', 'max_length'):
            return (
                a(f'((LENGTH({field}) {mm_op} {val}) {andnn}')
            )
        if kind == 'sign':
            op = BAD_SIGN_OP.get(val, None)
            return (
                a(f'(({field} {op} 0) {andnn}')
            )
        if kind == 'max_nulls':
            if val > 0:
                maxcond = f'((COUNT(*) OVER (PARTITION BY 1)) > {val}) AND '
            else:
                maxcond = ''
            return a(
                f'({maxcond}{field} IS NULL)'
            )
        if kind == 'no_duplicates':
            return a(f'(((COUNT(*) OVER (PARTITION BY {field})) > 1) {andnn}')
        if kind == 'allowed_values':
            return a(f"({field} NOT IN ({', '.join(squote(x) for x in val)})"
                     f"{andnn}"   )
        if kind == 'rex':
            rex_sql = rex_match_sql(field, v)
            if rex_sql:
                return a(f'{rex_sql} {andnn}')
            else:
                return 'false'
        raise Exception(f'Internal error: unknown constraint: {kind}')

    def out_field_name(self, field, kind):
        return f'{field}_{kind}_{self.out_field_suffix}'


class DatabaseConstraintVerifier(DatabaseConstraintCalculator,
                                 DatabaseConstraintDetector,
                                 BaseConstraintVerifier,
                                 DatabaseHandler):
    """
    A :py:class:`DatabaseConstraintVerifier` object provides methods
    for verifying every type of constraint against a single database table.
    """
    def __init__(self, dbtype, dbc, source_table,
                 epsilon=None, type_checking='strict', testing=False):
        """
        Inputs:

            *dbtype*:
                    Type of database.
            *dbc*:
                    A DB-API database connection object (as obtained from
                    a call to the connect() method on the underlying database
                    driver).
            *tablename*:
                    A table name, referring to a table that exists in the
                    database and is accessible. It can either be a simple
                    name, or a schema-qualified name of the form `schema.name`.
        """
        DatabaseHandler.__init__(self, dbtype, dbc)
        source_table = self.resolve_table(source_table)

        DatabaseConstraintCalculator.__init__(self, source_table, testing)
        DatabaseConstraintDetector.__init__(self, dbtype, dbc, source_table)
        BaseConstraintVerifier.__init__(self, epsilon=epsilon,
                                        type_checking=type_checking)


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
    def __init__(self, dbtype, dbc, tablename, inc_rex=False, seed=None):
        DatabaseHandler.__init__(self, dbtype, dbc)
        tablename = self.resolve_table(tablename)

        DatabaseConstraintCalculator.__init__(self, tablename)
        BaseConstraintDiscoverer.__init__(self, inc_rex=inc_rex, seed=seed)
        self.tablename = tablename


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
                    type_checking='strict', testing=False, report='all',
                    **kwargs):
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

                            For example, with epsilon set to 0.01 (i.e. 1%),
                            values can be up to 1% larger than a max constraint
                            without generating constraint failure,
                            and minimum values can be up to 1% smaller
                            that the minimum constraint value without
                            generating a constraint failure. (These
                            are modified, as appropriate, for negative
                            values.)

                            If not specified, an *epsilon* of 0 is used,
                            so there is no tolerance.

                            NOTE: A consequence of the fact that these
                            are proportionate is that min/max values
                            of zero do not have any tolerance, i.e.
                            the wrong sign always generates a failure.

        *type_checking*:
                            ``strict`` or ``sloppy``. For databases (unlike
                            Pandas DataFrames), this defaults to 'strict'.

                            If this is set to sloppy, a database "real"
                            column c will only be allowed to satisfy a
                            an "int" type constraint.

        *report*:
                            ``all`` or ``fields``.
                            This controls the behaviour of the
                            :py:meth:`~~tdda.constraints.db.constraints.DatabaseVerification.__str__`
                            method on the resulting
                            :py:class:`~tdda.constraints.db.constraints.DatabaseVerification`
                            object (but not its content).

                            The default is ``all``, which means that
                            all fields are shown, together with the
                            verification status of each constraint
                            for that field.

                            If report is set to ``fields``, only fields for
                            which at least one constraint failed are shown.

        *testing*:
                            Boolean flag. Should only be set to ``True``
                            when being run as part of an automated test.
                            It suppresses type-compatibility warnings.

    Returns:

        :py:class:`~tdda.constraints.db.constraints.DatabaseVerification` object.

        This object has attributes:

        - *passed*      --- Number of passing constriants
        - *failures*    --- Number of failing constraints

    Example usage::

        import pgdb
        from tdda.constraints import verify_db_table

        dbspec = 'localhost:databasename:username:password'
        tablename = 'schemaname.tablename'
        db = pgdb.connect(dbspec)
        v = verify_db_table('postgres' db, tablename, 'myconstraints.tdda')

        print('Constraints passing:', v.passes)
        print('Constraints failing: %d\\n' % v.failures)
        print(str(v))
    """
    dbv = DatabaseConstraintVerifier(dbtype, db, tablename, epsilon=epsilon,
                                     type_checking=type_checking,
                                     testing=testing)
    if not dbv.table_exists(tablename):
        print('No table %s' % tablename, file=sys.stderr)
        sys.exit(1)
    constraints = DatasetConstraints(loadpath=constraints_path)
    return dbv.verify(constraints,
                      VerificationClass=DatabaseVerification,
                      report=report, **kwargs)


def detect_db_table(dbtype, dbc, tablename, constraints_path, destination,
                    epsilon=None, type_checking='strict', testing=False,
                    **kwargs):
    """
    For detection of failures from verification of constraints, but
    not yet implemented for database tables.
    """
    detector = DatabaseConstraintDetector(
        dbtype, dbc, tablename, epsilon=epsilon,
        type_checking=type_checking,
        **kwargs
    )
    constraints = constraints_from_path_or_dict(constraints_path)
    return detector.detect(constraints, destination)



def discover_db_table(dbtype, dbc, tablename, inc_rex=False, seed=None):
    """
    Automatically discover potentially useful constraints that characterize
    the database table provided.

    Input:

        *dbtype*:
            Type of database.
        *db*:
            a database connection object
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
                in the field.

        *max_length*:
                For string fields, the length of the longest string(s)
                in the field.

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

    Regular Expression constraints are not (currently) generated for fields
    in database tables.

    Example usage::

        import pgdb
        from tdda.constraints import discover_db_table

        dbspec = 'localhost:databasename:username:password'
        tablename = 'schemaname.tablename'
        db = pgdb.connect(dbspec)
        constraints = discover_db_table('postgres', db, tablename)

        with open('myconstraints.tdda', 'w') as f:
            f.write(constraints.to_json())

    """
    disco = DatabaseConstraintDiscoverer(dbtype, dbc, tablename,
                                         inc_rex=inc_rex, seed=seed)
    if not disco.table_exists(tablename):
        print('No table %s' % tablename, file=sys.stderr)
        sys.exit(1)
    constraints = disco.discover()
    if constraints:
        nrows = disco.get_nrows(tablename)
        constraints.set_stats(n_records=nrows, n_selected=nrows)
        constraints.set_dates_user_host_creator()
        constraints.set_rdbms('%s:%s:%s:%s' % (dbtype or '', dbc.host or '',
                                               dbc.user, dbc.database))
        constraints.set_source(tablename, tablename)
    return constraints

def indent(s, indentation):
    joint = '\n' + ' ' * indentation
    return joint.join(s.splitlines())
