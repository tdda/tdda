import re
import os
import sys

from collections import namedtuple, Counter

TypeStats = namedtuple('TypeStats', 'field stats')

from tdda.serial.metadata import SerialMetadata, FieldMetadata, FieldType
from tdda.utils import warn, error, nvl, debug
from tdda.referencetest.utils import FileType
from tdda.serial.utils import non_chars, dict_max_items


KNOWN_NULLS = [
    '', 'NULL', 'NA', '<NA>', 'N/A', 'None',
    'nan', 'null', 'null ', 'Null', 'na', 'Na', '-', '-', 'x', 'X'
    'NaN', 'n/a', '#NA', '#N/A', '-NaN', '-nan',
    '#N/A N/A',  '-1.#IND', '-1.#QNAN', '1.#IND', '1.#QNAN', ' ',
]

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
    def __init__(self, inpath, lines_to_use=1000, verbosity=None):
        self.inpath = os.path.expanduser(inpath)
        self.lines_to_use = lines_to_use
        self.verbosity = nvl(verbosity, 10)
        self.read()
        self.process()

        self.metadata = SerialMetadata(
            fields=self.fields, encoding=self.encoding, delimiter=self.sep,
            stutter_quotes=self.stutter, escape_char=self.escape,
            quote_char=self.quote_char, null_indicator=self.null
        )

    def print(self, msg, min_verbosity=1):
        if self.verbosity >= min_verbosity:
            print(msg)

    def read(self):
        enc = nvl(FileType(self.inpath).encoding, 'UTF-8')
        self.encoding = 'UTF-8' if enc == 'ascii' else enc
        self.datalines = datalines = []
        with open(self.inpath, encoding=self.encoding) as f:
            self.header = f.readline().rstrip()
            while not self.header.strip():
                self.header = f.readline()
            for i in range(self.lines_to_use):
                line = f.readline().strip()
                if line:
                    datalines.append(line)

    def process(self):
        header = self.header
        self.all_lines = lines = [self.header] + self.datalines

        self.sep = sep = self.find_separator()
        self.quote_char = quote = self.find_quote_char()

        sep_replacement, qq_replacement = non_chars(lines, 2)
        restorations = self.restorations = {}

        escaped_sep = f'\\{sep}'
        for i, line in enumerate(lines):
            if escaped_sep in line:
                lines[i] = line.replace(escaped_sep, sep_replacement)
                restorations[sep_replacement] = sep

        fieldnames = self.find_fieldnames()
        self.n_fieldnames = len(fieldnames)

        escape = stutter = quoting = None
        plain_fieldnames, _ = self.dequote(fieldnames)
        if plain_fieldnames != fieldnames:
            self.quote_char = quote
            plain_fieldnames = header.split(sep)
        if quote:
            restorations[qq_replacement] = quote

        self.fieldnames = plain_fieldnames
        self.data = lines[1:]

        self.escape = escape
        self.stutter = stutter

        self.print(f'Inferred escape: {escape}.', 2)
        self.print(f'Inferred stutter: {stutter}.', 2)
        self.infer_fields()

    def find_separator(self):
        lines = self.all_lines
        n_commas = count(',', lines)
        n_pipes = count('|', lines)
        n_tabs = count('\t', lines)
        n_semis = count(';', lines)

        M = max((n_commas, n_pipes, n_tabs, n_semis))
        if M == 0:
            error('Separator does not appear to be comma, pipe, tab'
                  ' or semicolon. Abandoning.')

        sep = (
            ',' if n_commas == M else
            '|' if n_pipes == M else
            '\t' if n_tabs == M else
            ';'
        )
        self.print(f'Inferred separator: {sep} ({M} occurrences).', 2)
        return sep

    def find_quote_char(self):
        lines = self.all_lines
        n_dquotes = count('"', lines)
        n_squotes = count("'", lines)
        quote = "'" if n_squotes > n_dquotes else '"'
        self.n_quotes = n_squotes if n_squotes > n_dquotes else n_dquotes
        # But apostrophes...quoted or not.
        return quote

    def find_fieldnames(self):
        fieldnames = self.header.split(self.sep)
        quote = self.quote_char
        if quote and any(f.startswith(quote) and not f.endswith(quote)
                         for f in fieldnames):
            return careful_split(self.header, sep, quote, '\\')
        else:
            return fieldnames

    def infer_fields(self):
        sep = self.sep
        combined = [
            self.dequote_and_split(row)
            for row in self.data
        ]
        is_quoted = [r[2] for r in combined]
        data = [r[1] for r in combined]
        raw = [r[0] for r in combined]
        m = min(len(row) for row in data)
        M = max(len(row) for row in data)
        nFields = len(self.fieldnames)
        excel = not (m == M)
        if excel:
            self.print('Rows have different numbers of values.', 2)
        else:
            self.print('All rows complete', 2)

        self.print(f'Fieldnames {nFields}. '
                   f'Min fields in row: {m}. Max fields in row: {M}\n', 2)
        if M > nFields:
            self.print('More cols in some rows than fields (headers)', 2)
        if nFields > M:
            self.print('All rows lack at least one field.', 2)
        n = max(nFields, M)

        # Number quoted by column index
        n_quoted = {
            i: sum((q[i] if i < len(q) else 0) for q in is_quoted)
            for i in range(n)
        }
        self.print(f'Number quoted by col index: {n_quoted}', 2)
        total_quoted = sum(n_quoted.values())
        self.print(f'Total number quoted: {total_quoted}', 2)

        n_cols = max(len(row) for row in data)
        n_fields = len(self.fieldnames)
        if n_fields < n_cols:
            error(f'Found more data columns ({n_cols}) than fieldnames '
                  f'({n_fields}). Giving up.')

        type_info = {
            col: analyse_values(col, [row[i] for row in data if len(row) > i])
            for i, col in enumerate(self.fieldnames)
        }
        cand_nulls = Counter()
        for t in type_info.values():
            if t.poss_null is not None:
                cand_nulls[t.poss_null] += 1

        mode_nulls = dict_max_items(cand_nulls)
        if len(mode_nulls) == 1:
            self.null = list(mode_nulls)[0]
            self.describe_null()
        elif len(cand_nulls) > 1:
            m = mode_nulls[list(mode_nulls)[0]]
            self.print(f'Multiple candidate nulls with frequency {m}', 2)
            self.print('\n'.join(f'  "{n}"' for n in mode_nulls))
            knowns = {k for k in mode_nulls if k in KNOWN_NULLS}
            if knowns:
                ranked = sorted(knowns, key=lambda k: KNOWN_NULLS.index(k))
                self.null = ranked[0]
            else:
                self.null = sorted(cand_nulls)[0]
        else:
            self.print(f'No null detected.', 2)
            self.null = None

        self.fields = [
            FieldMetadata(name=name,
                          fieldtype=type_info[name].most_likely_type)
            for name in self.fieldnames
        ]
        self.quoting = self.infer_quoting(data, is_quoted, n_quoted)

    def dequote_and_split(self, line):
        raw_row = line.split(self.sep)
        q = self.quote_char
        if len(raw_row) > self.n_fieldnames:
            pass
            # more values than fields in header
            error('Too many values')
        elif q is not None and any(v.startswith(q) and not v.endswith(q)
                                   for v in raw_row):
            raw_row = careful_split(line, self.sep, self.quote_char,
                                self.escape_char)
            if raw_row is None:
                error('Can\'t split line')
        if q:
            deq_row, is_quoted = self.dequote(raw_row)
        else:
            deq_row = raw_row[:]
            is_quoted = [False] * len(deq_row)
        return raw_row, deq_row, is_quoted

    def infer_quoting(self, data, quoted, n_quoted):
        return
        debug('DATA:\n', data)
        debug('QUOTED:\n', quoted)
        debug('N QUOTED:\n', n_quoted)
        debug('QUOTE CHAR:', self.quote_char)
        debug(self.fields)


    def describe_null(self):
        if self.null in KNOWN_NULLS:
            self.print(f'Null: "{self.null}"', 2)
        else:
            if self.verbosity > 0:
                warn(f'Unusual null: "{self.null}".')


    def dequote(self, row):
        # Strip pairs of opening and closing quote for each element in row.
        # Also restores replaced characters based on map
        # Return list of dequoted values and list of booleans
        # saying whether each was quoted
        q = self.quote_char or '"'
        is_quoted = [
            s.startswith(q) and s.endswith(q)
            for s in row
        ]
        out = [
            s[1:-1] if s.startswith(q) and s.endswith(q) else s
            for s in row
        ]
        for k, v in self.restorations.items():
            out = [s.replace(k, v) for s in out]
        print(out)
        print(is_quoted)
        print()
        return out, is_quoted


