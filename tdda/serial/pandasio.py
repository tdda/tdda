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
        f.name: f for f in md.fields if f.mtype.startswith('date')
    }
    kw['dtype'] = {
        f.name: MTYPE_TO_PANDAS_DTYPE.get(f.mtype)
        for f in md.fields
        if f.name not in date_fields
    }
    if any(v.format for v in date_fields):
        kw['date_format'] = {name: f.format for name, f in date_fields.items()}
    if date_fields:
        kw['parse_dates'] = list(date_fields)


    if md.delimiter:
        kw['sep'] = md.delimiter
    if md.encoding:
        kw['encoding'] = md.encoding
    return kw
