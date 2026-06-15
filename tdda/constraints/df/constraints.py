# -*- coding: utf-8 -*-
"""
The ``tdda.constraints.df.constraints`` module provides an
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

from io import StringIO

import numpy as np
import pandas as pd
import polars as pl

from tdda.constraints.base import (
    STANDARD_FIELD_CONSTRAINTS,
    STANDARD_CONSTRAINT_SUFFIXES,
    CONSTRAINT_SUFFIX_MAP,
    unicode_definite,
    DatasetConstraints,
    Verification,
    Detection,
    constraints_from_path_or_dict,
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
    coltype_is_boolean,
    is_string_col,
    is_string_dtype,
    is_categorical_dtype,
)
from tdda.abstractdf import (
    all_non_nulls_boolean,
    calc_nunique,
    coarse_type,
    col_max,
    col_max_length,
    col_min,
    col_min_length,
    col_names,
    col_to_tdda_type,
    csv_to_dataframe,
    date_columns,
    detection_field,
    eltwise_is_duplicated,
    eltwise_isin,
    eltwise_isnull,
    eltwise_notnull,
    eltwise_str_len,
    filter_out_nulls,
    fuzzy_gt,
    fuzzy_lt,
    is_null,
    is_pandas_df,
    is_polars_df,
    non_integer_values_count,
    non_null_count,
    null_count,
    scalar_to_tdda_type,
    tdda_type,
    to_datetime,
    types_compatible,
    unique_values,
)


from tdda.referencetest.checkpandas import (
    default_csv_loader,
    default_csv_writer,
)
from tdda import rexpy

from tdda.serial.dfio import read_df as serial_read_df
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

DEBUG = False
RE_FLAGS = re.UNICODE | re.DOTALL


class DFConstraintCalculator(BaseConstraintCalculator):
    """
    Implementation of the Constraint Calculator methods for
    Pandas dataframes.
    """

    def __init__(self, df):
        self.df = df

    def is_null(self, value):
        return is_null(value)

    def to_datetime(self, value):
        return to_datetime(self.df, value)

    def get_column_names(self):
        return col_names(self.df)

    def get_nrecords(self):
        return len(self.df)

    def types_compatible(self, x, y, colname=None):
        return types_compatible(x, y, colname=colname)

    def calc_min(self, colname):
        return col_min(self.df[colname])

    def calc_max(self, colname):
        return col_max(self.df[colname])

    def calc_min_length(self, colname):
        return col_min_length(self.df[colname])

    def calc_max_length(self, colname):
        return col_max_length(self.df[colname])

    def calc_tdda_type(self, colname):
        return tdda_type(self.df[colname])

    def calc_null_count(self, colname):
        return null_count(self.df[colname])

    def calc_non_null_count(self, colname):
        return non_null_count(self.df[colname])

    def calc_nunique(self, colname):
        return int(calc_nunique(self.df[colname]))

    def calc_unique_values(self, colname, include_nulls=True):
        return unique_values(self.df[colname], include_nulls=include_nulls)

    def calc_non_integer_values_count(self, colname):
        return non_integer_values_count(self.df[colname])

    def calc_all_non_nulls_boolean(self, colname):
        return all_non_nulls_boolean(self.df[colname])

    # def allowed_values_exclusions(self):
    #     # remarkably, Pandas returns various kinds of nulls as
    #     # unique values, despite not counting them with .nunique()
    #     return [None, np.nan, pd.NaT, pd.NA, float('nan')]

    def filter_out_nulls(self, values):
        return filter_out_nulls(values)

    def find_rexes(self, colname, values=None, seed=None):
        if values is None:
            return rexpy.dfextract(self.df[colname], tag=self.group_rexes)
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
            unicode_definite(s)
            for s in unique_values(self.df[colname], include_nulls=False)
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


class DFConstraintDetector(BaseConstraintDetector):
    """
    Implementation of the Constraint Detector methods for
    Pandas dataframes.
    """

    def __init__(self, df):
        self.df = df
        if df is not None:
            self.date_cols = date_columns(df)
            if is_polars_df(df):
                self.out_df = None
                self.out_cols = {}
            else:
                index = df.index.copy()
                if not index.name:
                    index.name = 'Index'
                self.out_df = pd.DataFrame(index=index)
        else:
            self.date_cols = []
            self.out_df = None

    def _add_detect_col(self, name, value):
        if is_polars_df(self.df):
            self.out_cols[name] = value
        else:
            self.out_df[name] = value

    def detect_min_constraint(self, colname, value, precision, epsilon):
        name = verification_field(colname, 'min')
        c = self.df[colname]
        if not types_compatible(c, value):
            self._add_detect_col(name, False)
        elif precision == 'closed' or colname in self.date_cols:
            self._add_detect_col(name, detection_field(c, c >= value))
        elif precision == 'open':
            self._add_detect_col(name, detection_field(c, c > value))
        else:
            self._add_detect_col(name, detection_field(
                c, fuzzy_gt(c, value, epsilon)
            ))

    def detect_max_constraint(self, colname, value, precision, epsilon):
        name = verification_field(colname, 'max')
        c = self.df[colname]
        if not types_compatible(c, value):
            self._add_detect_col(name, False)
        elif precision == 'closed' or colname in self.date_cols:
            self._add_detect_col(name, detection_field(c, c <= value))
        elif precision == 'open':
            self._add_detect_col(name, detection_field(c, c < value))
        else:
            self._add_detect_col(name, detection_field(
                c, fuzzy_lt(c, value, epsilon)
            ))

    def detect_min_length_constraint(self, colname, value):
        name = verification_field(colname, 'min_length')
        c = self.df[colname]
        if coarse_type(c) != 'string':
            self._add_detect_col(name, False)
        else:
            self._add_detect_col(name, detection_field(c, eltwise_str_len(c) >= value))

    def detect_max_length_constraint(self, colname, value):
        name = verification_field(colname, 'max_length')
        c = self.df[colname]
        if coarse_type(c) != 'string':
            self._add_detect_col(name, False)
        else:
            self._add_detect_col(name, detection_field(c, eltwise_str_len(c) <= value))

    def detect_tdda_type_constraint(self, colname, value):
        name = verification_field(colname, 'type')
        self._add_detect_col(name, False)

    def detect_sign_constraint(self, colname, value):
        name = verification_field(colname, 'sign')
        c = self.df[colname]

        if coarse_type(c) == 'number':
            if value == 'null':
                self._add_detect_col(name, False)
            elif value == 'positive':
                self._add_detect_col(name, detection_field(c, c > 0))
            elif value == 'non-negative':
                self._add_detect_col(name, detection_field(c, c >= 0))
            elif value == 'zero':
                self._add_detect_col(name, detection_field(c, c == 0))
            elif value == 'non-positive':
                self._add_detect_col(name, detection_field(c, c <= 0))
            elif value == 'negative':
                self._add_detect_col(name, detection_field(c, c < 0))

    def detect_max_nulls_constraint(self, colname, value):
        # found more nulls than are allowed, so mark all null values as bad
        name = verification_field(colname, 'max_nulls')
        c = self.df[colname]
        self._add_detect_col(name, eltwise_notnull(c))

    def detect_no_duplicates_constraint(self, colname, value):
        # found duplicates, so mark anything duplicated as bad
        name = verification_field(colname, 'no_duplicates')
        c = self.df[colname]
        unique = ~eltwise_is_duplicated(self.df, colname)
        self._add_detect_col(name, detection_field(c, unique, default=True))

    def detect_allowed_values_constraint(
        self, colname, allowed_values, violations
    ):
        name = verification_field(colname, 'allowed_values')
        c = self.df[colname]
        self._add_detect_col(name, detection_field(c, ~eltwise_isin(c, violations)))

    def detect_rex_constraint(self, colname, violations):
        name = verification_field(colname, 'rex')
        c = self.df[colname]
        if coarse_type(c) != 'string':
            self._add_detect_col(name, False)
        else:
            self._add_detect_col(name, detection_field(c, ~eltwise_isin(c, violations)))

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
        if is_polars_df(self.df):
            return self._write_detected_records_polars(
                outpath=outpath,
                write_all_records=write_all_records,
                per_constraint=per_constraint,
                output_fields=output_fields,
                index=index,
                in_place=in_place,
                rownumber_is_index=rownumber_is_index,
                int_bools=int_bools,
                interleave=interleave,
                **kwargs,
            )
        return self._write_detected_records_pandas(
            outpath=outpath,
            write_all_records=write_all_records,
            per_constraint=per_constraint,
            output_fields=output_fields,
            index=index,
            in_place=in_place,
            rownumber_is_index=rownumber_is_index,
            int_bools=int_bools,
            interleave=interleave,
            **kwargs,
        )

    def _write_detected_records_pandas(
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

    def _write_detected_records_polars(
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
        if not self.out_cols:
            return None
        orig_fields = list(self.df.columns)
        output_is_typed = outpath and file_format(outpath) == 'parquet'

        n = len(self.df)
        broadcast_cols = {
            k: v if isinstance(v, pl.Series) else pl.Series(k, [v] * n)
            for k, v in self.out_cols.items()
        }
        out_df = pl.DataFrame(broadcast_cols)
        add_index = index or output_fields is None
        if output_fields is None:
            output_fields = []
        elif len(output_fields) == 0:
            output_fields = list(self.df.columns)

        nfailname = (
            'n_failures'
            if 'n_failures' not in self.df.columns
            else 'n_tdda_failures'
        )
        cols = out_df.columns
        nf = len(cols)
        true_sum = out_df.select(
            pl.sum_horizontal([pl.col(c).cast(pl.Float64) for c in cols])
        ).to_series()
        null_sum = out_df.select(
            pl.sum_horizontal(
                [pl.col(c).is_null().cast(pl.Float64) for c in cols]
            )
        ).to_series()
        fails = pl.Series([float(nf)] * len(out_df)) - true_sum - null_sum
        out_df = out_df.with_columns(
            fails.cast(pl.Int64).alias(nfailname)
        )
        n_failing_records = int((fails > 0).sum())
        n_passing_records = len(self.df) - n_failing_records

        if not per_constraint:
            fnames = [n for n in out_df.columns if n != nfailname]
            out_df = out_df.drop(fnames)

        if in_place:
            for fname in out_df.columns:
                newname = unique_column_name(self.df, fname)
                self.df = self.df.with_columns(
                    out_df[fname].alias(newname)
                )

        if output_fields:
            for fname in reversed(output_fields):
                if fname in self.df.columns:
                    if fname in self.out_cols:
                        warn(f'Replacing old field {fname}.')
                    else:
                        out_df = out_df.insert_column(0, self.df[fname])
                else:
                    raise Exception(
                        'DataFrame has no column %s' % fname
                    )

        if interleave:
            out_df = self.interleave(out_df, orig_fields, nfailname)

        if outpath:
            if output_is_typed:
                df_to_save = out_df
            else:
                df_to_save = polars_convert_output_types(out_df, int_bools)
            if add_index:
                stem = 'Index' if rownumber_is_index else 'RowNumber'
                idxname = unique_column_name(df_to_save, stem)
                idx = pl.Series(idxname, range(1, len(df_to_save) + 1))
                df_to_save = df_to_save.insert_column(0, idx)
            if not write_all_records:
                df_to_save = df_to_save.filter(
                    pl.col(nfailname) > 0
                )
            save_df(df_to_save, outpath, index=False)

        if not write_all_records:
            out_df = out_df.filter(pl.col(nfailname) > 0)
        return Detection(out_df, n_passing_records, n_failing_records)

    def interleave(self, df, orig_fields, nfailname):
        df_cols = col_names(df)
        if set(orig_fields) - set(df_cols):
            return df
            # Only interleave if all of the original fields
            # are in the output

        all_vfields = set(df_cols) - set(orig_fields) - set([nfailname])
        new_fields = []
        for f in orig_fields:
            new_fields.append(f)
            new_fields.extend(
                sorted([v for v in all_vfields if is_ver_field(v, f)])
            )
        new_fields.append(nfailname)
        if DEBUG and set(df_cols) != set(new_fields):
            print('col_names(df)', df_cols, len(df_cols))
            print('new fields', new_fields, len(new_fields))
        assert set(df_cols) == set(new_fields)
        return df[new_fields]


class DFConstraintVerifier(
    DFConstraintCalculator,
    DFConstraintDetector,
    BaseConstraintVerifier,
):
    """
    Provides methods for verifying every type of constraint against
    a Pandas DataFrame.
    """

    def __init__(self, df, epsilon=None, type_checking=None):
        DFConstraintCalculator.__init__(self, df)
        DFConstraintDetector.__init__(self, df)
        BaseConstraintVerifier.__init__(
            self, epsilon=epsilon, type_checking=type_checking
        )

    def repair_field_types(self, constraints):
        repair_field_types(self.df, constraints)


class DFVerification(Verification):
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
        df_obj = self.detection.obj
        df_cols = col_names(df_obj)
        exists = indicator_field in df_cols and field in df_cols
        if exists:
            if is_polars_df(df_obj):
                df = df_obj.filter(
                    pl.col(indicator_field) == self.bad_val
                )
            else:
                df = df_obj.query(
                    f'{indicator_field} == {self.bad_val}'
                )
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
        if ok_field in col_names(df):
            if is_polars_df(df):
                failures = int((df[ok_field] == False).sum())
            else:
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
            }.intersection(set(col_names(df)))
        )
        if len(indicators) == 0:  # no failures
            nf = 0
        elif is_polars_df(df):
            nf = df.filter(
                pl.any_horizontal(
                    [pl.col(ind) == self.bad_val for ind in indicators]
                )
            ).shape[0]
        else:
            nf = df.query(
                ' | '.join(
                    f'{indicator} == {self.bad_val}'
                    for indicator in indicators
                )
            ).shape[0]
        return PassFailCount(field, self.detection.n_source_records - nf, nf)


class DFDetection(DFVerification):
    """Detection result for a Pandas DataFrame.

    Extends ``DFVerification`` with a ``detected()`` method giving
    access to the detected records as a Pandas DataFrame.

    Attributes:
        n_passing_records: Number of records that passed all constraints.
        n_failing_records: Number of records that failed at least one
            constraint.

    Returned by ``detect_df``.
    """

    def __init__(self, *args, **kwargs):
        DFVerification.__init__(self, *args, **kwargs)

    def detected(self):
        """Return a DataFrame of detected (failing) records.

        Returns:
            DataFrame of records that failed at least one constraint,
            or ``None`` if there were no failures and ``write_all_records``
            was not set.
        """
        return self.detection.obj if self.detection else None


class DFConstraintDiscoverer(
    DFConstraintCalculator, BaseConstraintDiscoverer
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
        DFConstraintCalculator.__init__(self, df)
        BaseConstraintDiscoverer.__init__(
            self,
            inc_rex=inc_rex,
            group_rexes=group_rexes,
            no_md=no_md,
            allowed_fields=allowed_fields,
            required_fields=required_fields,
        )


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
            ``__str__`` on the resulting ``DFVerification`` object
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
        DFVerification: Verification results, with ``passes`` and
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
    pdv = DFConstraintVerifier(
        df, epsilon=epsilon, type_checking=type_checking
    )
    if isinstance(constraints_path, dict):
        constraints = DatasetConstraints()
        constraints.initialize_from_dict(unicode_definite(constraints_path))
    else:
        constraints = DatasetConstraints(loadpath=constraints_path)
    if repair and backend == OG_BACKEND and is_pandas_df(df):
        pdv.repair_field_types(constraints)
    n_records = df.shape[0]
    return pdv.verify(
        constraints,
        VerificationClass=DFVerification,
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
        DFDetection: Detection results. Use ``detected()`` to get
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
    pdv = DFConstraintVerifier(
        df, epsilon=epsilon, type_checking=type_checking
    )
    constraints = constraints_from_path_or_dict(constraints_path)
    if repair and is_pandas_df(df):
        pdv.repair_field_types(constraints)
    n_records = df.shape[0]
    return pdv.detect(
        constraints,
        VerificationClass=DFDetection,
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
        with open('example_constraints.tdda', 'w', encoding='utf-8') as f:
            f.write(constraints.to_json())

    See *simple_generation.py* in the :ref:`constraint_examples`
    for a slightly fuller example.
    """
    disco = DFConstraintDiscoverer(
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
        with open(constraints_path, 'w', encoding='utf-8') as f:
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


def load_df(path, md_path=None, find_md=False, engine=None,
            backend=None, config=None):
    """
    Loads a DataFrame from a path or stream.

    Args:
        path is usually a file path to be read, but can be a StringIO
        stream (pandas-only fallback).

        md_path is an optional path to an associated metadata file to use

        find_md  If a CSV file ('.csv', '.psv', '.tsv' or '.txt' file)
                 is given and no metadata file is provided, this setting
                 will cause the software to look for metadata using known
                 patterns.

        engine  'pandas' or 'polars'. Defaults to config, then 'pandas'.

        backend  Pandas dtype backend ('numpy_nullable', 'pyarrow', etc.).
    """
    if isinstance(path, StringIO):  # stream: pandas-only path
        return default_csv_loader(path)
    stem, ext = os.path.splitext(path)
    ext = ext.lower()
    path = handle_tilde(path)
    if ext == '.parquet':
        df = serial_read_df(
            path,
            engine=engine,
            backend=backend,
            config=config,
        )
    else:
        df = csv_to_dataframe(
            path,
            md_path,
            find_md=find_md,
            infer_datetime_formats=True,
            engine=engine,
            backend=backend,
            config=config,
        )
    return df



def save_df(df, path, index=False):
    if path == '-' or path is None:
        print(default_csv_writer(df, None, index=index))
    else:
        fmt = file_format(path)
        if fmt == 'parquet':
            if is_polars_df(df):
                df.write_parquet(path)
            else:
                df.to_parquet(path=path, index=False)
        elif fmt in ('csv', 'psv', 'tsv', 'txt'):
            if is_polars_df(df):
                df.write_csv(path)
            else:
                default_csv_writer(df, path, index=index)
        else:
            raise Exception(f'Unknown output format: {fmt}')


def repair_field_types(df, constraints):
    # Use constraint type info to fix columns mistyped on CSV read
    # (e.g. a string field containing only digits may look numeric).
    for c in col_names(df):
        if c not in constraints:
            continue
        ser = df[c]
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
                        is_real = non_integer_values_count(ser) > 0
                    df[c] = np.where(
                        ser.notnull(), ser.astype(str), np.nan
                    )
                    if not is_real:
                        df[c] = df[c].str.replace('.0', '', regex=False)
            elif ctype == 'bool' and str(dtype).lower().startswith('int'):
                df[c] = ser.astype(bool)
        except Exception as e:
            print('%s: %s' % (e.__class__.__name__, str(e)))


def unique_column_name(df, name):
    """
    Generate a column name that is not already present in the dataframe.
    """
    i = 1
    newname = name
    while newname in col_names(df):
        i += 1
        newname = '%s_%d' % (name, i)
    return newname


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
    pandas_false_values = (False, np.bool_(False))
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


def polars_convert_output_types(df, int_bools):
    """
    Polars equivalent of convert_output_types: map boolean columns to
    string true/false (or 1/0 if int_bools).
    """
    trueval = '1' if int_bools else 'true'
    falseval = '0' if int_bools else 'false'
    exprs = []
    for col in df.columns:
        if df[col].dtype == pl.Boolean:
            exprs.append(
                pl.when(pl.col(col).is_null())
                .then(pl.lit(None, dtype=pl.String))
                .when(pl.col(col))
                .then(pl.lit(trueval))
                .otherwise(pl.lit(falseval))
                .alias(col)
            )
        else:
            exprs.append(pl.col(col))
    return df.select(exprs)


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