def infer_format_from_flat_file(path, lines_to_use=1000, verbosity=None):
    inferrer = MetadataInferrer(path, lines_to_use, verbosity=verbosity)
    return inferrer.metadata


def count(char, lines):
    return sum(sum(c == char for c in line) for line in lines)


def careful_split(line, sep, quote, escape):
    pos = 0
    out = []
    parts = line.split(sep)
    i = field = 0
    out = []
    while i < len(parts):
        part = parts[i]
        while part.startswith(quote) and not part.endswith(quote):
            i += 1
            if i < len(parts):
                part += f',{parts[i]}'
            else:
                warn('Unbalanced quotes found')
                return None
        out.append(part)
        i += 1

    return out



class TypeStats:
    """
    Container for information about possible validity of a set of
    string values (from a field) for the type specified.
    """
    def __init__(self, type_):
        self.type_ = type_  # Not really used by this class (for info)
        self.n_valid = 0
        self.n_invalid = 0
        self.invalids = Counter()
        self.n_distinct_invalids = 0
        self.poss_null = None


    def summarize(self):
        self.n_distinct_invalids = len(self.invalids)
        self.n_invalid = sum(self.invalids.values())
        if self.invalids:
            modes = dict_max_items(self.invalids)
            if len(modes) == 1:
                self.poss_null = list(modes)[0]

        # Potentially valid as this type if null is poss_null
        self.all_poss_valid = (
            self.n_invalid == 0 or (
                self.n_distinct_invalids == 1
                and self.poss_null is not None
            )
        )

    def __str__(self):
        """
        This string function reports whether the values are all
        compatible with this type for some possible null indicator.
        """
        null = (
            f': {self.n_valid} valid + {self.n_invalid} null if null is '
            f'"{self.poss_null}"'
        ) if self.poss_null else ''
        return (
            f'poss {self.type_}{null}'
            if self.all_poss_valid
            else ''
        )


