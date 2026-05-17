# -*- coding: utf-8 -*-
"""
The ``tdda.constraints.pd.constraints`` module provides an
implementation of TDDA constraint discovery and verification
for Pandas DataFrames.

This allows it to be used for data in CSV files, or for DataFrames
read from Parquet files.

The top-level functions are:

    ``tdda.constraints.discover_df``:
        Discover constraints from a Pandas DataFrame.

    ``tdda.constraints.verify_df``:
        Verify (check) a Pandas DataFrame, against a set of previously
        discovered constraints.

    ``tdda.constraints.detect_df``:
        For detection of failing rows in a Pandas DataFrame,
        verified against a set of previously discovered constraints,
        and generate an output dataset containing
        information about input rows which failed any of the constraints.

"""

import datetime
import os
import re
import sys

from collections import OrderedDict

try:
    from StringIO import StringIO
except ImportError:
    from io import StringIO

import numpy as np
import pandas as pd

from tdda.constraints.base import (
    STANDARD_FIELD_CONSTRAINTS,
    STANDARD_CONSTRAINT_SUFFIXES,
    CONSTRAINT_SUFFIX_MAP,
    unicode_definite,
    DatasetConstraints,
    Verification,
    Detection,
    constraints_from_path_or_dict,
    fuzz_down,
    fuzz_up,
    PassFailCount,
)
from tdda.constraints.baseconstraints import (
    BaseConstraintCalculator,
    BaseConstraintDetector,
    BaseConstraintVerifier,
    BaseConstraintDiscoverer,
    MAX_CATEGORIES,
)
from tdda.pd.utils import (
    is_string_col,
    is_string_dtype,
    is_categorical_dtype,
)
from tdda.abstractdf import csv_to_dataframe


from tdda.referencetest.checkpandas import (
    default_csv_loader,
    default_csv_writer,
)
from tdda import rexpy

from tdda.serial.reader import load_metadata
from tdda.serial.utils import (
    find_associated_metadata_file,
    find_metadata_type_from_path,
    get_backend,
    OG_BACKEND,
)
from tdda.serial.pandasio import serial_to_pandas_read_csv_args
from tdda.utils import (
    indicator_field_name,
    pass_fail_stats,
    handle_tilde,
    warn,
    json_sanitize,
)

# pd.tslib is deprecated in newer versions of Pandas
if hasattr(pd, 'Timestamp'):
    pandas_Timestamp = pd.Timestamp
else:
    pandas_Timestamp = pd.tslib.Timestamp

DEBUG = False
RE_FLAGS = re.UNICODE | re.DOTALL


class PandasConstraintCalculator(BaseConstraintCalculator):
    """
    Implementation of the Constraint Calculator methods for
    Pandas dataframes.
    """

    def __init__(self, df):
        self.df = df

    def is_null(self, value):
        return pd.isnull(value)

    def to_datetime(self, value):
        return pd.to_datetime(value)

    def get_column_names(self):
        return list(self.df)

    def get_nrecords(self):
        return len(self.df)

    def types_compatible(self, x, y, colname=None):
        return pandas_types_compatible(x, y, colname=colname)

    def calc_min(self, colname):
        if is_string_col(self.df[colname]):
            m = self.df[colname].dropna().min()  # Otherwise -inf!
        else:
            m = self.df[colname].min()
        if pandas_tdda_type(m) == 'date' and hasattr(m, 'to_pydatetime'):
            m = m.to_pydatetime(warn=False)
        elif hasattr(m, 'item'):
            m = m.item()
        return m

    def calc_max(self, colname):
        if is_string_col(self.df[colname]):
            M = self.df[colname].dropna().max()
        else:
            M = self.df[colname].max()
        if pandas_tdda_type(M) == 'date' and hasattr(M, 'to_pydatetime'):
            M = M.to_pydatetime(warn=False)
        elif hasattr(M, 'item'):
            M = M.item()
        return M

    def calc_min_length(self, colname):
        return self.df[colname].str.len().min()

    def calc_max_length(self, colname):
        return self.df[colname].str.len().max()

    def calc_tdda_type(self, colname):
        return pandas_tdda_type(self.df[colname])

    def calc_null_count(self, colname):
        return int(len(self.df) - self.df[colname].count())

    def calc_non_null_count(self, colname):
        return int(len(self.df) - self.calc_null_count(colname))

    def calc_nunique(self, colname):
        return int(self.df[colname].nunique())

    def calc_unique_values(self, colname, include_nulls=True):
        values = self.df[colname].unique()
        nullvalues = (
            [v for v in self.df[colname].unique() if pd.isnull(v)]
            if include_nulls
            else []
        )
        nonnullvalues = [v for v in values if not pd.isnull(v)]
        return nullvalues + sorted(nonnullvalues)

    def calc_non_integer_values_count(self, colname):
        values = self.df[colname].dropna()
        non_nulls = self.df[colname].count()
        return int(
            non_nulls - (values.astype(int) == values).astype(int).sum()
        )

    def calc_all_non_nulls_boolean(self, colname):
        nn = self.df[colname].dropna()
        return all(type(v) is bool for v in nn.to_list())

    # def allowed_values_exclusions(self):
    #     # remarkably, Pandas returns various kinds of nulls as
    #     # unique values, despite not counting them with .nunique()
    #     return [None, np.nan, pd.NaT, pd.NA, float('nan')]

    def filter_out_nulls(self, values):
        return {v for v in values if not pd.isnull(v)}

    def find_rexes(self, colname, values=None, seed=None):
        if values is None:
            return rexpy.pdextract(self.df[colname], tag=self.group_rexes)
        else:
            return rexpy.extract(values, seed=None, tag=self.group_rexes)

    def calc_rex_constraint(self, colname, constraint, detect=False):
        # note that this should return a set of violations, not True/False.
        rexes = constraint.value
        if rexes is None:  # a null value is not considered
            return None  # to be an active constraint,
            # so is always satisfied
        rexes = [re.compile(r, RE_FLAGS) for r in rexes]
        strings = [
            unicode_definite(s) for s in self.df[colname].dropna().unique()
        ]

        failures = set()
        for s in strings:
            for r in rexes:
                if re.match(r, s):
                    break
            else:
                if DEBUG:
                    print('*** Unmatched string: "%s"' % s)
                if detect:
                    failures.add(s)
                else:
                    return True  # At least one string didn't match
        if detect:
            return failures
        else:
            return None


