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
    FieldConstraints,
    Verification,
    constraints_from_path_or_dict,
    CONSTRAINT_SUFFIX_MAP,
    PassFailCount,
)
from tdda.constraints.baseconstraints import (
    BaseConstraintCalculator,
    BaseConstraintDetector,
    BaseConstraintVerifier,
    BaseConstraintDiscoverer,
    MAX_CATEGORIES,
)

from tdda.constraints.db.drivers import DatabaseHandler
from tdda.state import get_config
from tdda.utils import (
    squote,
    remove_falsy_values,
    indicator_field_name,
    pass_fail_stats,
    OK,
    BAD,
    TDDAError,
)
from tdda import rexpy


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
        self.n_source_records = self.get_database_nrows(self.tablename)
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
        return self.get_database_unique_values(
            self.tablename, colname, include_nulls=include_nulls
        )

    def calc_non_integer_values_count(self, colname):
        raise TDDAError('database should not require non_integer_values_count')

    def calc_all_non_nulls_boolean(self, colname):
        raise TDDAError('database should not require all_non_nulls_boolean')

    def find_rexes(self, colname, values=None, seed=None):
        if not values:
            values = self.get_database_unique_values(self.tablename, colname)
        return rexpy.extract(sorted(values), seed=seed, tag=self.group_rexes)

    def calc_rex_constraint(self, colname, constraint, detect=False):
        return not self.get_database_rex_match(
            self.tablename, colname, constraint.value
        )


class DatabaseConstraintVerifier(
    DatabaseConstraintCalculator, BaseConstraintVerifier, DatabaseHandler
):
    """
    A :py:class:`DatabaseConstraintVerifier` object provides methods
    for verifying every type of constraint against a single database table.
    """

    def __init__(
        self,
        dbtype,
        dbc,
        source_table,
        epsilon=None,
        type_checking='strict',
        testing=False,
    ):
        """
        Args:
            dbtype: Type of database.
            dbc: A DB-API database connection object (as obtained from
                a call to the ``connect()`` method on the underlying
                database driver).
            source_table: A table name referring to a table that exists
                in the database and is accessible. Can be a simple name
                or a schema-qualified name of the form ``schema.name``.
        """
        DatabaseHandler.__init__(self, dbtype, dbc)
        source_table = self.resolve_table(source_table)

        DatabaseConstraintCalculator.__init__(self, source_table, testing)
        BaseConstraintVerifier.__init__(
            self, epsilon=epsilon, type_checking=type_checking
        )


