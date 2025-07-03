import csv
import datetime
import locale
import os
import shutil

from collections import namedtuple

from tdda.serial import SerialMetadata, FieldMetadata
from tdda.utils import swap_ext

FieldInfo = namedtuple('FieldInfo', 'csvname type')

OUTDIR = 'torture'

DELIMITERS = {
     ',': 'csv',
     '\t': 'tsv',
}

QUOTECHARS = {
    '"': 'dquote',
    "'": 'squote',
}

STUTTER = {
    True:  'stutter',  # stutter
    False: 'escape',  # escape
}

ESCAPECHARS = {
     '\\': 'backslash',
     '`': 'backtick'
}

QUOTING = {
    csv.QUOTE_MINIMAL:    'q_minimal',     # 0
    csv.QUOTE_ALL:        'q_all',         # 1
    csv.QUOTE_NONNUMERIC: 'q_nonnumeric',  # 2
    csv.QUOTE_NONE:       'q_none',        # 3
    csv.QUOTE_STRINGS:    'q_string',      # 4
    csv.QUOTE_NOTNULL:    'q_notnull',     # 5
}

ENCODINGS = {
    'UTF-8': 'UTF-8',
    'latin-1': 'latin-1',
}

DATEFORMATS = {
    '%Y-%m-%d': 'iso',
    '%d-%m-%Y': 'euro',
}

NULLS = {
    '': 'blank',
    'NULL': 'NULL',
    '¤': 'currency',
}

DIFF_CSV_NAMES = {
    False: '1name',
    True: '2names',
}


HEADER = {
    True: 'header',
    False: 'nohead',
}

DP = {
    '.': 'dpdot',
    ',': 'comma',
}

DPS = {
    2: '2dp',
    None: 'alldp'
}

FIELD_INFO = {
    'i': FieldInfo('', 'int'),
    'b': FieldInfo('OK?', 'bool'),
    'f': FieldInfo('Irrationals', 'float'),
    'snull': FieldInfo('Null-like Strings', 'string'),
    'sesc': FieldInfo('Escape-like Strings', 'string'),
    'sdt': FieldInfo('Date-like Strings', 'string'),
    'sf': FieldInfo('Float-like Strings', 'string'),
    'sq': FieldInfo('Quote-like Strings', 'string'),
    'ssep': FieldInfo('String-Separator-like strings', 'string'),
    'd': FieldInfo('Date', 'date'),
}


DATA = {
    'i': [1, 2, None, 4],
    'b': [True, False, None, None],
    'f': [1/3, 1/7, 1/11, None],
    'snull': ['s1', '', 'NULL', '¤'],
    'sesc': ['s2', '\\', '`', None],
    'sdt': ['s3', '2000-01-01', '2001/12/31', None],
    'sf': ['s4', '1.125', '1,000', None],
    'sq': ['s5', '"', "'", None],
    'ssep': ['s6', '|', ',', '\t'],
    'd':  [datetime.date(2000, 1, 1), datetime.date(2001, 12, 31), None, None],
}


def generate_one(parts, csv_kw, *, ext=None, diff_csv_names=None, header=None,
                 date_format=None, dp=None, dps=None, null=None,
                 encoding=None):
    """
    Generate on CSV file.

    Args:

        parts: the components to use for the suffix of the output file name

        csv_kw: dictionary of keyword arguments to be passed to csv.writer

        ext: the extension to use for the filename

        diff_csv_names: If true, the names in the CSV file will be mapped
                        using FIELD_INFO

        header: If False, no header will be written

        date_format: The format to use when writing dates.
                     If this is an ISO8601 format, this will be left to
                     csv.writer. Otherwise, date will be tranformed
                     to a string (with implications for quoting).

        dps: the number of decimal places for floating point values.
             If None, not set

        null: The null marker to be used
    """