class PandasConstraintDetector(BaseConstraintDetector):
    """
    Implementation of the Constraint Detector methods for
    Pandas dataframes.
    """

    def __init__(self, df):
        self.df = df
        if df is not None:
            self.date_cols = list(df.select_dtypes(include=[np.datetime64]))
            index = df.index.copy()
            if not index.name:
                index.name = 'Index'
            self.out_df = pd.DataFrame(index=index)
        else:
            self.date_cols = []
            self.out_df = None

    def remove_if_exists(self, name):
        if name in self.out_df:
            del self.df[name]
        warn(f'Updating old field {name}.')

    def detect_min_constraint(self, colname, value, precision, epsilon):
        name = verification_field(colname, 'min')
        c = self.df[colname]
        if not pandas_types_compatible(c, value):
            self.out_df[name] = False
        elif precision == 'closed' or colname in self.date_cols:
            self.out_df[name] = detection_field(c, c >= value)
        elif precision == 'open':
            self.out_df[name] = detection_field(c, c > value)
        else:
            self.out_df[name] = detection_field(
                c, df_fuzzy_gt(c, value, epsilon)
            )

    def detect_max_constraint(self, colname, value, precision, epsilon):
        name = verification_field(colname, 'max')
        c = self.df[colname]
        if not pandas_types_compatible(c, value):
            self.out_df[name] = False
        elif precision == 'closed' or colname in self.date_cols:
            self.out_df[name] = detection_field(c, c <= value)
        elif precision == 'open':
            self.out_df[name] = detection_field(c, c < value)
        else:
            self.out_df[name] = detection_field(
                c, df_fuzzy_lt(c, value, epsilon)
            )

    def detect_min_length_constraint(self, colname, value):
        name = verification_field(colname, 'min_length')
        c = self.df[colname]
        if pandas_coarse_type(c) != 'string':
            self.out_df[name] = False
        else:
            self.out_df[name] = detection_field(c, c.str.len() >= value)

    def detect_max_length_constraint(self, colname, value):
        name = verification_field(colname, 'max_length')
        c = self.df[colname]
        if pandas_coarse_type(c) != 'string':
            self.out_df[name] = False
        else:
            self.out_df[name] = detection_field(c, c.str.len() <= value)

    def detect_tdda_type_constraint(self, colname, value):
        name = verification_field(colname, 'type')
        self.out_df[name] = False

    def detect_sign_constraint(self, colname, value):
        name = verification_field(colname, 'sign')
        c = self.df[colname]

        if pandas_coarse_type(c) != 'number':
            result = False
        elif value == 'null':
            self.out_df[name] = False
        elif value == 'positive':
            self.out_df[name] = detection_field(c, c > 0)
        elif value == 'non-negative':
            self.out_df[name] = detection_field(c, c >= 0)
        elif value == 'zero':
            self.out_df[name] = detection_field(c, c == 0)
        elif value == 'non-positive':
            self.out_df[name] = detection_field(c, c <= 0)
        elif value == 'negative':
            self.out_df[name] = detection_field(c, c < 0)

    def detect_max_nulls_constraint(self, colname, value):
        # found more nulls than are allowed, so mark all null values as bad
        name = verification_field(colname, 'max_nulls')
        c = self.df[colname]
        self.out_df[name] = pd.notnull(c)

    def detect_no_duplicates_constraint(self, colname, value):
        # found duplicates, so mark anything duplicated as bad
        name = verification_field(colname, 'no_duplicates')
        c = self.df[colname]
        unique = ~self.df.duplicated(colname, keep=False)
        self.out_df[name] = detection_field(c, unique, default=True)

    def detect_allowed_values_constraint(
        self, colname, allowed_values, violations
    ):
        name = verification_field(colname, 'allowed_values')
        c = self.df[colname]
        self.out_df[name] = detection_field(c, ~c.isin(violations))

    def detect_rex_constraint(self, colname, violations):
        name = verification_field(colname, 'rex')
        c = self.df[colname]
        if pandas_coarse_type(c) != 'string':
            self.out_df[name] = False
        else:
            self.out_df[name] = detection_field(c, ~c.isin(violations))

    def write_detected_records(
        self,
        outpath=None,
        write_all_records=False,
        per_constraint=False,
        output_fields=None,
        index=False,
        in_place=False,
        rownumber_is_index=True,
        int_bools=False,
        interleave=False,
        **kwargs,
    ):
        if self.out_df is None:
            return None
        orig_fields = list(self.df)
        output_is_typed = outpath and file_format(outpath) == 'parquet'

        out_df = self.out_df
        add_index = index or output_fields is None
        if output_fields is None:
            output_fields = []
        elif len(output_fields) == 0:
            output_fields = list(self.df)

        nfailname = (
            'n_failures' if 'n_failures' not in self.df else 'n_tdda_failures'
        )
        nf = len(list(out_df))  # ok fields
        fails = (
            nf
            - out_df.sum(axis=1).astype(float)
            - out_df.isnull().sum(axis=1).astype(float)
        )
        out_df[nfailname] = fails.astype(int)  # failing record indicator
        n_failing_records = (fails > 0).astype(int).sum()
        n_passing_records = self.df.shape[0] - n_failing_records

        if not per_constraint:
            fnames = [name for name in list(out_df) if name != nfailname]
            out_df = out_df.drop(fnames, axis=1)

        if in_place:
            for fname in list(out_df):
                newfield = out_df[fname]
                self.df[unique_column_name(self.df, fname)] = newfield

        if output_fields:
            for fname in reversed(output_fields):
                if fname in list(self.df):
                    if fname in list(self.out_df):
                        warn(f'Replacing old field {fname}.')
                    else:
                        out_df.insert(0, fname, self.df[fname])
                else:
                    raise Exception('DataFrame has no column %s' % fname)

        if interleave:
            out_df = self.interleave(out_df, orig_fields, nfailname)
        #             if in_place:  # does not work in place
        #                 self.interleave(self.df, orig_fields, nfailname)

        if outpath:
            index_is_trivial = is_pd_index_trivial(out_df)
            if output_is_typed:
                df_to_save = out_df
            else:
                df_to_save = convert_output_types(out_df, int_bools)
            if add_index:
                # Legacy
                # Add Index or RowNumber columns to output CSV file (or
                # add appropriate columns to output feather file and reset
                # its index, because feather doesn't support MultiIndexes
                # and doesn't retain single indexes).
                indexes = []
                if rownumber_is_index:
                    stem = 'Index' if rownumber_is_index else 'RowNumber'
                    if isinstance(df_to_save.index, pd.MultiIndex):
                        for i, level in enumerate(df_to_save.index.levels):
                            name = (
                                df_to_save.index.names[i]
                                if df_to_save.index.names
                                else '%s_%d' % (stem, (i + 1))
                            )
                            pair = (
                                unique_column_name(df_to_save, name),
                                df_to_save.index.get_level_values(i),
                            )
                            indexes.append(pair)
                    else:
                        indexes.append(
                            (
                                unique_column_name(df_to_save, stem),
                                df_to_save.index,
                            )
                        )
                    df_to_save.reset_index(inplace=True, drop=True)
                else:
                    pair = (
                        unique_column_name(df_to_save, 'RowNumber'),
                        pd.RangeIndex(1, len(df_to_save) + 1),
                    )
                    indexes.append(pair)
                for name, index in reversed(indexes):
                    df_to_save.insert(0, name, index)

            if not write_all_records:
                df_to_save = df_to_save[df_to_save[nfailname] > 0]
            save_df(df_to_save, outpath, index=False)

        if not write_all_records:
            out_df = out_df[out_df[nfailname] > 0]
        return Detection(out_df, n_passing_records, n_failing_records)

    def interleave(self, df, orig_fields, nfailname):
        if set(orig_fields) - set(list(df)):
            return df
            # Only interleave if all of the original fields
            # are in the output

        all_vfields = set(list(df)) - set(orig_fields) - set([nfailname])
        new_fields = []
        for f in orig_fields:
            new_fields.append(f)
            new_fields.extend(
                sorted([v for v in all_vfields if is_ver_field(v, f)])
            )
        new_fields.append(nfailname)
        if DEBUG and set(list(df)) != set(new_fields):
            print('list(df))', list(df), len(list(df)))
            print('new fields', new_fields, len(new_fields))
        assert set(list(df)) == set(new_fields)
        return df[new_fields]


