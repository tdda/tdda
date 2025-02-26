import datetime
import re
import sys

import pandas as pd

from tdda.serial.csvw import CSVWMetadata
from tdda.serial.base import (
    SerialMetadata, FieldMetadata, FieldType, DateFormat, Defaults
)


DATETIME_RE = re.compile(r'^datetime[0-9]+\[[a-z]+(,?)(.*)\]$')


FIELDTYPE_TO_PANDAS_DTYPE = {
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
                if f.fieldtype and f.fieldtype.startswith('date')
    }
    kw['dtype'] = {
        f.name: FIELDTYPE_TO_PANDAS_DTYPE.get(f.fieldtype)
        for f in md.fields
        if f.name not in date_fields
        and FIELDTYPE_TO_PANDAS_DTYPE.get(f.fieldtype) is not None
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
        if getattr(f, 'format', None) and f.fieldtype == 'bool'
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

        The fieldtype (a value from FieldType) if recognized,
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
    return SerialMetadata(
               fields, path=path,
               encoding=Defaults.ENCODING,
               delimiter=Defaults.DELIMITER,
               quote_char=Defaults.QUOTE_CHAR,
               escape_char=Defaults.ESCAPE_CHAR,
               null_indicators=Defaults.NULL_INDICATORS,
               header_rows=Defaults.HEADER_ROW_COUNT
           )


def col_to_field_metadata(field, fieldtype=None,
                          fmt=None, prefer_nullable=True):
    """
    Produces a FieldMetadata object for the pandas series provided
    in field.

    Args:

        field: a pandas series

        fieldtype:         Optional fieldtype to use. Must be compatible
                           with the data in the field if validate is True

        fmt:               Optional format informaiton for the field

        prefer_nullable:   promote int-ish floats to ints

    Returns:

        FieldMetadata object for the field

    """
    if fieldtype:
        fieldtype = fieldtype
    else:
        fieldtype = dtype_to_fieldtype(field.dtype, col=field,
                                       prefer_nullable=prefer_nullable)

    if not fmt:
        if fieldtype == FieldType.DATE:
            fmt = DateFormat.ISO8601_DATE
        elif fieldtype == FieldType.DATETIME:
            fmt = DateFormat.ISO8601_DATETIME
        elif fieldtype == FieldType.DATETIME_WITH_TIMEZONE:
            fmt = DateFormat.ISO8601_DATETIME_TZ
    return FieldMetadata(field.name, fieldtype, format=fmt)


def item(v):
    return v.item() if hasattr(v, 'item') else v