class DatabaseConstraintDetector(
    DatabaseConstraintVerifier, BaseConstraintDetector
):
    """ """

    def __init__(
        self,
        dbtype,
        dbc,
        tablename,
        epsilon=None,
        type_checking='strict',
        config=None,
        **kwargs,
    ):
        DatabaseConstraintVerifier.__init__(self, dbtype, dbc, tablename)
        config = get_config(config)
        cconfig = config.constraints
        self.dbtype = dbtype
        self.source_table = self.resolve_table(tablename, quote=True)
        self.n_source_records = self.get_database_nrows(self.source_table)
        self.detect_passes = True  # False for _bad fields
        self.out_field_suffix = OK if self.detect_passes else BAD
        self.interleave = cconfig.get('interleave', kwargs)
        self.per_constraint = cconfig.get('per_constraint', kwargs)
        self.report_formats = cconfig.get('report_formats', kwargs)
        self.write_all_records = cconfig.get('write_all_records', kwargs)
        self.n_failures_field = 'n_failures'

    def detect(self, constraints, dest_pair, execute=True, **kwargs):
        ver = self.verify(
            constraints,
            VerificationClass=DatabaseVerification,
            n_source_records=self.n_source_records,
            **kwargs,
        )
        ver.dbh = self
        if ver.failures == 0:
            return ver  # possibly calulate failure passing & failing
            # records and values; though that's bit trivial

        # Build map from names of fields with failures
        # to the failing constraints (only)
        failure_map = remove_falsy_values(
            {
                field: [c for (c, ok) in fc.items() if not ok]
                for field, fc in ver.fields.items()
            }
        )
        failure_field_constraints = remove_falsy_values(
            {
                field: FieldConstraints(
                    field,
                    [
                        constraint
                        for kind, constraint in fc.constraints.items()
                        if kind in failure_map[field]
                    ],
                )
                for field, fc in constraints.fields.items()
                if field in failure_map
            }
        )
        ver.n_failing_fields = len(failure_map)
        ver.n_passing_fields = len(ver.fields) - ver.n_failing_fields
        raw_dest_name, dest_dbtype = dest_pair
        dest_name = self.resolve_table(raw_dest_name, quote=True)
        ver.detection_table = dest_name

        if dest_dbtype != self.dbtype:
            raise TDDAError(
                'Detect from RDBMS currently only supportswriting to same RDBMS.'
            )
        self.drop_table_if_exists(raw_dest_name)
        exprs = (
            []
            if self.interleave
            else [self.quoted(field) for field in failure_map]
        )
        ver.detection_fields = detection_fields = []
        for fc in failure_field_constraints.values():
            if self.interleave:
                exprs.append(self.quoted(fc.name))
            exprs.extend(self.detection_field_expressions(fc))
            detection_fields.extend(self.detection_field_names(fc))
        n_failures_field_sql = self.failures_field(detection_fields)
        exprstr = ',\n'.join(exprs)
        where = (
            ''
            if self.write_all_records
            else (f'WHERE {self.quoted(self.n_failures_field)} > 0')
        )
        sql = f"""
CREATE TABLE {dest_name}
AS
WITH BASE AS (
    SELECT {indent(exprstr, 11)}
    FROM {self.source_table}
),
DETECTED AS (
SELECT *,
       {n_failures_field_sql}
FROM BASE
)
SELECT * FROM DETECTED
{where}
""".strip()
        ver.sql = sql
        if execute:
            self.execute_commit(sql)
            ver.n_records = self.get_nrows(self.source_table)
            ver.n_failing_records = self.count_failing_records(dest_name)
            ver.n_passing_records = ver.n_records - ver.n_failing_records
            ver.write_detection_reports()
        return ver

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
        return [self.out_field_name(fc.name, kind) for kind in fc.constraints]

    def failures_field(self, out_fields):
        if self.detect_passes:
            joint = '\n          + '
            return (
                str(len(out_fields))
                + '\n       - ('
                + (
                    joint.join(
                        f'{self.cast_bool_to_int(self.quoted(field))}'
                        for field in out_fields
                    )
                )
                + f'\n        ) AS {self.quoted(self.n_failures_field)}'
            )
        else:
            joint = '\n       + '
            return (
                joint.join(f'{field}::INT' for field in out_fields)
            ) + f'\nAS {self.quoted(self.n_failures_field)}'

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
            return a(f'({field} {mm_op} {val} {ornull}')
        if kind in ('min_length', 'max_length'):
            return a(f'(LENGTH({field}) {mm_op} {val} {ornull}')
        if kind == 'sign':
            op = SIGN_OP.get(val, None)
            return a(f'({field} {op} 0 {ornull}')
        if kind == 'max_nulls':
            if val > 0:
                maxcond = f'((COUNT(*) OVER ()) <= {val}) OR '
            else:
                maxcond = ''
            return a(f'({maxcond}{field} IS NOT NULL)')
        if kind == 'no_duplicates':
            return a(f'(((COUNT(*) OVER (PARTITION BY {field})) = 1) {ornull}')
        if kind == 'allowed_values':
            return a(
                f'({field} IN ({", ".join(squote(x) for x in val)}) {ornull}'
            )
        if kind == 'rex':
            rex_sql = self.rex_match_sql(field, val)
            if rex_sql:
                return a(f'({rex_sql} {ornull}')
            else:
                return 'true'
        raise TDDAError(f'Internal error: unknown constraint: {kind}')

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
            return a(f'(({field} {mm_op} {val}) {andnn}')
        if kind in ('min_length', 'max_length'):
            return a(f'((LENGTH({field}) {mm_op} {val}) {andnn}')
        if kind == 'sign':
            op = BAD_SIGN_OP.get(val, None)
            return a(f'(({field} {op} 0) {andnn}')
        if kind == 'max_nulls':
            if val > 0:
                maxcond = f'((COUNT(*) OVER (PARTITION BY 1)) > {val}) AND '
            else:
                maxcond = ''
            return a(f'({maxcond}{field} IS NULL)')
        if kind == 'no_duplicates':
            return a(f'(((COUNT(*) OVER (PARTITION BY {field})) > 1) {andnn}')
        if kind == 'allowed_values':
            return a(
                f'({field} NOT IN ({", ".join(squote(x) for x in val)}){andnn}'
            )
        if kind == 'rex':
            rex_sql = self.rex_match_sql(field, val)
            if rex_sql:
                return a(f'{rex_sql} {andnn}')
            else:
                return 'false'
        raise TDDAError(f'Internal error: unknown constraint: {kind}')

    def out_field_name(self, field, kind):
        return f'{field}_{kind}_{self.out_field_suffix}'

    def count_failing_records(self, table):
        expr = self.count_non_zero_sql(self.n_failures_field)
        return self.get_scalar(expr, table)