class PandasConstraintVerifier(
    PandasConstraintCalculator,
    PandasConstraintDetector,
    BaseConstraintVerifier,
):
    """
    Provides methods for verifying every type of constraint against
    a Pandas DataFrame.
    """

    def __init__(self, df, epsilon=None, type_checking=None):
        PandasConstraintCalculator.__init__(self, df)
        PandasConstraintDetector.__init__(self, df)
        BaseConstraintVerifier.__init__(
            self, epsilon=epsilon, type_checking=type_checking
        )

    def repair_field_types(self, constraints):
        # We sometimes haven't inferred the field types correctly for
        # the dataframe (e.g. if we read it from a csv file, "string"
        # fields might look like numeric ones, if they only contain digits).
        # We can try to use the constraint information to try to repair this,
        # but it's not always going to be successful.
        for c in self.df.columns.tolist():
            if c not in constraints:
                continue
            ser = self.df[c]
            try:
                ctype = constraints[c]['type'].value
                dtype = ser.dtype
                if ctype == 'string' and not is_string_col(ser):
                    is_numeric = True
                    is_real = False
                    for limit in ('min', 'max'):
                        if limit in constraints[c]:
                            limitval = constraints[c][limit].value
                            if type(limitval) in (int, float):
                                if type(limitval) == float:
                                    is_real = True
                            else:
                                is_numeric = False
                                break
                    if is_numeric:
                        if is_real:
                            is_real = self.calc_non_integer_values_count(c) > 0
                        self.df[c] = np.where(
                            ser.notnull(), ser.astype(str), np.nan
                        )
                        if not is_real:
                            self.df[c] = self.df[c].str.replace(
                                '.0', '', regex=False
                            )
                elif ctype == 'bool' and str(dtype).lower().startswith('int'):
                    self.df[c] = ser.astype(bool)
            except Exception as e:
                print('%s: %s' % (e.__class__.__name__, str(e)))


