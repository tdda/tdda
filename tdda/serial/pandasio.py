import sys
from tdda.serial.csvw import CSVWMetadata


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
