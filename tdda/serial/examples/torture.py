import csv
import datetime
import os

OUTDIR = 'torture'

DELIMITERS = {
    '|': 'psv',
     ',': 'csv',
     '\t': 'tsv',
}

QUOTECHARS = {
    '"': 'dq',
    "'": 'sq',
}

STUTTER = {
    True:  'st',  # stutter
    False: 'esc',  # escape
}

DATEFORMATS = {
    '%Y-%m-%d': 'iso',
    '%d-%m-%Y': 'euro',
    '%m-%d-%Y': 'us',
}

NULLS = {
    '': 'blank',
    'NULL': 'NULL',
    '∅': 'eset',
}

ESCAPECHARS = {
     '\\': 'bs',
     '`': 'bt'
}

HEADER = {
    True: 'hd',
    False: 'nohd'
}

DP = {
    '.': 'dot',
    ',': 'comma'
}

DPS = {
    2: '2',
    8: '8'
}

CSV_NAMES = {
    'i': '',
    'b': 'OK?',
    'f': 'Irrationals',
    'snull': 'Null-like Strings',
    'sesc': 'Escape-like Strings',
    'sdt': 'Date-like Strings',
    'sf': 'Float-like Strings',
    'sq': 'Quote-like Strings',
    'd': 'Date'
}

QUOTING = {
    'QUOTE_MINIMAL': 'q_min',        # 0
    'QUOTE_ALL': 'q_all',            # 1
    'QUOTE_NONNUMERIC': 'q_nonnum',  # 2
    'QUOTE_NONE': 'q_none',          # 3
    'QUOTE_STRINGS': 'q_str',        # 4
    'QUOTE_NOTNULL': 'q_notnull',    # 5
}

ENCODINGS = {
    'UTF-8': 'UTF-8',
    'latin-1': 'latin-1',
    'UTF-16': 'UTF-16'
}


DATA = {
    'i': [1, 2, None, 4],
    'b': [True, False, None, None],
    'f': [1/3, 1/7, 1/11, None],
    'snull': ['s1', '', 'NULL', '∅'],
    'sesc': ['s2', '\\', '`', None],
    'sdt': ['s3', '2000-01-01', '2999/12/31', None],
    'sf': ['s4', '1.125', '1,000', None],
    'sq': ['s5', '"', "'", None],
    'ssep': ['s6', '|', ',', '\t'],
    'd':  [datetime.date(2000, 1, 1), datetime.date(2999, 12, 31), None, None],
}


def generate_one(outpath, **kw):
    n_rows = len(DATA['i'])
    fieldnames = list(DATA)
    with open(outpath, 'w') as f:
        flat = csv.writer(f, **kw)
        flat.writerow(fieldnames)
        for i in range(n_rows):
            flat.writerow([DATA[field][i] for field in fieldnames])
    print(f'Written {outpath}.')


def generate():
    if not os.path.exists('torture'):
        os.mkdir('torture')

    kw = {}
    parts = []
    for delimiter, ext in DELIMITERS.items():
        kw['delimiter'] = delimiter
        for quotechar, qname in QUOTECHARS.items():
            kw['quotechar'] = quotechar
            parts.append(qname)
            for stutter, stname in STUTTER.items()
                kw[doublequote] = stutter
                parts.append(stname)
                for dateformat, dname in DATEFORMATS.items()
                    kw[quotechar] = quotechar
                    parts.append(stname)
                    for escapechar, escname in escape.items():
                        kw['escapechar'] = escapechar
                        parts.append()
                        for header, hname in HEADER.items()
                            for encoding, ename in ENCODINGS.items()
                                for csvnames
                                    for quoting
                                        for dp, dpname in DP.items():
                                            for dps, dpsname in DPS.items():
                                                path = outname(parts)
                                                generate_one(path, **kw)
                             quoting=csv.QUOTE_ALL)

if __name__ == '__main__':
    generate()