class PandasVerification(Verification):
    """Verification result for a Pandas DataFrame.

    Extends ``Verification`` with ``to_frame()`` to convert the
    verification result to a Pandas DataFrame, with columns:

    - ``field``: field (column) name.
    - ``failures``: number of failing constraints for the field.
    - ``passes``: number of passing constraints for the field.
    - One boolean column per constraint type, with values ``True``
      (constraint satisfied), ``False`` (constraint failed), or
      ``np.nan`` (no constraint of this kind).

    Returned by ``verify_df``.
    """

    def __init__(self, *args, **kwargs):
        Verification.__init__(self, *args, **kwargs)

    def to_frame(self):
        """
        Converts object to a Pandas DataFrame.
        """
        return self.verification_to_dataframe(self)

    @staticmethod
    def verification_to_dataframe(ver):
        fields = ver.fields
        df = pd.DataFrame(
            OrderedDict(
                (
                    ('field', list(fields.keys())),
                    ('failures', [v.failures for k, v in fields.items()]),
                    ('passes', [v.passes for k, v in fields.items()]),
                )
            )
        )
        kinds_used = set([])
        for field, constraints in fields.items():
            kinds_used = kinds_used.union(set(list(constraints.keys())))
        base_kinds = [k for k in STANDARD_FIELD_CONSTRAINTS if k in kinds_used]
        other_kinds = [k for k in kinds_used if not k in base_kinds]
        for kind in base_kinds + other_kinds:
            df[kind] = [fields[field].get(kind, np.nan) for field in fields]
        return df

    to_dataframe = to_frame

    def get_failure_values(self, field, constraint, key_fields, max_vals=None):
        indicator_field = self.indicator_field_name(field, constraint)
        exists = (
            indicator_field in self.detection.obj
            and field in self.detection.obj
        )
        bad_val = 0  # 1 for bad field#
        if exists:
            df = self.detection.obj.query(f'{indicator_field} == {bad_val}')
            if max_vals and df.shape[0] > max_vals:
                df = df.head(max_vals)
            return zip(
                *(df[k].to_list() for k in key_fields), df[field].to_list()
            )
        else:
            return None

    def get_constraint_stats(self, field, constraint):
        ok_field = self.indicator_field_name(field, constraint)
        # TODO: support bad as well
        df = self.detection.obj
        n_records = int(
            self.detection.n_passing_records + self.detection.n_failing_records
        )
        if ok_field in df:
            failures = int((df[ok_field] == 0).sum())
            passes = n_records - failures
            return pass_fail_stats(passes, failures, 'values')
        else:
            return pass_fail_stats(n_records, 0, 'values')

    def get_field_stats(self, field):
        """
        Count the number of passes and failures across all constraints
        for the field (name) specified as a PassFailCount object.

        Used to calculate number of failing (constrained) values.
        """
        df = self.detection.obj
        indicators = list(
            {
                self.indicator_field_name(field, constraint)
                for constraint in CONSTRAINT_SUFFIX_MAP
            }.intersection(set(df))
        )
        if len(indicators) == 0:  # no failures
            nf = 0
        else:
            nf = df.query(
                ' | '.join(
                    f'{indicator} == {self.bad_val}'
                    for indicator in indicators
                )
            ).shape[0]
        return PassFailCount(field, self.detection.n_source_records - nf, nf)


class PandasDetection(PandasVerification):
    """Detection result for a Pandas DataFrame.

    Extends ``PandasVerification`` with a ``detected()`` method giving
    access to the detected records as a Pandas DataFrame.

    Attributes:
        n_passing_records: Number of records that passed all constraints.
        n_failing_records: Number of records that failed at least one
            constraint.

    Returned by ``detect_df``.
    """

    def __init__(self, *args, **kwargs):
        PandasVerification.__init__(self, *args, **kwargs)

    def detected(self):
        """Return a DataFrame of detected (failing) records.

        Returns:
            DataFrame of records that failed at least one constraint,
            or ``None`` if there were no failures and ``write_all_records``
            was not set.
        """
        return self.detection.obj if self.detection else None


class PandasConstraintDiscoverer(
    PandasConstraintCalculator, BaseConstraintDiscoverer
):
    """
    Used to discover constraints on a Pandas DataFrame.
    """

    def __init__(
        self,
        df,
        inc_rex=False,
        group_rexes=True,
        no_md=False,
        allowed_fields=True,
        required_fields=True,
    ):
        PandasConstraintCalculator.__init__(self, df)
        BaseConstraintDiscoverer.__init__(
            self,
            inc_rex=inc_rex,
            group_rexes=group_rexes,
            no_md=no_md,
            allowed_fields=allowed_fields,
            required_fields=required_fields,
        )


