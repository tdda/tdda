import re
import os

from tdda.serial.metadata import SerialMetadata, FieldMetadata, FieldType
from tdda.utils import warn, error, nvl
from tdda.referencetest.utils import FileType
from tdda.serial.utils import non_chars


NULLS = ['', 'NULL', 'na', 'n/a', '.', '-']

DATEISH = re.compile('^[0-9]{2,4}[-./][0-9]{2}[-./][0-9]{2,4}$')
ADATEISH = re.compile(
    '^([0-9]{2,4}|[a-z]{3}).([0-9]{2,4}|[a-z]{3}).[0-9]{2,4}$'
)

DTISH = re.compile(
  '^[0-9]{2,4}[-./][0-9]{2,4}[-./][0-9]{2,4}.[0-9]{2}:[0-9]{2}:[0-9]{2}.*$'
)
ADTISH = re.compile(
    '^([0-9]{2,4}|[a-z]{3}).([0-9]{2,4}|[a-z]{3}).[0-9]{2,4}'
    '[0-9]{2}:[0-9]{2}:[0-9]{2}.*$'
)


class MetadataInferrer:
    def __init__(self, inpath, lines_to_use= 1000):
        self.inpath = os.path.expanduser(inpath)
        self.lines_to_use = lines_to_use
        self.read()
        self.process_header()

        self.metadata = SerialMetadata(
            fields=self.fields, encoding=self.encoding, delimiter=self.sep,
            stutter_quotes=self.stutter, escape_char=self.escape,
            quote_char=self.quote_char, null_indicator=self.null
        )


    def read(self):
        enc = nvl(FileType(self.inpath).encoding, 'UTF-8')
        self.encoding = 'UTF-8' if enc == 'ascii' else enc
        self.data = data = []
        with open(self.inpath, encoding=self.encoding) as f:
            self.header = f.readline()
            while not self.header.strip():
                self.header = f.readline()
            for i in range(self.lines_to_use):
                line = f.readline().strip()
                if line:
                    data.append(line)

    def process_header(self):
        header = self.header
        lines = [header] + self.data
        n_commas = count(',', lines)
        n_pipes = count('|', lines)
        n_tabs = count('\t', lines)
        n_semis = count(';', lines)
        n_dquotes = count('"', lines)
        n_squotes = count("'", lines)

        M = max((n_commas, n_pipes, n_tabs, n_semis))
        if M == 0:
            error('Separator does not appear to be comma, pipe, tab'
                  ' or semicolon. Abandoning.')

        self.sep = sep = (
            ',' if n_commas == M else
            '|' if n_pipes == M else
            '\t' if n_tabs == M else
            ';'
        )

        m = max((n_dquotes, n_squotes))

        sep_replacement, qq_replacement = non_chars(lines, 2)
        restorations = self.restorations = {}

        for i, line in enumerate(lines):
            escaped_sep = f'\\{sep}'
            if escaped_sep in line:
                lines[i] = line.replace(escaped_sep, sep_replacement)
                restorations[sep_replacement] = sep

        escape = stutter = quote_char = None
        self.quote_char = quote = '"'
        if m > 0:
            stuttered = quote * 2
            escaped = f'\\{quote}'
            quote = '"' if n_dquotes > n_squotes else "'"
            for i, line in enumerate(lines):
                # Crudely handle escaping and stuttering (all lines)
                if stuttered in line:
                    lines[i] = line.replace(stuttered, qq_replacement)
                    stutter = True
                if escaped in header:
                    lines[i] = line.replace(escaped, sep_replacement)
                    escape = '\\'
            self.header = header = lines[0]
            fieldnames = header.split(sep)
            plain_fieldnames = self.dequote(fieldnames)
            if plain_fieldnames != fieldnames:
                quote_char = quote
            else:
                plain_fieldnames = fieldnames
        else:
            plain_fieldnames = header.split(sep)
        if quote:
            restorations[qq_replacement] = quote

        self.fieldnames = plain_fieldnames
        self.data = lines[1:]

        self.escape = escape
        self.stutter = stutter
        self.quote_char = quote_char
        self.infer_fields()

    def infer_fields(self):
        sep = self.sep
        data = [
            self.dequote(row.split(self.sep))
            for row in self.data
        ]
        n_cols = max(len(row) for row in data)
        n_fields = len(self.fieldnames)
        if n_fields < n_cols:
            error(f'Found more data columns ({n_cols}) than fieldnames '
                  f'({n_fields}). Giving up.')

        n_nulls = {
            nil: count(nil, data)
            for nil in NULLS
        }
        m = max(n_nulls.values())
        if m > 0:
            cands = [k for k, v in n_nulls.items() if v == m]
            nil = cands[0]
            if len(cands) > 1:
                nils = '\n    '.join(nil for nil in cands)
                warn(f'Multiple possible null values found:\n{nils}\n'
                     f'Assuming {nil}')
        else:
            nil = None
        typemap = {}
        for c in range(n_cols):
            col_vals = [row[c] for row in data if len(row) > c]
            col_vals = [v for v in col_vals if v != nil]
            typemap[self.fieldnames[c]] = guess_type(col_vals)
        self.fields = [
            FieldMetadata(name=name, fieldtype=typemap.get(name))
            for name in self.fieldnames
        ]
        self.null = nil

    def dequote(self, names):
        # Strip pairs of opening and closing quote for each element in names.
        # Also restores replaced characters based on map
        q = self.quote_char or '"'
        out = [
            s[1:-1] if s.startswith(q) and s.endswith(q) else s
            for s in names
        ]
        for k, v in self.restorations.items():
            out = [s.replace(k, v) for s in out]
        return out


def infer_format_from_flat_file(path, lines_to_use=1000):
    inferrer = MetadataInferrer(path, lines_to_use)
    return inferrer.metadata


def count(char, lines):
    return sum(sum(c == char for c in line) for line in lines)


def guess_type(values):
    if all(v.lower() in ('true', 'false') for v in values):
        return FieldType.BOOL
    for v in values:
        try:
            if '.' in v:
                break
            int(v)
        except ValueError:
            break
    else:
        return FieldType.INT

    for v in values:
        try:
            float(v)
        except ValueError:
            break
    else:
        return FieldType.FLOAT

    if all(re.match(DATEISH, v) for v in values):
        return FieldType.DATE
    if all(re.match(ADATEISH, v) for v in values):
        return FieldType.DATE
    if all(re.match(DTISH, v) for v in values):
        return FieldType.DATETIME
    if all(re.match(ADTISH, v) for v in values):
        return FieldType.DATETIME

    return FieldType.STRING
