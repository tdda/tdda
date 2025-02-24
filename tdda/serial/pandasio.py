import datetime
import re
import sys

import pandas as pd

from tdda.serial.csvw import CSVWMetadata
from tdda.serial.base import Metadata, FieldMetadata, FieldType


DATETIME_RE = re.compile(r'^datetime[0-9]+\[[a-z]+(,?)(.*)\]$')


MTYPE_TO_PANDAS_DTYPE = {
    'bool': 'boolean',
    'int': 'Int64',
    'string': 'string',
    'number': 'float',
    'float': 'float',
    'datetime': 'datetime',
    'date': 'date',
}


def gen_pandas_kwargs(spec, extensions=False):
    """
    Construct a suitable set of kwargs to pass to pandas.read_csv
    to get it to read a CSV file in conformance to the csvw
    specification in spec.

    Args:
        spec should either be a path to a CSVW file (usually .json or .csvw)
             or a dictionary of the form returned by performing
             a json.load such a (valid) CSVW).

    Returns:
        kwargs dictionary for pandas csv_read function, implementing
        the spec given as closely as possible.
    """
    md = CSVWMetadata(spec, extensions=extensions)
    kw = to_pandas_read_csv_args(md)
    return kw


def to_pandas_read_csv_args(md):
    kw = {}
    date_fields = {
        f.name: f for f in md.fields
                if f.mtype and f.mtype.startswith('date')
    }
    kw['dtype'] = {
        f.name: MTYPE_TO_PANDAS_DTYPE.get(f.mtype)
        for f in md.fields
        if f.name not in date_fields
        and MTYPE_TO_PANDAS_DTYPE.get(f.mtype) is not None
    } or None
    if any(v.format for v in date_fields):
        kw['date_format'] = {name: f.format for name, f in date_fields.items()}
    if date_fields:
        kw['parse_dates'] = list(date_fields)

    if any(v.altnames for v in md.fields):
        kw['names'] = [v.name for v in md.fields]
        kw['header'] = 0

    if md.delimiter:
        kw['sep'] = md.delimiter
    if md.encoding:
        kw['encoding'] = md.encoding

    if md.header_rows == 0:
        kw['header'] = None

    booleans = [
        f.format
        for f in md.fields
        if getattr(f, 'format', None) and f.mtype == 'bool'
    ]
    if booleans:
        trues, falses = set(), set()
        for b in booleans:
            parts = b.split('|')
            if len(parts) == 2:
                trues.add(parts[0])
                falses.add(parts[1])
            else:
                print(f'*** Warning: Boolean specification {b} not understood;'
                       ' ignoring')
            if trues.intersection(falses):
                print(f'*** Conflicting values for booleans.')
            else:
                kw['true_values'] = list(trues)
                kw['false_values'] = list(falses)
    return kw


def dtype_to_fieldtype(dtype, col=None, prefer_nullable=True):
    """
    Converts a pandas dtype to a serial.base.FieldType

    Args:

        dtype   is the pandas datatype to be converted.
                It can be provided as the actual dtype (df[col].dtype)
                or as the string version of that (str(df[col].dtype)).

        col     (Optional) the column of values (a pd.Series, typically)

        prefer_nullable:  If True, will demote floats to ints where possible

    Returns:

        The mtype (a value from FieldType) if recognized,
        or None if no recognized dtype is found.
    """

    dt = str(dtype) if type(dtype) is not str else dtype
    dtl = dt.lower()
    if dtl.startswith('int') or dtl.startswith('uint'):
        return FieldType.INT
    elif dtl.startswith('float'):
        if prefer_nullable and (col is not None):
            nonnull = col.dropna()
            if nonnull.size > 0:
                if (nonnull.astype(int) == nonnull).sum() == len(nonnull):
                    return FieldType.INT
        return FieldType.FLOAT
    elif dt.startswith('string'):
        return FieldType.STRING
    elif dt.startswith('datetime'):
        m = re.match(DATETIME_RE, dt)
        if m:
            if m.group(1):
                return FieldType.DATETIME_WITH_TIMEZONE
            else:
                return FieldType.DATETIME
    elif dtl.startswith('bool'):
        return FieldType.BOOL
    elif dtl == 'object':
        if col is None:
            return FieldType.STRING  # Most likely
        else:
            nonnulls = col.dropna()
            if nonnulls.size == 0:
                return FieldType.STRING  # Most likely
            r = nonnulls.min()
            m = item(r)
            t = type(m)
            if t is str:
                return FieldType.STRING
            elif pd.isnull(m):
                return FieldType.STRING
            elif t is bool:
                return FieldType.BOOL
            elif t is int:
                return FieldType.INT
            elif t is float:
                return FieldType.FLOAT
            elif t is datetime.date:
                return FieldType.DATE
            elif t is datetime.datetime:
                return FieldType.DATETIME
            elif str(t).endwith('Timestamp'):
                return FieldType.DATETIME_TZ
    else:
        return None


def df_to_metadata(df, path=None):
    fields = [
        col_to_field_metadata(df[c])
        for c in df
    ]



def col_to_field_metadata(field, mtype=None,
                                 fmt=None, validate=True):
    """
    Produces a FieldMetadata object for the pandas series provided
    in field.

    Args:

        field: a pandas series

        mtype: Optional mtype to use. Must be compatible
               with the data in the field if validate is True

        fmt: Optional format informaiton for the field

        validate: If true, will fail if mtype is not compatible
                  with the data in the field.

    Returns:

        FieldMetadata object for the field

    """
    name = field.name



def item(v):
    return v.item() if hasattr(v, 'item') else v