class DatabaseVerification(Verification):
    """Verification and detection result for a database table.

    Extends ``Verification`` for use with database tables. Used for
    both verification results (from ``verify_db_table``) and detection
    results (from ``detect_db_table``).

    Attributes:
        passes: Number of constraints that passed.
        failures: Number of constraints that failed.
        fields: Per-field verification results, keyed by field name.
        n_source_records: Number of records in the source table.
    """

    def __init__(self, *args, **kwargs):
        self.is_db = True
        Verification.__init__(self, *args, **kwargs)

    def get_failure_values(self, field, constraint, key_fields, max_vals=None):
        indicator_field = indicator_field_name(
            field,
            constraint,
            CONSTRAINT_SUFFIX_MAP,
            detect_passes=self.detect_passes,
        )
        exists = indicator_field in self.detection_fields
        bad_val = str(self.bad_val).upper()
        keys = (
            (','.join(self.quoted(k) for k in key_fields) + ', ')
            if key_fields
            else ''
        )
        dbh = self.dbh
        if exists:
            sql = (
                f'SELECT {keys}{self.dbh.quoted(field)}\n'
                f'FROM {self.detection_table}\n'
                f'WHERE {dbh.quoted(indicator_field)} = {bad_val}'
            )
            if max_vals:
                if not type(max_vals) == int and max_vals > 0:
                    raise TDDAError(
                        f'Internal error: Bad value for max_vals: {max_vals}'
                    )
                sql += f'\nLIMIT {max_vals}'
            result = self.dbh.execute_all(sql)
            return [list(r) for r in result]
        else:
            return None

    def get_constraint_stats(self, field, constraint):
        indicator_field = indicator_field_name(
            field,
            constraint,
            CONSTRAINT_SUFFIX_MAP,
            detect_passes=self.detect_passes,
        )
        if not hasattr(self, 'constraint_stats'):
            # compute them all together and save as dict
            sql = (
                'SELECT\n'
                + ',\n'.join(
                    self.count_failing_records_for(indicator)
                    for indicator in self.detection_fields
                )
                + f'\nFROM {self.detection_table}'
            )
            result = self.dbh.execute_all(sql)
            self.constraint_stats = dict(zip(self.detection_fields, result[0]))
        failures = self.constraint_stats.get(indicator_field, 0)
        passes = self.n_records - failures
        return pass_fail_stats(passes, failures, 'values')

    def bad_val(self):
        if self.detect_passes:
            return '0' if self.int_bools else 'FALSE'
        else:
            return '1' if self.int_bools else 'TRUE'

    def count_failing_records_for(self, indicator_field):
        dbh = self.dbh
        if self.int_bools:
            f = dbh.sum_sql if self.detect_passes else dbh.count_zero_sql
        else:
            f = (
                dbh.count_false_sql
                if self.detect_passes
                else dbh.count_true_sql
            )
        return f(indicator_field)

    def build_field_stats(self, fields):
        self.field_stats = {}
        inds = {
            field: list(
                {
                    self.indicator_field_name(field, constraint)
                    for constraint in CONSTRAINT_SUFFIX_MAP
                }.intersection(set(self.detection_fields))
            )
            for field in fields
        }
        sql = (
            'SELECT\n'
            + ',\n'.join(
                self.count_failing_field_values(field, inds[field])
                for field in fields
            )
            + f'\nFROM {self.detection_table}'
        )
        results = self.dbh.execute_all(sql)
        self.field_stats = {
            field: PassFailCount(
                field, self.n_source_records - results[0][i], results[0][i]
            )
            for i, field in enumerate(fields)
        }

    def count_failing_field_values(self, field, indicators):
        dbh = self.dbh
        if len(indicators) == 0:  # no indicators, no failures
            return '0'

        if self.int_bools:
            if self.detect_passes:
                return dbh.count_zero_sql(indicators, joint=' * ')
            elif len(indicators) == 1:
                return dbh.sum_sql(indicators[0])
            else:
                return dbh.sum_greatest_sql(indicators)
        else:
            if self.detect_passes:
                return dbh.count_false_sql(indicators, joint=' AND ')
            else:
                return dbh.count_true_sql(indicators, joint=' OR ')

    def get_field_stats(self, field):
        return self.field_stats[field]