class FieldTypeStats:
    def __init__(self, fieldname):
        self.fieldname = fieldname
        self.stats = {
            'bool': TypeStats('bool'),
            'int': TypeStats('int'),
            'float': TypeStats('float'),
            'date': TypeStats('date'),
            'datetime': TypeStats('datetime'),
        }

    def summarize(self):
        for stats in self.stats.values():
            stats.summarize()
        m = max(stats.n_valid for stats in self.stats.values())
        if m == 0:
            self.most_likely_type = 'string'
            self.poss_null = None
        else:
            most_likelies = {
                k: v for k, v in self.stats.items()
                if v.n_valid == m
            }
            if len(most_likelies) == 1:
                t = self.most_likely_type = list(most_likelies)[0]
            elif set(most_likelies) == {'int', 'float'}:
                t = self.most_likely_type = 'int'
            else:  # set to list if can't tell
                self.most_likely_type = list(most_likelies)
                t = self.most_likely_type[0]
            self.poss_null = self.stats[t].poss_null
        self.summarized = True

    def __str__(self):
        if not getattr(self, 'summarized'):
            error('Not summarized')
        stats = '\n  '.join(str(v) for v in self.stats.values() if str(v))
        if not stats:
            stats = 'Poss string'
        return f'Field {self.fieldname}: {self.most_likely_type}\n  {stats}\n'


def analyse_values(fieldname, values):
    stats = FieldTypeStats(fieldname)
    b = stats.stats['bool']
    i = stats.stats['int']
    f = stats.stats['float']
    d = stats.stats['date']
    dt = stats.stats['datetime']

    for v in values:
        if v.lower() in ('true', 'false'):
            b.n_valid += 1
        else:
            b.invalids[v] += 1

        if v and v.isdigit() or (v[1:].isdigit() and v[:1] in '+-'):
            i.n_valid += 1
        else:
            i.invalids[v] += 1

        try:
            float(v)
            f.n_valid += 1
        except ValueError:
            f.invalids[v] += 1

        if re.match(DATEISH, v) or re.match(ADATEISH, v):
            d.n_valid += 1
        else:
            d.invalids[v] += 1

        if re.match(DTISH, v) or re.match(ADTISH, v):
           dt.n_valid += 1
        else:
            dt.invalids[v] += 1

    stats.summarize()
    return stats