def pandas_types_compatible(x, y, colname=None):
    """
    Returns boolean indicating whether the coarse_type of *x* and *y* are
    the same, for scalar values.

    If *colname* is provided, and the check fails, a warning is issued
    to stderr.
    """
    ok = pandas_coarse_type(x) == pandas_coarse_type(y)
    if not ok and colname:
        print(
            'Warning: Failing incompatible types constraint for field %s '
            'of type %s.\n(Constraint value %s of type %s.)'
            % (colname, type(x), y, type(y)),
            file=sys.stderr,
        )
    return ok


def pandas_coarse_type(x):
    """
    Returns the TDDA coarse type of *x*, a scalar value.
    The coarse types combine ``bool``, ``int`` and ``real`` into ``number``.

    Obviously, some people will dislike treating booleans as numbers.
    But it is necessary here.
    """
    t = pandas_tdda_type(x)
    return 'number' if t in ('bool', 'int', 'real') else t


def pandas_tdda_type(x):
    """
    Returns the TDDA type of a column.

    Basic TDDA types are one of 'bool', 'int', 'real', 'string' or 'date'.

    If *x* is ``None`` or something Pandas classes as null, 'null' is returned.

    If *x* is not recognized as one of these, 'other' is returned.
    """
    if type(x) == str:
        return 'string'
    dt = getattr(x, 'dtype', None)
    dts = str(dt).lower()
    if dt == np.dtype('O'):
        # objects could be either strings or booleans-with-nulls or dates
        for v in x:
            if type(v) in (bool, np.bool_):
                return 'bool'
            elif type(v) in (str, bytes):
                return 'string'
            elif isinstance(v, datetime.datetime):
                return 'date'
            elif isinstance(v, datetime.date):
                return 'date'
        # if it was all null, there's no way to tell its type, so say string
        return 'string'
    if is_categorical_dtype(dt) or dts.startswith('str'):
        return 'string'
    if type(x) == bool or 'bool' in dts:
        return 'bool'
    if type(x) is int or 'int' in dts:
        return 'int'
    if type(x) == float or 'float' in dts or 'double' in dts:
        return 'real'
    if (
        'date' in dts
        or isinstance(x, datetime.datetime)
        or isinstance(x, datetime.date)
        or isinstance(x, pandas_Timestamp)
    ):
        return 'date'
    if x is None:
        return 'null'
    null = pd.isnull(x)
    if hasattr(null, 'size'):
        null = False  # pd.isnull returned an array
    if not isinstance(x, pd.core.series.Series) and null:
        return 'null'
    # Everything else is other, for now, including compound types,
    return 'other'


def verify_df(
    df,
    constraints_path,
    epsilon=None,
    type_checking=None,
    repair=True,
    report='all',
    engine=None,
    backend=None,
    config=None,
    **kwargs,
):
    """Verify that a DataFrame satisfies the constraints in a ``.tdda`` file.

    Args:
        df: DataFrame to be checked (Pandas or Polars).
        constraints_path: Path to a JSON ``.tdda`` file, or an in-memory
            dictionary containing the structured contents of a ``.tdda``
            file.
        epsilon: Tolerance for min/max constraint checks, as a proportion
            of the constraint value. For example, ``0.01`` allows values
            up to 1% larger than a max constraint without generating a
            failure, and minimum values can be up to 1% smaller than the
            minimum constraint value without generating a failure. (These
            are modified, as appropriate, for negative values.)

            If not specified, an epsilon of 0 is used, so there is no
            tolerance.

            NOTE: A consequence of the fact that these are proportionate
            is that min/max values of zero do not have any tolerance,
            i.e. the wrong sign always generates a failure.

        type_checking: ``'strict'``, ``'sloppy'``, or ``'loose'``
            (``'loose'`` and ``'sloppy'`` are equivalent). Defaults to
            ``'sloppy'`` for Pandas, because Pandas silently promotes
            integer and boolean columns to reals and objects when they
            contain nulls. With ``'sloppy'``/``'loose'``, such promotions
            do not generate type failures. With ``'strict'``, a ``float``
            column ``c`` may only satisfy an ``int`` constraint if
            ``c.dropna().astype(int) == c.dropna()``, and similarly
            Object fields will satisfy a ``bool`` constraint only if
            ``c.dropna().astype(bool) == c.dropna()``.
        repair: If ``True``, use constraint type information to repair
            potentially incorrect type inferences made when loading the
            DataFrame from CSV. Default is ``True``. Should not be used
            with DataFrames from reliable typed sources.
        report: ``'all'`` or ``'fields'``. Controls the behaviour of
            ``__str__`` on the resulting ``PandasVerification`` object
            (but not its content).

            ``'all'`` (the default) means that all fields are shown,
            together with the verification status of each constraint for
            that field.

            If set to ``'fields'``, only fields for which at least one
            constraint failed are shown.

        engine: DataFrame engine: ``'pandas'`` or ``'polars'``.
        backend: Pandas backend: ``'numpy_nullable'`` (or ``'n'``),
            ``'pyarrow'`` (or ``'a'``), or ``'original'`` (or ``'o'``).
        config: Optional configuration object or path.
        **kwargs: Additional keyword arguments passed to the verifier.

    Returns:
        PandasVerification: Verification results, with ``passes`` and
        ``failures`` attributes. Use ``to_frame()`` to get results as a
        DataFrame, or ``str()`` to print a detailed report.

    Example::

        import pandas as pd
        from tdda.constraints import verify_df

        df = pd.DataFrame({'a': [0, 1, 2, 10, np.nan],
                           'b': ['one', 'one', 'two', 'three', np.nan]})
        v = verify_df(df, 'example_constraints.tdda')

        print('Constraints passing: %d\\n' % v.passes)
        print('Constraints failing: %d\\n' % v.failures)
        print(str(v))
        print(v.to_frame())

    See *simple_verification.py* in the :ref:`constraint_examples`
    for a slightly fuller example.
    """
    backend = get_backend(backend, config)
    pdv = PandasConstraintVerifier(
        df, epsilon=epsilon, type_checking=type_checking
    )
    if isinstance(constraints_path, dict):
        constraints = DatasetConstraints()
        constraints.initialize_from_dict(unicode_definite(constraints_path))
    else:
        constraints = DatasetConstraints(loadpath=constraints_path)
    if repair and backend == OG_BACKEND:
        pdv.repair_field_types(constraints)
    n_records = df.shape[0]
    return pdv.verify(
        constraints,
        VerificationClass=PandasVerification,
        report=report,
        n_source_records=n_records,
        **kwargs,
    )