class DatabaseConstraintDiscoverer(
    DatabaseConstraintCalculator, BaseConstraintDiscoverer, DatabaseHandler
):
    """
    A :py:class:`DatabaseConstraintDiscoverer` object is used to discover
    constraints on a single database table.
    """

    def __init__(
        self,
        dbtype,
        dbc,
        tablename,
        inc_rex=False,
        group_rexes=True,
        no_md=False,
        allowed_fields=True,
        required_fields=True,
        seed=None,
    ):
        DatabaseHandler.__init__(self, dbtype, dbc)
        tablename = self.resolve_table(tablename)

        DatabaseConstraintCalculator.__init__(self, tablename)
        BaseConstraintDiscoverer.__init__(
            self,
            inc_rex=inc_rex,
            group_rexes=group_rexes,
            no_md=no_md,
            allowed_fields=allowed_fields,
            required_fields=required_fields,
            seed=seed,
        )
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
    tx = type(x)
    ty = type(y)
    ok = tx == ty
    if not ok and colname:
        print(
            'Warning: Failing incompatible types constraint for field %s '
            'of type %s.\n(Constraint value %s of type %s.)'
            % (colname, type(x), y, type(y)),
            file=sys.stderr,
        )
    return ok


def verify_db_table(
    dbtype,
    db,
    tablename,
    constraints_path,
    epsilon=None,
    type_checking='strict',
    testing=False,
    report='all',
    **kwargs,
):
    """Verify that the database table satisfies the constraints in the
    ``.tdda`` file provided.

    Args:
        dbtype: Database type (e.g. ``'postgres'``, ``'mysql'``).
        db: Database connection object.
        tablename: Name of the table to verify.
        constraints_path: Path to a JSON ``.tdda`` file, or an
            in-memory ``DatasetConstraints`` object.
        epsilon: Tolerance for min/max constraint checks, as a
            proportion of the constraint value. For example, ``0.01``
            allows values up to 1% larger than a max constraint without
            generating a failure, and minimum values can be up to 1%
            smaller than the minimum constraint value without generating
            a failure. (These are modified, as appropriate, for negative
            values.)

            If not specified, an epsilon of 0 is used, so there is no
            tolerance.

            NOTE: A consequence of the fact that these are proportionate
            is that min/max values of zero do not have any tolerance,
            i.e. the wrong sign always generates a failure.

        type_checking: ``'strict'``, ``'sloppy'``, or ``'loose'``
            (``'loose'`` and ``'sloppy'`` are equivalent). Defaults to
            ``'strict'`` for databases. With ``'sloppy'``/``'loose'``,
            a database ``real`` column may satisfy an ``int`` type
            constraint.
        testing: If ``True``, suppresses type-compatibility warnings.
            Should only be set when running automated tests. Default
            is ``False``.
        report: ``'all'`` or ``'fields'``. Controls the behaviour of
            ``__str__`` on the resulting ``DatabaseVerification`` object
            (but not its content).

            ``'all'`` (the default) means that all fields are shown,
            together with the verification status of each constraint for
            that field.

            If set to ``'fields'``, only fields for which at least one
            constraint failed are shown.
        **kwargs: Additional keyword arguments.

    Returns:
        DatabaseVerification: Verification results, with ``passes``
        and ``failures`` attributes giving the number of passing and
        failing constraints.

    Example::

        import pgdb
        from tdda.constraints import verify_db_table

        dbspec = 'localhost:databasename:username:password'
        tablename = 'schemaname.tablename'
        db = pgdb.connect(dbspec)
        v = verify_db_table('postgres', db, tablename,
                            'myconstraints.tdda')

        print('Constraints passing:', v.passes)
        print('Constraints failing: %d\\n' % v.failures)
        print(str(v))
    """
    dbv = DatabaseConstraintVerifier(
        dbtype,
        db,
        tablename,
        epsilon=epsilon,
        type_checking=type_checking,
        testing=testing,
    )
    if not dbv.table_exists(tablename):
        print('No table %s' % tablename, file=sys.stderr)
        sys.exit(1)
    constraints = DatasetConstraints(loadpath=constraints_path)
    return dbv.verify(
        constraints,
        VerificationClass=DatabaseVerification,
        report=report,
        n_source_records=dbv.n_source_records,
        **kwargs,
    )


