# -*- coding: utf-8 -*-
"""
The :py:mod:`tdda.constraints.pd.constraints` module provides an
implementation of TDDA constraint discovery and verification
for Pandas DataFrames.

This allows it to be used for data in CSV files, or for Pandas or R
DataFrames saved as Feather files.

The top-level functions are:

    :py:func:`tdda.constraints.discover_df`:
        Discover constraints from a Pandas DataFrame.

    :py:func:`tdda.constraints.verify_df`:
        Verify (check) a Pandas DataFrame, against a set of previously
        discovered constraints.

    :py:func:`tdda.constraints.detect_df`:
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

from tdda.deprecated.featherfiles import read_feather_file, write_feather_file

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
    native_definite,
    DatasetConstraints,
    Verification,
    Detection,
    fuzz_up, fuzz_down,
)
from tdda.constraints.baseconstraints import (
    BaseConstraintCalculator,
    BaseConstraintDetector,
    BaseConstraintVerifier,
    BaseConstraintDiscoverer,
    MAX_CATEGORIES,
    unicode_string, byte_string, long_type
)
from tdda.pd.utils import is_string_col, is_string_dtype, is_categorical_dtype

from tdda.referencetest.checkpandas import (default_csv_loader,
                                            default_csv_writer)
from tdda import rexpy

from tdda.serial.reader import load_metadata
from tdda.serial.utils import (
    find_associated_metadata_file,
    find_metadata_type_from_path
)
from tdda.serial.pandasio import to_pandas_read_csv_args

# pd.tslib is deprecated in newer versions of Pandas
if hasattr(pd, 'Timestamp'):
    pandas_Timestamp = pd.Timestamp
else:
    pandas_Timestamp = pd.tslib.Timestamp

isPy3 = sys.version_info[0] >= 3

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
        if isPy3:
            return self.df[colname].str.len().min()
        else:
            return self.df[colname].str.decode('UTF-8').str.len().min()

    def calc_max_length(self, colname):
        if isPy3:
            return self.df[colname].str.len().max()
        else:
            return self.df[colname].str.decode('UTF-8').str.len().max()

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
        nullvalues = ([v for v in self.df[colname].unique()
                         if pd.isnull(v)] if include_nulls
                      else [])
        nonnullvalues = [v for v in values if not pd.isnull(v)]
        return nullvalues + sorted(nonnullvalues)

    def calc_non_integer_values_count(self, colname):
        values = self.df[colname].dropna()
        non_nulls = self.df[colname].count()
        return int(non_nulls
                   - (values.astype(int) == values).astype(int).sum())

    def calc_all_non_nulls_boolean(self, colname):
        nn = self.df[colname].dropna()
        return all([type(v) is bool for i, v in nn.iteritems()])

    def allowed_values_exclusions(self):
        # remarkably, Pandas returns various kinds of nulls as
        # unique values, despite not counting them with .nunique()
        return [None, np.nan, pd.NaT]

    def find_rexes(self, colname, values=None, seed=None):
        if values is None:
            return rexpy.pdextract(self.df[colname])
        else:
            return rexpy.extract(values, seed=None)

    def calc_rex_constraint(self, colname, constraint, detect=False):
        # note that this should return a set of violations, not True/False.
        rexes = constraint.value
        if rexes is None:      # a null value is not considered
            return None        # to be an active constraint,
                               # so is always satisfied
        rexes = [re.compile(r, RE_FLAGS) for r in rexes]
        strings = [native_definite(s)
                   for s in self.df[colname].dropna().unique()]

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
            self.out_df[name] = detection_field(c, df_fuzzy_gt(c, value,
                                                               epsilon))

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
            self.out_df[name] = detection_field(c, df_fuzzy_lt(c, value,
                                                               epsilon))

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
        unique = ~ self.df.duplicated(colname, keep=False)
        self.out_df[name] = detection_field(c, unique, default=True)

    def detect_allowed_values_constraint(self, colname, allowed_values,
                                         violations):
        name = verification_field(colname, 'allowed_values')
        c = self.df[colname]
        self.out_df[name] = detection_field(c, ~ c.isin(violations))

    def detect_rex_constraint(self, colname, violations):
        name = verification_field(colname, 'rex')
        c = self.df[colname]
        if pandas_coarse_type(c) != 'string':
            self.out_df[name] = False
        else:
            self.out_df[name] = detection_field(c, ~ c.isin(violations))

    def write_detected_records(self,
                               detect_outpath=None,
                               detect_write_all=False,
                               detect_per_constraint=False,
                               detect_output_fields=None,
                               detect_index=False,
                               detect_in_place=False,
                               rownumber_is_index=True,
                               boolean_ints=False,
                               interleave=False,
                               **kwargs):
        if self.out_df is None:
            return None
        orig_fields = list(self.df)
        output_is_typed = (
            detect_outpath
            and file_format(detect_outpath) in ('parquet', 'feather')
        )
        output_is_feather = (detect_outpath
                             and file_format(detect_outpath) == 'feather')

        out_df = self.out_df
        add_index = detect_index or detect_output_fields is None
        if detect_output_fields is None:
            detect_output_fields = []
        elif len(detect_output_fields) == 0:
            detect_output_fields = list(self.df)

        nfailname = 'n_failures'
        nf = len(list(out_df))
        fails = (nf - out_df.sum(axis=1).astype(float)
                    - out_df.isnull().sum(axis=1).astype(float))
        out_df[nfailname] = fails.astype(int)
        n_failing_records = (fails > 0).astype(int).sum()
        n_passing_records = len(out_df) - n_failing_records

        if not detect_per_constraint:
            fnames = [name for name in list(out_df) if name != nfailname]
            out_df = out_df.drop(fnames, axis=1)

        if detect_in_place:
            for fname in list(out_df):
                newfield = out_df[fname]
                self.df[unique_column_name(self.df, fname)] = newfield

        if detect_output_fields:
            for fname in reversed(detect_output_fields):
                if fname in list(self.df):
                    out_df.insert(0, fname, self.df[fname])
                else:
                    raise Exception('DataFrame has no column %s' % fname)

        if interleave:
            out_df = self.interleave(out_df, orig_fields, nfailname)
#             if detect_in_place:  # does not work in place
#                 self.interleave(self.df, orig_fields, nfailname)

        if detect_outpath:
            index_is_trivial = is_pd_index_trivial(out_df)
            if output_is_typed:
                df_to_save = out_df
            else:
                df_to_save = convert_output_types(out_df, boolean_ints)
            if add_index:
                # Add Index or RowNumber columns to output CSV file (or
                # add appropriate columns to output feather file and reset
                # its index, because feather doesn't support MultiIndexes
                # and doesn't retain single indexes).
                #
                # TODO: If the feather file is going to be saved using
                #       pmmif's featherpmm, and if featherpmm were able to
                #       transparently retain indexes, then we wouldn't need
                #       to do that in this case (when featherpmm is set, and
                #       output_is_typed).
                indexes = []
                if output_is_feather or rownumber_is_index:
                    stem = 'Index' if rownumber_is_index else 'RowNumber'
                    if isinstance(df_to_save.index, pd.MultiIndex):
                        for i, level in enumerate(df_to_save.index.levels):
                            name = (df_to_save.index.names[i]
                                    if df_to_save.index.names
                                    else '%s_%d' % (stem, (i+1)))
                            pair = (unique_column_name(df_to_save, name),
                                    df_to_save.index.get_level_values(i))
                            indexes.append(pair)
                    else:
                        indexes.append((unique_column_name(df_to_save, stem),
                                        df_to_save.index))
                    df_to_save.reset_index(inplace=True, drop=True)
                else:
                    pair = (unique_column_name(df_to_save, 'RowNumber'),
                            pd.RangeIndex(1, len(df_to_save)+1))
                    indexes.append(pair)
                for name, index in reversed(indexes):
                    df_to_save.insert(0, name, index)

            if not detect_write_all:
                df_to_save = df_to_save[df_to_save[nfailname] > 0]
            save_df(df_to_save, detect_outpath, index=False)

        if not detect_write_all:
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
            new_fields.extend(sorted([v for v in all_vfields
                                      if is_ver_field(v, f)]))
        new_fields.append(nfailname)
        if DEBUG and set(list(df)) != set(new_fields):
            print('list(df))', list(df), len(list(df)))
            print('new fields', new_fields, len(new_fields))
        assert set(list(df)) == set(new_fields)
        return df[new_fields]


class PandasConstraintVerifier(PandasConstraintCalculator,
                               PandasConstraintDetector,
                               BaseConstraintVerifier):
    """
    A :py:class:`PandasConstraintVerifier` object provides methods
    for verifying every type of constraint against a Pandas DataFrame.
    """
    def __init__(self, df, epsilon=None, type_checking=None):
        PandasConstraintCalculator.__init__(self, df)
        PandasConstraintDetector.__init__(self, df)
        BaseConstraintVerifier.__init__(self, epsilon=epsilon,
                                        type_checking=type_checking)

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
                            if type(limitval) in (int, long_type, float):
                                if type(limitval) == float:
                                    is_real = True
                            else:
                                is_numeric = False
                                break
                    if is_numeric:
                        if is_real:
                            is_real = self.calc_non_integer_values_count(c) > 0
                        self.df[c] = np.where(ser.notnull(),
                                              ser.astype(str),
                                              np.nan)
                        if not is_real:
                            self.df[c] = self.df[c].str.replace('.0', '',
                                                                regex=False)
                elif ctype == 'bool' and str(dtype).lower().startswith('int'):
                    self.df[c] = ser.astype(bool)
            except Exception as e:
                print('%s: %s' % (e.__class__.__name__, str(e)))


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
    - ``np.NaN``  --- if there was no constraint of this kind

    This Pandas-specific implementation of constraint verification also
    provides methods :py:meth:`to_frame` to get the overall verification
    result as as a Pandas DataFrame, and :py:meth:`detected` to get any
    detection results as a a Pandas DataFrame (if the verification has been
    run with in ``detect`` mode).
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

    to_dataframe = to_frame


class PandasDetection(PandasVerification):
    """
    A :py:class:`PandasDetection` object adds a :py:meth:`detected()`
    method to a :py:class:`PandasVerification` object.

    This allows the Pandas DataFrame resulting from constraint detection
    to be made available.

    The object also provides properties `n_passing_records` and
    `n_failing_records`, recording how many records passed and failed
    the detection process.
    """
    def __init__(self, *args, **kwargs):
        PandasVerification.__init__(self, *args, **kwargs)

    def detected(self):
        """
        Returns a Pandas DataFrame containing the detection results.

        If there are no failing records, and the detection was not run
        with the `write_all` flag set, then ``None`` is returned.
        """
        return self.detection.obj if self.detection else None


class PandasConstraintDiscoverer(PandasConstraintCalculator,
                                 BaseConstraintDiscoverer):
    """
    A :py:class:`PandasConstraintDiscoverer` object is used to discover
    constraints on a Pandas DataFrame.
    """
    def __init__(self, df, inc_rex=False):
        PandasConstraintCalculator.__init__(self, df)
        BaseConstraintDiscoverer.__init__(self, inc_rex=inc_rex)


def pandas_types_compatible(x, y, colname=None):
    """
    Returns boolean indicating whether the coarse_type of *x* and *y* are
    the same, for scalar values.

    If *colname* is provided, and the check fails, a warning is issued
    to stderr.
    """
    ok = pandas_coarse_type(x) == pandas_coarse_type(y)
    if not ok and colname:
        print('Warning: Failing incompatible types constraint for field %s '
              'of type %s.\n(Constraint value %s of type %s.)'
              % (colname, type(x), y, type(y)), file=sys.stderr)
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
    if dt == np.dtype('O'):
        # objects could be either strings or booleans-with-nulls or dates
        for v in x:
            if type(v) in (bool, np.bool_):
                return 'bool'
            elif type(v) in (unicode_string, byte_string):
                return 'string'
            elif isinstance(v, datetime.datetime):
                return 'date'
            elif isinstance(v, datetime.date):
                return 'date'
        # if it was all null, there's no way to tell its type, so say string
        return 'string'
    if is_categorical_dtype(dt):
        return 'string'
    dts = str(dt).lower()
    if type(x) == bool or 'bool' in dts:
        return 'bool'
    if type(x) in (int, long_type) or 'int' in dts:
        return 'int'
    if type(x) == float or 'float' in dts:
        return 'real'
    if ('date' in dts
                or isinstance(x, datetime.datetime)
                or isinstance(x, datetime.date)
                or isinstance(x, pandas_Timestamp)):
        return 'date'
    if x is None:
        return 'null'
    null = pd.isnull(x)
    if hasattr(null, 'size'):
        null = False  # pd.isnull returned an array
    if (not isinstance(x, pd.core.series.Series) and null):
        return 'null'
    # Everything else is other, for now, including compound types,
    return 'other'


def verify_df(df, constraints_path, epsilon=None, type_checking=None,
              repair=True, report='all', **kwargs):
    """
    Verify that (i.e. check whether) the Pandas DataFrame provided
    satisfies the constraints in the JSON ``.tdda`` file provided.

    Mandatory Inputs:

        *df*:
                            A Pandas DataFrame, to be checked.

        *constraints_path*:
                            The path to a JSON ``.tdda`` file (possibly
                            generated by the discover_df function, below)
                            containing constraints to be checked.
                            Or, alternatively, an in-memory dictionary
                            containing the structured contents of a ``.tdda``
                            file.

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
                            ``strict`` or ``sloppy``.
                            Because Pandas silently, routinely and
                            automatically "promotes" integer and boolean
                            columns to reals and objects respectively
                            if they contain nulls, strict type checking
                            can be problematical in Pandas. For this reason,
                            ``type_checking`` defaults to ``sloppy``, meaning
                            that type changes that could plausibly be
                            attributed to Pandas type promotion will not
                            generate constraint values.

                            If this is set to strict, a Pandas ``float``
                            column ``c`` will only be allowed to satisfy a
                            an ``int`` type constraint if::

                                c.dropnulls().astype(int) == c.dropnulls()

                            Similarly, Object fields will satisfy a
                            ``bool`` constraint only if::

                                c.dropnulls().astype(bool) == c.dropnulls()

        *repair*:
                            A boolean to specify whether to try to use the
                            information in the constraints to attempt to
                            repair potentially-incorrect type inferrences
                            made when constructing the dataframe. When the
                            dataframe has been loaded from a .csv file, this
                            can often be useful (but should not be used with
                            dataframes that have come from a more reliable
                            source).

        *report*:
                            ``all`` or ``fields``.
                            This controls the behaviour of the
                            :py:meth:`~tdda.constraints.pd.constraints.PandasVerification.__str__` method on
                            the resulting :py:class:`~tdda.constraints.pd.constraints.PandasVerification`
                            object (but not its content).

                            The default is ``all``, which means that
                            all fields are shown, together with the
                            verification status of each constraint
                            for that field.

                            If report is set to ``fields``, only fields for
                            which at least one constraint failed are shown.

    Returns:

        :py:class:`~tdda.constraints.pd.constraints.PandasVerification` object.

        This object has attributes:

        - *passes*      --- Number of passing constraints
        - *failures*    --- Number of failing constraints

        It also has a :py:meth:`~tdda.constraints.pd.constraints.PandasVerification.to_frame()` method for
        converting the results of the verification to a Pandas DataFrame,
        and a :py:meth:`~tdda.constraints.pd.constraints.PandasVerification.__str__` method to print
        both the detailed and summary results of the verification.

    Example usage::

        import pandas as pd
        from tdda.constraints import verify_df

        df = pd.DataFrame({'a': [0, 1, 2, 10, np.NaN],
                           'b': ['one', 'one', 'two', 'three', np.NaN]})
        v = verify_df(df, 'example_constraints.tdda')

        print('Constraints passing: %d\\n' % v.passes)
        print('Constraints failing: %d\\n' % v.failures)
        print(str(v))
        print(v.to_frame())

    See *simple_verification.py* in the :ref:`constraint_examples`
    for a slightly fuller example.

    """
    pdv = PandasConstraintVerifier(df, epsilon=epsilon,
                                   type_checking=type_checking)
    if isinstance(constraints_path, dict):
        constraints = DatasetConstraints()
        constraints.initialize_from_dict(native_definite(constraints_path))
    else:
        constraints = DatasetConstraints(loadpath=constraints_path)
    if repair:
        pdv.repair_field_types(constraints)
    return pdv.verify(constraints,
                      VerificationClass=PandasVerification,
                      report=report, **kwargs)


def detect_df(df, constraints_path, epsilon=None, type_checking=None,
              outpath=None, write_all=False, per_constraint=False,
              output_fields=None, index=False, in_place=False,
              rownumber_is_index=True, boolean_ints=False,
              repair=True, report='records',
              **kwargs):
    """
    Check the records from the Pandas DataFrame provided, to detect
    records that fail any of the constraints in the JSON ``.tdda`` file
    provided. This is anomaly detection.

    Mandatory Inputs:

        *df*:
                            A Pandas DataFrame, to be checked.

        *constraints_path*:
                            The path to a JSON ``.tdda`` file (possibly
                            generated by the discover_df function, below)
                            containing constraints to be checked.
                            Or, alternatively, an in-memory dictionary
                            containing the structured contents of a ``.tdda``
                            file.

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
                            ``strict`` or ``sloppy``.
                            Because Pandas silently, routinely and
                            automatically "promotes" integer and boolean
                            columns to reals and objects respectively
                            if they contain nulls, strict type checking
                            can be problematical in Pandas. For this reason,
                            ``type_checking`` defaults to ``sloppy``, meaning
                            that type changes that could plausibly be
                            attributed to Pandas type promotion will not
                            generate constraint values.

                            If this is set to strict, a Pandas ``float``
                            column ``c`` will only be allowed to satisfy a
                            an ``int`` type constraint if::

                                c.dropnulls().astype(int) == c.dropnulls()

                            Similarly, Object fields will satisfy a
                            ``bool`` constraint only if::

                                c.dropnulls().astype(bool) == c.dropnulls()

        *outpath*:
                            This specifies that the verification process
                            should detect records that violate any constraints,
                            and write them out to this CSV, parquet
                            or feather file.

                            By default, only failing records are written out
                            to file, but this can be overridden with the
                            ``write_all`` parameter.

                            By default, the columns in the detection output
                            file will be a boolean ``ok`` field for each
                            constraint on each field, an and ``n_failures``
                            field containing the total number of constraints
                            that failed for each row.  This behavious can be
                            overridden with the ``per_constraint``,
                            ``output_fields`` and ``index`` parameters.

        *write_all*:
                            Include passing records in the detection output
                            file when detecting.

        *per_constraint*:
                            Write one column per failing constraint, as well
                            as the ``n_failures`` total.

        *output_fields*:
                            Specify original columns to write out when detecting.

                            If passed in as an empty list (rather than None),
                            all original columns will be included.

        *index*:
                            Boolean to specify whether to include a row-number
                            index in the output file when detecting.

                            This is automatically enabled if no output field
                            names are specified.

                            Rows are numbered from 0.

        *in_place*:
                            Detect failing constraints by adding columns to
                            the input DataFrame.

                            If ``outpath`` is also specified, then
                            failing records will also be written to file.

        *rownumber_is_index*:
                            ``False`` if the DataFrame originated from a CSV
                            file (and therefore any detection output file
                            should refer to row numbers from the file, rather
                            than items from the DataFrame index).

        *boolean_ints*:
                            If ``True``, write out all boolean values to
                            CSV file as integers (1 for true, and 0 for
                            false), rather than as ``true`` and ``false``
                            values.

        *repair*:
                            A boolean to specify whether to try to use the
                            information in the constraints to attempt to
                            repair potentially-incorrect type inferrences
                            made when constructing the dataframe. When the
                            dataframe has been loaded from a .csv file, this
                            can often be useful (but should not be used with
                            dataframes that have come from a more reliable
                            source).

    The *report* parameter from :py:func:`verify_df` can also be
    used, in which case a verification report will also be produced in
    addition to the detection results.

    Returns:

        :py:class:`~tdda.constraints.pd.constraints.PandasDetection` object.

        This object has a :py:meth:`~PandasDetection.detected()` method
        for obtaining the Pandas DataFrame containing the detection
        results.

    Example usage::

        import pandas as pd
        from tdda.constraints import detect_df

        df = pd.DataFrame({'a': [0, 1, 2, 10, np.NaN],
                           'b': ['one', 'one', 'two', 'three', np.NaN]})
        v = detect_df(df, 'example_constraints.tdda')
        detection_df = v.detected()
        print(detection_df.to_string())

    """
    pdv = PandasConstraintVerifier(df, epsilon=epsilon,
                                   type_checking=type_checking)
    if isinstance(constraints_path, dict):
        constraints = DatasetConstraints()
        constraints.initialize_from_dict(native_definite(constraints_path))
    else:
        constraints = DatasetConstraints(loadpath=constraints_path)
    if repair:
        pdv.repair_field_types(constraints)
    return pdv.detect(constraints, VerificationClass=PandasDetection,
                      outpath=outpath, write_all=write_all,
                      per_constraint=per_constraint,
                      output_fields=output_fields, index=index,
                      in_place=in_place,
                      rownumber_is_index=rownumber_is_index,
                      boolean_ints=boolean_ints,
                      report=report, **kwargs)


def discover_df(df, inc_rex=False, df_path=None):
    """
    Automatically discover potentially useful constraints that characterize
    the Pandas DataFrame provided.

    Input:

        *df*:
            any Pandas DataFrame.

        *inc_rex*:
            If ``True``, include discovery of regular expressions
            for string fields, using rexpy (default: ``False``).

        *df_path*:
            The path from which the dataframe was loaded, if any.

    Possible return values:

    -  :py:class:`~tdda.constraints.base.DatasetConstraints` object
    -  ``None``    --- (if no constraints were found).

    This function goes through each column in the DataFrame and, where
    appropriate, generates constraints that describe (and are satisified
    by) this dataframe.

    Assuming it generates at least one constraint for at least one field
    it returns a :py:class:`tdda.constraints.base.DatasetConstraints` object.

    This includes a ``fields`` attribute, keyed on the column name.

    The returned :py:class:`~tdda.constraints.base.DatasetConstraints` object
    includes a :py:meth:`~tdda.constraints.base.DatasetContraints.to_json`
    method, which converts the constraints into JSON for saving as a tdda
    constraints file. By convention, such JSON files use a ``.tdda``
    extension.

    The JSON constraints file can be used to check whether other datasets
    also satisfy the constraints.

    The kinds of constraints (potentially) generated for each field (column)
    are:

        ``type``:
                the (coarse, TDDA) type of the field. One of
                ``bool``, ``int``, ``real``, ``string`` or ``date``.


        ``min``:
                for non-string fields, the minimum value in the column.
                Not generated for all-null columns.

        ``max``:
                for non-string fields, the maximum value in the column.
                Not generated for all-null columns.

        ``min_length``:
                For string fields, the length of the shortest string(s)
                in the field. N.B. In Python2, this assumes the strings
                are encoded in UTF-8, and an error may occur if this is
                not the case. String length counts unicode characters,
                not bytes.

        ``max_length``:
                For string fields, the length of the longest string(s)
                in the field.  N.B. In Python2, this assumes the strings
                are encoded in UTF-8, and an error may occur if this is
                not the case. String length counts unicode characters,
                not bytes.

        ``sign``:
                If all the values in a numeric field have consistent sign,
                a sign constraint will be written with a value chosen from:

                - ``positive``     --- For all values ``v`` in field: ``v > 0``
                - ``non-negative`` --- For all values ``v`` in field: ``v >= 0``
                - ``zero``         --- For all values ``v`` in field: ``v == 0``
                - ``non-positive`` --- For all values ``v`` in field: ``v <= 0``
                - ``negative``     --- For all values ``v`` in field: ``v < 0``
                - ``null``         --- For all values ``v`` in field: ``v is null``

        ``max_nulls``:
                The maximum number of nulls allowed in the field.

                - If the field has no nulls, a constraint
                  will be written with ``max_nulls`` set to zero.
                - If the field has a single null, a constraint will
                  be written with ``max_nulls`` set to one.
                - If the field has more than 1 null, no constraint
                  will be generated.

        ``no_duplicates``:
                For string fields (only, for now), if every
                non-null value in the field is different,
                this constraint will be generated (with value ``True``);
                otherwise no constraint will be generated. So this constraint
                indicates that all the **non-null** values in a string
                field are distinct (unique).

        ``allowed_values``:
                 For string fields only, if there are
                 :py:const:`MAX_CATEGORIES` or fewer distinct string
                 values in the dataframe, an AllowedValues constraint
                 listing them will be generated.
                 :py:const:`MAX_CATEGORIES` is currently "hard-wired" to 20.

        ``rex``:
                 For string fields only, a list of regular expressions
                 where each value in the dataframe is expected to match
                 at least one of the expressions.

    Example usage::

        import pandas as pd
        from tdda.constraints import discover_df

        df = pd.DataFrame({'a': [1, 2, 3], 'b': ['one', 'two', np.NaN]})
        constraints = discover_df(df)
        with open('example_constraints.tdda', 'w') as f:
            f.write(constraints.to_json())

    See *simple_generation.py* in the :ref:`constraint_examples`
    for a slightly fuller example.

    """
    disco = PandasConstraintDiscoverer(df, inc_rex=inc_rex)
    constraints = disco.discover()
    if constraints:
        constraints.set_dates_user_host_creator()
        constraints.set_source(df_path)
        constraints.set_stats(n_records=len(df), n_selected=len(df))
    return constraints


def file_format(path):
    if isinstance(path, StringIO):
        return 'csv'
    else:
        (stem, ext) = os.path.splitext(path)
        return ext[1:] if ext else 'csv'


def load_df(path, mdpath=None, ignore_apparent_metadata=False,
            infer_metadata=True):
    """
    Loads a pandas DataFrame from a path or stream.

    Args:
        path is usually a file path to be read, but can be a stream

        mdpath is an optional path to an associated metadata file to use

        ignore_apparent_metadata  Ordinarily, if a CSV file is provided
                                  as path, and there is "next to it"
                                  a file that looks likes a metadata file
                                  (same stem name with an extension fitting
                                  a recommended pattern for csvw, csvmetadata
                                  or frictionless), that metadata will be read
                                   and used.
                                  Setting this to True prevents that.

        infer_metadata  If a CSV file ('.csv', '.psv', '.tsv' or '.txt' file)
                        is given and no metadata file is provided, this
                        function will ordinarily try to infer the file
                        format using the csvmetadata library.
                        Setting this to False overrides that behaviour,
                        forcing the default Pandas CSV reader to be used
                        with few TDDA's default arguments for it.
    """
    if isinstance(path, StringIO):  # stream
        return default_csv_loader(path)
    exists = os.path.exists(os.path.expanduser(path))
    stem, ext = os.path.splitext(path)
    lcstem, ext = stem.lower(), ext.lower()

    if ext == '.parquet':
        return pd.read_parquet(path)
    elif ext == '.feather':
        return read_feather_file(path)

    if mdpath is None:
        md_type, _ = find_metadata_type_from_path(path)
        if md_type:
            # path is a metadata file of a known type
            # load the metadata from it and get the file path, if any
            # from the metadata file
            metadata = load_metadata(path)
            if metadata and metadata.path:
                print('** Using metadata %s.  '
                      'Use --no-csv-metadata to override.' % path,
                      file=sys.stderr)
                kw = to_pandas_read_csv_args(metadata)
                return default_csv_loader(metadata.path, **kw)

        if not ignore_apparent_metadata:
            # no explicit metadata path provided
            mdpath = find_associated_metadata_file(path)
            if mdpath:
                metadata = load_metadata(path)
                kw = to_pandas_read_csv_args(metadata)
                return default_csv_loader(path, **kw)
            elif infer_metadata:
                # infer metadata
                pass
        # Told not to look for apparent metadata or infer metadata
        return default_csv_loader(path)

    else:  # explicit metadatapath provided
        metadata = load_metadata(path)
        kw = to_pandas_read_csv_args(metadata)
        return default_csv_loader(path, **kw)


def save_df(df, path, index=False):
    if path == '-' or path is None:
        print(default_csv_writer(df, None, index=index))
    else:
        fmt = file_format(path)
    if fmt == 'parquet':
        df.to_parquet(path=path, index=False)
    elif fmt in ('csv', 'psv', 'tsv', 'txt'):
        default_csv_writer(df, path, index=index)
    elif fmt == 'feather':
        write_feather_file(df, path, name='verification')
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
        null = np.nan if default is None else default # np.nan  # pd.NA
        return np.where(pd.isnull(column), null, expr.astype('O'))




def convert_output_types(df, boolean_ints):
    """
    Construct a new DataFrame with boolean values mapped to appropriate
    string equivalents (usually "true" and "false", but optionally "1" and
    "0")
    """
    newdf = pd.DataFrame(index=df.index)
    trueval = '1' if boolean_ints else 'true'
    falseval = '0' if boolean_ints else 'false'
    pandas_true_values = (True, np.bool_(True))
    pandas_false_values = (True, np.bool_(False))
    for col in list(df):
        c = df[col]
        if c.dtype in (np.dtype('O'), np.dtype(bool)):
            newdf[col] = [(trueval if v in pandas_true_values
                           else falseval if v in pandas_false_values
                           else v) for v in c]
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
    if v[:L + 1] != f + '_':
        return False  # didn't start with f

    v = v[L + 1:]
    has_digits = False
    while v and v[-1].isdigit():  # remove any trailing (disambiguation) digits
        v = v[:-1]
        has_digits = True
    if has_digits:
        if not v.endswith('_'):  # was only disamb. if ended _ddd
            return False
        v = v[:-1]    # remove the underscore

    if not v.endswith('_ok'):
        return False

    v = v[:-3]
    return v in STANDARD_CONSTRAINT_SUFFIXES


def verification_field(col, ctype):
    return '%s_%s_ok' % (col, CONSTRAINT_SUFFIX_MAP[ctype])


# for backwards compatibility (old name for function)
discover_constraints = discover_df