#    if not header and diff_csv_names:
#        return  # no point: names aren't used. But serial data is different
    data = DATA.copy()
    n_rows = len(data['i'])
    fieldnames = list(data)
    suffix = '-'.join([
         parts['quotechar'],
         parts['doublequote'],
         parts['escapechar'],
         parts['quoting'],
         parts['diff_csv_names'],
         parts['header'],
         parts['date_format'],
         parts['dp'],
         parts['dps'],
         parts['null'],
         parts['encoding']
    ])
    outpath = os.path.join(OUTDIR, f'flat-{suffix}.{ext}')

    if date_format != '%Y-%m-%d':
        data['d'] = [
            None if v is None else v.strftime(date_format) for v in data['d']
        ]
    if dps:
        data['f'] = [None if v is None else round(v, dps) for v in data['f']]

    if null != '':
        data = {
            k: [999 if v is null else v for v in values]
            for k, values in data.items()
        }

    with open(outpath, 'w', encoding=encoding) as f:
        flat = csv.writer(f, **csv_kw)
        if header:
            if diff_csv_names:
                flat.writerow([FIELD_INFO[k].csvname for k in fieldnames])
            else:
                flat.writerow(fieldnames)
        for i in range(n_rows):
            flat.writerow([data[field][i] for field in fieldnames])

    fix(outpath, null, csv_kw['quoting'], csv_kw['quotechar'],
        dp, dps, ext, encoding)
    print(f'Written {outpath}.')

    fields = [
        FieldMetadata(
            name=name,
            csvname=fieldinfo.csvname if diff_csv_names else None,
            fieldtype=fieldinfo.type
        )
        for name, fieldinfo in FIELD_INFO.items()
    ]
    md = SerialMetadata(
            fields=fields,
            path=os.path.basename(outpath),
            encoding=encoding,
            delimiter=csv_kw['delimiter'],
            quote_char=csv_kw['quotechar'],
            date_format=date_format,
            escape_char=csv_kw['escapechar'],
            stutter_quotes=csv_kw['doublequote'],
            header_row_count=1 if header else 0,
            header_row = 0 if header else None,
            quoting=csv_kw['quoting'],
            decimal_point=dp,
            null_indicator=null,
            dps=dps,
    )
    md.write(outpath, use_serial_ext=True, verbose=True)


def fix(path, null, quoting, quote, dp, dps, ext, encoding):
    if null == '' and dp == '.':
        return  # csv should have done what we need

    with open(path, encoding=encoding) as f:
        lines = f.readlines()
    if null != '':
        if quoting == csv.QUOTE_ALL:
            in_null = f'{quote}999{quote}'
            out_null = f'{quote}{null}{quote}'
        elif quoting == csv.QUOTE_MINIMAL:
            in_null = f'999'
            out_null = null
        elif quoting == csv.QUOTE_NONNUMERIC:
            in_null = '999'
            out_null = f'{quote}{null}{quote}'
        elif quoting == csv.QUOTE_NONE:
            in_null = '999'
            out_null = f'{null}'
        elif quoting == csv.QUOTE_NOTNULL:
            in_null = f'{quote}999{quote}'
            out_null = f'{null}'
        elif quoting == csv.QUOTE_STRINGS:
            in_null = f'{quote}999{quote}'
            out_null = f'{null}'
        else:
            raise Exception('Should not be able to get here.')
        lines = [L.replace(in_null, out_null) for L in lines]

    if dp == ',':
        in_dec = '0.'
        out_dec = '0,'
        if ext == 'csv':
            if quoting == csv.QUOTE_NONE:
                out_dec = r'0\,'
            elif quoting in (csv.QUOTE_MINIMAL, csv.QUOTE_NONNUMERIC):
                if dps == 2:
                    vals = ('0.33', '0.14', '0.09')
                else:
                    vals = ('0.3333333333333333', '0.14285714285714285',
                            '0.09090909090909091')
                for v in vals:
                    lines = [
                        L.replace(v, f'{quote}{v}{quote}') for L in lines
                    ]
        lines = [L.replace(in_dec, out_dec) for L in lines]
    with open(path, 'w', encoding=encoding) as f:
        for line in lines:
            f.write(line)



def generate_variants(csv_kw, parts, ext):
    kw = {'ext': ext}
    for diff_csv_names, diff_names in DIFF_CSV_NAMES.items():
        kw['diff_csv_names'] = diff_csv_names
        parts['diff_csv_names'] = diff_names
        for header, hname in HEADER.items():
            kw['header'] = header
            parts['header'] = hname
            for date_format, dfname in DATEFORMATS.items():
                kw['date_format'] = date_format
                parts['date_format'] = dfname
                for dp, dpname in DP.items():
                    kw['dp'] = dp
                    parts['dp'] = dpname
                    for dps, dpsname in DPS.items():
                        kw['dps'] = dps
                        parts['dps'] = dpsname
                        for null, nullname in NULLS.items():
                            kw['null'] = null
                            parts['null'] = nullname
                            for encoding, encname in ENCODINGS.items():
                                kw['encoding'] = encoding
                                parts['encoding'] = encname
                                generate_one(parts, csv_kw, **kw)

def generate():
    shutil.rmtree('torture')
    os.mkdir('torture')

    kw = {}
    parts = {}
    for delimiter, ext in DELIMITERS.items():
        kw['delimiter'] = delimiter
        for quotechar, qcname in QUOTECHARS.items():
            kw['quotechar'] = quotechar
            parts['quotechar'] = qcname
            for stutter, stname in STUTTER.items():
                kw['doublequote'] = stutter
                parts['doublequote'] = stname
                for escapechar, escname in ESCAPECHARS.items():
                    kw['escapechar'] = escapechar
                    parts['escapechar'] = escname
                    for quoting, qname in QUOTING.items():
                        kw['quoting'] = quoting
                        parts['quoting'] = qname
                        generate_variants(kw, parts, ext)


if __name__ == '__main__':
    generate()