def detect_df(
    df,
    constraints_path,
    epsilon=None,
    type_checking=None,
    outpath=None,
    write_all_records=False,
    per_constraint=False,
    output_fields=None,
    index=False,
    in_place=False,
    rownumber_is_index=True,
    int_bools=False,
    repair=True,
    report='records',
    backend=None,
    **kwargs,
):
    """Detect records in a DataFrame that fail any constraints in a
    ``.tdda`` file.

    Args:
        df: DataFrame to be checked (Pandas or Polars).
        constraints_path: Path to a JSON ``.tdda`` file, or an in-memory
            dictionary containing the structured contents of a ``.tdda``
            file.
        epsilon: Tolerance for min/max constraint checks, as a proportion
            of the constraint value. For example, ``0.01`` allows values
            up to 1% larger than a max constraint without generating a
            failure, and minimum values can be up to 1% smaller than the
            minimum constraint value without generating a failure. (These
            are modified, as appropriate, for negative values.)

            If not specified, an epsilon of 0 is used, so there is no
            tolerance.

            NOTE: A consequence of the fact that these are proportionate
            is that min/max values of zero do not have any tolerance,
            i.e. the wrong sign always generates a failure.

        type_checking: ``'strict'``, ``'sloppy'``, or ``'loose'``
            (``'loose'`` and ``'sloppy'`` are equivalent). Defaults to
            ``'sloppy'`` for Pandas, because Pandas silently promotes
            integer and boolean columns to reals and objects when they
            contain nulls. With ``'sloppy'``/``'loose'``, such promotions
            do not generate type failures. With ``'strict'``, a ``float``
            column ``c`` may only satisfy an ``int`` constraint if
            ``c.dropna().astype(int) == c.dropna()``, and similarly
            Object fields will satisfy a ``bool`` constraint only if
            ``c.dropna().astype(bool) == c.dropna()``.
        outpath: Path for a CSV or parquet output file containing
            detected (failing) records. By default only failing records
            are written; use ``write_all_records`` to include passing
            records too.

            By default, the output columns are a boolean ``ok`` field
            for each constraint on each field, and an ``n_failures``
            field containing the total number of constraints that failed
            for each row. This can be overridden with the
            ``per_constraint``, ``output_fields``, and ``index``
            parameters.
        write_all_records: If ``True``, include passing records in the
            detection output. Default is ``False``.
        per_constraint: If ``True``, write one indicator column per
            failing constraint in addition to ``n_failures``. Default
            is ``False``.
        output_fields: List of original columns to include in the
            detection output. Pass an empty list to include all original
            columns. Default is ``None``.
        index: If ``True``, include a row-number index (from 0) in the
            detection output. Automatically enabled if no
            ``output_fields`` are specified. Default is ``False``.
        in_place: If ``True``, add detection indicator columns directly
            to the input DataFrame. If ``outpath`` is also set, failing
            records are also written to file. Default is ``False``.
        rownumber_is_index: Set to ``False`` if the DataFrame was loaded
            from a CSV file, so that detection output refers to file row
            numbers rather than DataFrame index values. Default is
            ``True``.
        int_bools: If ``True``, write boolean indicator values as
            integers (``1``/``0``) rather than ``true``/``false``.
            Default is ``False``.
        repair: If ``True``, use constraint type information to repair
            potentially incorrect type inferences. Default is ``True``.
        report: ``'all'``, ``'fields'``, or ``'records'``. If set,
            a verification report is also produced. Default is
            ``'records'``.
        backend: Pandas backend: ``'numpy_nullable'`` (or ``'n'``),
            ``'pyarrow'`` (or ``'a'``), or ``'original'`` (or ``'o'``).
        **kwargs: Additional keyword arguments passed to the verifier.

    Returns:
        PandasDetection: Detection results. Use ``detected()`` to get
        the DataFrame of failing records.

    Example::

        import pandas as pd
        from tdda.constraints import detect_df

        df = pd.DataFrame({'a': [0, 1, 2, 10, np.nan],
                           'b': ['one', 'one', 'two', 'three', np.nan]})
        v = detect_df(df, 'example_constraints.tdda')
        detection_df = v.detected()
        print(detection_df.to_string())
    """
    pdv = PandasConstraintVerifier(
        df, epsilon=epsilon, type_checking=type_checking
    )
    constraints = constraints_from_path_or_dict(constraints_path)
    if repair:
        pdv.repair_field_types(constraints)
    n_records = df.shape[0]
    return pdv.detect(
        constraints,
        VerificationClass=PandasDetection,
        outpath=outpath,
        write_all_records=write_all_records,
        per_constraint=per_constraint,
        output_fields=output_fields,
        index=index,
        in_place=in_place,
        rownumber_is_index=rownumber_is_index,
        int_bools=int_bools,
        report=report,
        n_source_records=n_records,
        **kwargs,
    )