def detect_db_table(
    dbtype,
    dbc,
    tablename,
    constraints_path,
    destination,
    epsilon=None,
    type_checking='strict',
    testing=False,
    **kwargs,
):
    """Detect records in the database table that fail any of the
    constraints in the ``.tdda`` file provided.

    Args:
        dbtype: Database type (e.g. ``'postgres'``, ``'mysql'``).
        dbc: Database connection object.
        tablename: Name of the table to check.
        constraints_path: Path to a JSON ``.tdda`` file, or an
            in-memory ``DatasetConstraints`` object.
        destination: Destination for output records.
        epsilon: Tolerance for min/max constraint checks, as a
            proportion of the constraint value. For example, ``0.01``
            allows values up to 1% larger than a max constraint without
            generating a failure, and minimum values can be up to 1%
            smaller than the minimum constraint value without generating
            a failure. (These are modified, as appropriate, for negative
            values.)

            If not specified, an epsilon of 0 is used, so there is no
            tolerance.

            NOTE: A consequence of the fact that these are proportionate
            is that min/max values of zero do not have any tolerance,
            i.e. the wrong sign always generates a failure.

        type_checking: ``'strict'``, ``'sloppy'``, or ``'loose'``
            (``'loose'`` and ``'sloppy'`` are equivalent). Defaults to
            ``'strict'`` for databases. With ``'sloppy'``/``'loose'``,
            a database ``real`` column may satisfy an ``int`` type
            constraint.
        testing: If ``True``, suppresses type-compatibility warnings.
            Default is ``False``.
        **kwargs: Additional keyword arguments.

    Returns:
        DatabaseVerification: Detection results.
    """
    detector = DatabaseConstraintDetector(
        dbtype,
        dbc,
        tablename,
        epsilon=epsilon,
        type_checking=type_checking,
        **kwargs,
    )
    constraints = constraints_from_path_or_dict(constraints_path)
    return detector.detect(constraints, destination, **kwargs)