def discover_df(
    df,
    constraints_path=None,
    inc_rex=False,
    df_path=None,
    group_rexes=True,
    report_path=None,
    report_formats=None,
    engine=None,
    backend=None,
    no_md=False,
    allowed_fields=True,
    required_fields=True,
    verbose=None,
):
    """Discover constraints characterizing the Pandas DataFrame provided.

    Goes through each column and generates constraints that describe
    (and are satisfied by) the data. Assuming at least one constraint
    is found, returns a ``DatasetConstraints`` object with a ``fields``
    attribute keyed on the column name, and a ``to_json()`` method for
    saving as a ``.tdda`` constraints file. By convention, such files
    use a ``.tdda`` extension. The constraints file can then be used to
    check whether other datasets satisfy the same constraints.

    Returns ``None`` if no constraints were found.

    The kinds of constraints (potentially) generated for each field are:

    - **type**: the (coarse, TDDA) type of the field: ``'bool'``,
      ``'int'``, ``'real'``, ``'string'``, or ``'date'``.
    - **min**: for non-string fields, the minimum value in the column.
      Not generated for all-null columns.
    - **max**: for non-string fields, the maximum value in the column.
      Not generated for all-null columns.
    - **min_length**: for string fields, the length of the shortest
      string(s) in the field. N.B. In Python 2, this assumes strings
      are encoded in UTF-8, and an error may occur if not. String
      length counts unicode characters, not bytes.
    - **max_length**: for string fields, the length of the longest
      string(s) in the field. N.B. In Python 2, this assumes strings
      are encoded in UTF-8, and an error may occur if not. String
      length counts unicode characters, not bytes.
    - **sign**: if all values in a numeric field have consistent sign,
      a sign constraint is written with a value chosen from:

      - ``'positive'``     — for all values ``v`` in field: ``v > 0``
      - ``'non-negative'`` — for all values ``v`` in field: ``v >= 0``
      - ``'zero'``         — for all values ``v`` in field: ``v == 0``
      - ``'non-positive'`` — for all values ``v`` in field: ``v <= 0``
      - ``'negative'``     — for all values ``v`` in field: ``v < 0``
      - ``'null'``         — for all values ``v`` in field: ``v is null``

    - **max_nulls**: the maximum number of nulls allowed in the field.
      Set to 0 if the field has no nulls, 1 if it has a single null.
      Not generated if the field has more than one null.
    - **no_duplicates**: for string fields (only, for now), ``True``
      if every non-null value in the field is distinct. Only generated
      when all non-null values are unique; otherwise no constraint is
      written.
    - **allowed_values**: for string fields only, if there are
      ``MAX_CATEGORIES`` (currently 20) or fewer distinct values, an
      AllowedValues constraint listing them will be generated.
    - **rex**: for string fields only, a list of regular expressions
      such that each value in the field matches at least one of them.

    Args:
        df: Any Pandas DataFrame.
        constraints_path: Path to write the discovered constraints to.
            If ``None``, constraints are not written to file.
        inc_rex: If ``True``, include discovery of regular expressions
            for string fields using rexpy. Default is ``False``.
        df_path: The path from which the DataFrame was loaded, if any.
        group_rexes: If ``True``, include groups in variable parts of
            generated regular expressions. Default is ``True``.
        report_path: Path for reports (extension ignored). Writes
            reports to variations of this path if set; otherwise uses
            ``constraints_path``.
        report_formats: List of report formats to write. Options:
            ``'html'``, ``'markdown'`` (or ``'md'``), ``'text'`` (or
            ``'txt'``), ``'yaml'``, ``'json'``, ``'toml'``.
        engine: Engine to use (``'pandas'`` or ``'polars'``).
        backend: Pandas backend to use.
        no_md: If ``True``, metadata is omitted from the ``.tdda``
            file. Default is ``False``.
        allowed_fields: If ``False``, no ``allowed_fields`` entry is
            generated. Default is ``True``.
        required_fields: If ``False``, no ``required_fields`` entry is
            generated. Default is ``True``.

    Returns:
        DatasetConstraints: Discovered constraints, or ``None`` if no
        constraints were found.

    Example::

        import pandas as pd
        from tdda.constraints import discover_df

        df = pd.DataFrame({'a': [1, 2, 3], 'b': ['one', 'two', np.nan]})
        constraints = discover_df(df)
        with open('example_constraints.tdda', 'w') as f:
            f.write(constraints.to_json())

    See *simple_generation.py* in the :ref:`constraint_examples`
    for a slightly fuller example.
    """
    disco = PandasConstraintDiscoverer(
        df,
        inc_rex=inc_rex,
        group_rexes=group_rexes,
        no_md=no_md,
        allowed_fields=allowed_fields,
        required_fields=required_fields,
    )
    constraints = disco.discover()
    if constraints:
        constraints.set_dates_user_host_creator()
        constraints.set_source(df_path)
        constraints.set_stats(n_records=len(df), n_selected=len(df))
        write_constraints(
            constraints,
            constraints_path,
            report_path=report_path or constraints_path,
            report_formats=report_formats,
            verbose=verbose,
        )

    return constraints


def write_constraints(
    constraints,
    constraints_path,
    report_path=None,
    report_formats=None,
    verbose=False,
):
    out_json = constraints.to_json(tddafile=constraints_path)
    if constraints_path and constraints_path != '-':
        with open(constraints_path, 'w') as f:
            f.write(out_json)
        if report_formats:
            constraints.write_discovery_reports(
                report_path or constraints_path, report_formats
            )

    elif verbose or constraints_path == '-':
        print(out_json)


def file_format(path):
    if isinstance(path, StringIO):
        return 'csv'
    else:
        (stem, ext) = os.path.splitext(path)
        if not ext:
            return 'csv'
        return 'parquet' if ext[1:].lower() == 'parquet' else 'csv'


def load_df(path, md_path=None, find_md=False, backend=None, config=None):
    """
    Loads a pandas DataFrame from a path or stream.

    Args:
        path is usually a file path to be read, but can be a stream

        md_path is an optional path to an associated metadata file to use

        infer_metadata  If a CSV file ('.csv', '.psv', '.tsv' or '.txt' file)
                        is given and no metadata file is provided, this
                        setting will cause the software to look for
                        metadata using known patterns.
    """
    backend = get_backend(backend, config)
    if isinstance(path, StringIO):  # stream
        return default_csv_loader(path)
    exists = os.path.exists(os.path.expanduser(path))
    stem, ext = os.path.splitext(path)
    lcstem, ext = stem.lower(), ext.lower()

    path = handle_tilde(path)

    if ext == '.parquet':
        return pd.read_parquet(path, dtype_backend=backend)
    else:
        return csv_to_dataframe(
            path,
            md_path,
            find_md=find_md,
            infer_datetime_formats=True,
            backend=backend,
        )


def save_df(df, path, index=False):
    if path == '-' or path is None:
        print(default_csv_writer(df, None, index=index))
    else:
        fmt = file_format(path)
    if fmt == 'parquet':
        df.to_parquet(path=path, index=False)
    elif fmt in ('csv', 'psv', 'tsv', 'txt'):
        default_csv_writer(df, path, index=index)
    else:
        raise Exception(f'Unknown output format: {fmt}')


def unique_column_name(df, name):
    """
    Generate a column name that is not already present in the dataframe.
    """
    i = 1
    newname = name
    while newname in list(df):
        i += 1
        newname = '%s_%d' % (name, i)
    return newname


def detection_field(column, expr, default=None):
    """
    Construct a field for a detection result
    """
    if column.isnull().sum() == 0:
        return expr.astype(bool)
    else:
        null = np.nan if default is None else default  # np.nan  # pd.NA
        return np.where(pd.isnull(column), null, expr.astype('O'))


def convert_output_types(df, int_bools):
    """
    Construct a new DataFrame with boolean values mapped to appropriate
    string equivalents (usually "true" and "false", but optionally "1" and
    "0")
    """
    newdf = pd.DataFrame(index=df.index)
    trueval = '1' if int_bools else 'true'
    falseval = '0' if int_bools else 'false'
    pandas_true_values = (True, np.bool_(True))
    pandas_false_values = (True, np.bool_(False))
    for col in list(df):
        c = df[col]
        if c.dtype in (np.dtype('O'), np.dtype(bool)):
            newdf[col] = [
                (
                    trueval
                    if v in pandas_true_values
                    else falseval
                    if v in pandas_false_values
                    else v
                )
                for v in c
            ]
        else:
            newdf[col] = c
    return newdf


def is_pd_index_trivial(df):
    """
    Is this a trivial Pandas index (starting at 0, monotonic with no dups)?
    """
    if not isinstance(df.index, pd.RangeIndex):
        return False
    if not df.index.is_monotonic_increasing:
        return False
    if df.index.has_duplicates:
        return False
    if hasattr(df.index, 'start') and df.index.start != 0:
        # not clear why start can be missing with modern pandas;
        # but sometimes it seem to be
        return False
    return True


def verification_field(col, ctype):
    return '%s_%s_ok' % (col, CONSTRAINT_SUFFIX_MAP[ctype])


def df_fuzzy_gt(a, b, epsilon):
    """
    Returns a >~ b (a is greater than or approximately equal to b)

    At the moment, this simply reduces b by 1% if it is positive,
    and makes it 1% more negative if it is negative.
    """
    return (a >= b) | (a >= fuzz_down(b, epsilon))


def df_fuzzy_lt(a, b, epsilon):
    """
    Returns a <~ b (a is less than or approximately equal to b)

    At the moment, this increases b by 1% if it is positive,
    and makes it 1% less negative if it is negative.
    """
    return (a <= b) | (a <= fuzz_up(b, epsilon))


def is_ver_field(v, f):
    """Test whether v is a verification field for original field f"""
    L = len(f)
    if v[: L + 1] != f + '_':
        return False  # didn't start with f

    v = v[L + 1 :]
    has_digits = False
    while v and v[-1].isdigit():  # remove any trailing (disambiguation) digits
        v = v[:-1]
        has_digits = True
    if has_digits:
        if not v.endswith('_'):  # was only disamb. if ended _ddd
            return False
        v = v[:-1]  # remove the underscore

    if not v.endswith('_ok'):
        return False

    v = v[:-3]
    return v in STANDARD_CONSTRAINT_SUFFIXES


# for backwards compatibility (old name for function)
discover_constraints = discover_df