def discover_db_table(
    dbtype,
    dbc,
    tablename,
    inc_rex=False,
    group_rexes=True,
    report_path=None,
    report_formats=None,
    seed=None,
    no_md=False,
    **kw,
):
    """Discover constraints characterizing the database table provided.

    Examines each column and generates constraints that describe the
    data. The kinds of constraints potentially generated for each field
    are:

    - **type**: the coarse TDDA type: ``'bool'``, ``'int'``,
      ``'real'``, ``'string'``, or ``'date'``.
    - **min**: for non-string fields, the minimum value (not generated
      for all-null columns).
    - **max**: for non-string fields, the maximum value (not generated
      for all-null columns).
    - **min_length**: for string fields, the shortest string length.
    - **max_length**: for string fields, the longest string length.
    - **sign**: if all values in a numeric field have consistent sign,
      a sign constraint is written with a value chosen from:

      - ``'positive'``     — for all values *v* in field: ``v > 0``
      - ``'non-negative'`` — for all values *v* in field: ``v >= 0``
      - ``'zero'``         — for all values *v* in field: ``v == 0``
      - ``'non-positive'`` — for all values *v* in field: ``v <= 0``
      - ``'negative'``     — for all values *v* in field: ``v < 0``
      - ``'null'``         — for all values *v* in field: ``v is null``

    - **max_nulls**: the maximum number of nulls allowed in the field.
      Set to 0 if the field has no nulls, 1 if it has a single null.
      Not generated if the field has more than one null.
    - **no_duplicates**: for string fields (only, for now), ``True``
      if every non-null value in the field is distinct. Only generated
      when all non-null values are unique; otherwise no constraint is
      written.
    - **allowed_values**: for string fields only, if there are
      ``MAX_CATEGORIES`` (currently 20) or fewer distinct values, an
      allowed-values constraint listing them will be generated.

    Regular expression constraints are not (currently) generated for
    database tables.

    Args:
        dbtype: Database type (e.g. ``'postgres'``, ``'mysql'``).
        dbc: Database connection object.
        tablename: Name of the table to discover constraints for.
        inc_rex: If ``True``, include regular expression constraints.
            Default is ``False``.
        group_rexes: If ``True``, group regular expression
            constraints. Default is ``True``.
        report_path: Path for reports (extension ignored).
        report_formats: List of report formats to write. Options:
            ``'html'``, ``'markdown'`` (or ``'md'``), ``'text'`` (or
            ``'txt'``), ``'yaml'``, ``'json'``, ``'toml'``.
        seed: Optional random seed.
        no_md: If ``True``, suppress the metadata section of the
            ``.tdda`` file. Default is ``False``.
        **kw: Additional keyword arguments.

    Returns:
        DatasetConstraints: Discovered constraints, or ``None`` if no
        constraints were found. The returned object includes a
        ``to_json()`` method, which converts the constraints to JSON
        for saving as a ``.tdda`` constraints file. By convention,
        such files use a ``.tdda`` extension. The constraints file
        can then be used to check whether other datasets satisfy the
        same constraints.

    Example::

        import pgdb
        from tdda.constraints import discover_db_table

        dbspec = 'localhost:databasename:username:password'
        tablename = 'schemaname.tablename'
        db = pgdb.connect(dbspec)
        constraints = discover_db_table('postgres', db, tablename)

        with open('myconstraints.tdda', 'w', encoding='utf-8') as f:
            f.write(constraints.to_json())
    """
    disco = DatabaseConstraintDiscoverer(
        dbtype,
        dbc,
        tablename,
        inc_rex=inc_rex,
        group_rexes=group_rexes,
        no_md=no_md,
        seed=seed,
    )
    if not disco.table_exists(tablename):
        print('No table %s' % tablename, file=sys.stderr)
        sys.exit(1)
    constraints = disco.discover()
    if constraints:
        nrows = disco.get_nrows(tablename)
        constraints.set_stats(n_records=nrows, n_selected=nrows)
        constraints.set_dates_user_host_creator()
        constraints.set_rdbms(
            '%s:%s:%s:%s'
            % (dbtype or '', dbc.host or '', dbc.user, dbc.database)
        )
        constraints.set_source(tablename, tablename)
    return constraints


def indent(s, indentation):
    joint = '\n' + ' ' * indentation
    return joint.join(s.splitlines())
