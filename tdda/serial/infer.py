import re
import os
import sys

from collections import namedtuple, Counter

TypeStats = namedtuple('TypeStats', 'field stats')

from tdda.serial.dateutils import (
    AMBIGUOUS_DATE_FORMATS,
    infer_date_format_from_strings,
    resolve_ambiguous_format,
)
from tdda.serial.metadata import (
    SerialMetadata,
    FieldMetadata,
    FieldType,
    STRFTIME_TO_NAMED_FORMAT,
)
from tdda.utils import TDDAError, warn, error, nvl, debug, testwarn
from tdda.referencetest.utils import FileType
from tdda.serial.utils import non_chars, dict_max_items


KNOWN_NULLS = [
    '',
    'NULL',
    'NA',
    '<NA>',
    'N/A',
    'None',
    'nan',
    'null',
    'null ',
    'Null',
    'na',
    'Na',
    '-',
    '-',
    'x',
    'XNaN',
    'n/a',
    '#NA',
    '#N/A',
    '-NaN',
    '-nan',
    '#N/A N/A',
    '-1.#IND',
    '-1.#QNAN',
    '1.#IND',
    '1.#QNAN',
    ' ',
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

NO_DELIMITER = chr(0)

# Strict: standard code identifier (letters, digits, underscores)
STRICT_NAME_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
# Extended: allows dots, dashes, spaces (CH-style dotted/spaced names)
EXTENDED_NAME_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_./ -]*$')
# Human: starts with a Unicode letter or underscore, contains anything
# printable that isn't a separator
HUMAN_NAME_RE = re.compile(
    r'^[^\W\d_].*$|^[a-zA-Z_]', re.UNICODE
)
NUMERIC_RE = re.compile(r'^-?[0-9]+(\.[0-9]+)?$')

SEP_CHARS = (',', '|', '\t', ';')

ENCODING_FALLBACKS = ['utf-8', 'utf-8-sig', 'utf-16', 'latin-1']

# Values that are almost certainly data, not field names, even if they
# look like identifiers (e.g. 'false' matches STRICT_NAME_RE).
KNOWN_DATA_VALUES = {
    'true', 'false', 'yes', 'no', 'null', 'none', 'nan', 'na',
    'True', 'False', 'Yes', 'No', 'Null', 'None', 'Nan', 'Na',
    'TRUE', 'FALSE', 'YES', 'NO', 'NULL', 'NONE', 'NAN', 'NA',
}


def _has_cp1252_bytes(path):
    # Bytes 0x80-0x9F are printable in cp1252 but control codes in latin-1.
    # If any are present the file is almost certainly cp1252.
    with open(path, 'rb') as f:
        chunk = f.read(65536)
    return any(0x80 <= b <= 0x9F for b in chunk)


def read_file_lines(path, initial_enc=None, lines_to_use=1000):
    """Read header and data lines from path with encoding fallback.

    Tries initial_enc first, then each encoding in ENCODING_FALLBACKS.
    Promotes latin-1 to cp1252 when 0x80-0x9F bytes are present.

    Returns (header, datalines, enc_used), or (None, [], None) if all
    encodings fail.
    """
    candidates = [initial_enc] + [
        e for e in ENCODING_FALLBACKS if e != initial_enc
    ]
    for enc in candidates:
        datalines = []
        try:
            with open(path, encoding=enc) as f:
                header = f.readline().rstrip()
                while not header.strip():
                    header = f.readline()
                for _ in range(lines_to_use):
                    line = f.readline().strip()
                    if line:
                        datalines.append(line)
            if enc == 'latin-1' and _has_cp1252_bytes(path):
                enc = 'cp1252'
            return header, datalines, enc
        except UnicodeDecodeError:
            continue
    return None, [], None


class FirstLineStats:
    """Stats and provisional conclusions from the first (header) line."""

    def __init__(self, line, single_field=False):
        self.line = line
        self.n_commas = line.count(',')
        self.n_pipes = line.count('|')
        self.n_tabs = line.count('\t')
        self.n_semis = line.count(';')
        self.n_spaces = line.count(' ')
        self.n_dquotes = line.count('"')
        self.n_squotes = line.count("'")
        self.n_backslashes = line.count('\\')

        if single_field:
            self.sep = NO_DELIMITER
        else:
            self.sep = self._infer_sep()
        self.quote_char = self._infer_quote_char()
        self.fieldnames = self._split_fieldnames()
        self._analyse_fieldnames()
        self._detect_escape_stutter()

    def _infer_sep(self):
        counts = {
            ',': self.n_commas,
            '|': self.n_pipes,
            '\t': self.n_tabs,
            ';': self.n_semis,
        }
        best = max(counts.values())
        if best == 0:
            return []
        return [c for c, n in counts.items() if n == best]

    def _infer_quote_char(self):
        if self.n_dquotes > 0 and self.n_dquotes % 2 == 0:
            return '"'
        # Backslash-escaped single quote is strong evidence ' is the quote char,
        # even when apostrophes make the plain even-count test unreliable.
        if "\\'" in self.line:
            return "'"
        if (self.n_squotes > 0 and self.n_squotes % 2 == 0
                and self.n_squotes > self.n_backslashes * 2):
            return "'"
        return None

    def _split_fieldnames(self):
        if not self.sep:
            return [self.line]
        # Use first candidate sep for splitting (ties resolved later)
        s = self.sep[0]
        q = self.quote_char
        if q and q in self.line:
            result = careful_split(self.line, s, q, '\\')
            if result is not None:
                return result
        return self.line.split(s)

    def _analyse_fieldnames(self):
        names = self.fieldnames
        self.n_fields = len(names)
        q = self.quote_char
        # Dequote for analysis purposes
        stripped = [
            n.strip()[1:-1] if q and n.strip().startswith(q)
            and n.strip().endswith(q) and len(n.strip()) >= 2
            else n.strip()
            for n in names
        ]
        self.n_empty = sum(1 for n in stripped if not n)
        self.n_numeric = sum(1 for n in stripped if NUMERIC_RE.match(n))
        self.n_strict = sum(1 for n in stripped if STRICT_NAME_RE.match(n))
        self.n_extended = sum(
            1 for n in stripped
            if not STRICT_NAME_RE.match(n) and EXTENDED_NAME_RE.match(n)
        )
        self.n_human = sum(
            1 for n in stripped
            if not EXTENDED_NAME_RE.match(n) and HUMAN_NAME_RE.match(n)
        )
        self.n_name_like = self.n_strict + self.n_extended + self.n_human
        self.n_other = (
            self.n_fields - self.n_empty
            - self.n_numeric - self.n_name_like
        )
        self.n_with_space = sum(1 for n in stripped if n and ' ' in n)
        self.n_boolean = sum(1 for n in stripped if n in KNOWN_DATA_VALUES)
        total = self.n_fields
        name_ratio = self.n_name_like / total if total else 0
        self.looks_like_header = (
            name_ratio >= 0.75
            and self.n_empty <= 1
            and self.n_numeric == 0
            # Single-field: prose (has spaces) or known data value → not a header
            and not (self.n_fields == 1 and self.n_with_space > 0)
            and not (self.n_fields == 1 and self.n_boolean > 0)
        )

    def _detect_escape_stutter(self):
        q = self.quote_char
        self.has_stutter = False
        self.has_backslash_escape = False
        if q:
            qq = q + q
            bq = f'\\{q}'
            for field in self.fieldnames:
                f = field.strip()
                if bq in f:
                    self.has_backslash_escape = True
                # Only count qq as stutter if not preceded by backslash
                s = f.replace(bq, '')
                if qq in s:
                    self.has_stutter = True

    def __str__(self):
        sep = (
            repr(self.sep[0]) if len(self.sep) == 1
            else repr(self.sep)
            if self.sep
            else '[]'
        )
        q = repr(self.quote_char)
        return (
            f'FirstLineStats(\n'
            f'    sep={sep},\n'
            f'    q={q},\n'
            f'    fields={self.n_fields},\n'
            f'    strict={self.n_strict},\n'
            f'    ext={self.n_extended},\n'
            f'    human={self.n_human},\n'
            f'    empty={self.n_empty},\n'
            f'    numeric={self.n_numeric},\n'
            f'    other={self.n_other},\n'
            f'    stutter={self.has_stutter},\n'
            f'    esc={self.has_backslash_escape},\n'
            f'    header={self.looks_like_header},\n'
            f')'
        )


class SampleStats:
    """Per-line character counts for separator consistency checking."""

    def __init__(self, lines):
        self.counts = {c: [] for c in SEP_CHARS}
        self.counts['\\'] = []
        self.counts['"'] = []
        self.counts["'"] = []
        for line in lines:
            for c in self.counts:
                self.counts[c].append(line.count(c))

    def consistency(self, char):
        """Return (min, max, mode) count for char across sample lines."""
        vals = self.counts.get(char, [])
        if not vals:
            return 0, 0, 0
        mn = min(vals)
        mx = max(vals)
        mode = Counter(vals).most_common(1)[0][0]
        return mn, mx, mode

    def consistent_sep(self, char):
        """True if char count is identical across all sample lines."""
        mn, mx, _ = self.consistency(char)
        return mn == mx and mn > 0


class MetadataInferrer:
    def __init__(
        self, inpath, lines_to_use=1000, verbosity=None, single_field=None,
        warner=None, add_defaults=False, report_added_defaults=True,
        raise_error=False
    ):
        self.inpath = os.path.expanduser(inpath)
        self.lines_to_use = lines_to_use
        self.verbosity = nvl(verbosity, 10)
        self.single_field = single_field
        self.warn = nvl(warner, warn)
        self.add_defaults = add_defaults
        self.report_added_defaults = report_added_defaults
        self.raise_error = raise_error
        self.read()
        self.process()

        self.metadata = SerialMetadata(
            fields=self.fields,
            encoding=self._default(self.encoding, 'UTF-8', 'encoding'),
            delimiter=self.sep,
            stutter_quotes=self.stutter,
            escape_char=self.escape,
            quote_char=self._default(self.quote_char, '"', 'quote_char'),
            null_indicator=self.null,
            date_format=self.date_format,
            datetime_format=self.datetime_format,
        )

    def vprint(self, msg, min_verbosity=1):
        if self.verbosity >= min_verbosity:
            self.warn(msg)

    def _default(self, value, default, name):
        if value is not None:
            return value
        if self.add_defaults:
            if self.report_added_defaults:
                self.warn(f'{name}: {default!r} (default, no evidence)')
            return default
        return None

    def read(self):
        enc = nvl(FileType(self.inpath).encoding, 'UTF-8')
        self.encoding = None if enc == 'ascii' else enc
        self.datalines = datalines = []
        enc_used = self._open_with_fallback(datalines)
        if enc_used != self.encoding:
            self.encoding = enc_used

    def _open_with_fallback(self, datalines):
        header, lines, enc = read_file_lines(
            self.inpath, self.encoding, self.lines_to_use
        )
        if header is None:
            error(
                f'Cannot read file {self.inpath!r}: tried encodings '
                f'{ENCODING_FALLBACKS}; all failed.',
                raise_error=self.raise_error,
            )
            return None
        self.header = header
        datalines.extend(lines)
        if enc != self.encoding:
            self.warn(
                f'Encoding {self.encoding!r} failed; reading as {enc!r}.'
            )
        return enc

    def process(self):
        header = self.header
        self.all_lines = lines = [self.header] + self.datalines

        self.sep = sep = self.find_separator()
        self.quote_char, self.escape, self.stutter = self.find_quote_chars()

        sep_replacement, qq_replacement = non_chars(lines, 2)
        restorations = self.restorations = {}

        escaped_sep = f'\\{sep}'
        for i, line in enumerate(lines):
            if escaped_sep in line:
                lines[i] = line.replace(escaped_sep, sep_replacement)
                restorations[sep_replacement] = sep

        fieldnames = self.find_fieldnames()
        self.n_fieldnames = len(fieldnames)

        quote = self.quote_char
        plain_fieldnames, _ = self.dequote(fieldnames)
        if plain_fieldnames != fieldnames:
            self.quote_char = quote
            plain_fieldnames = header.split(sep)
        if quote:
            restorations[qq_replacement] = quote

        self.fieldnames = plain_fieldnames
        self.data = lines[1:]

        self.vprint(f'Inferred escape: {self.escape}.', 2)
        self.vprint(f'Inferred stutter: {self.stutter}.', 2)
        self.infer_fields()

    def find_separator(self):
        if self.single_field:
            return NO_DELIMITER
        lines = self.all_lines
        n_commas = count(',', lines)
        n_pipes = count('|', lines)
        n_tabs = count('\t', lines)
        n_semis = count(';', lines)

        M = max((n_commas, n_pipes, n_tabs, n_semis))
        if M == 0:
            error(
                'Separator does not appear to be comma, pipe, tab'
                ' or semicolon. Abandoning.',
                raise_error=self.raise_error,
            )

        sep = (
            ','
            if n_commas == M
            else '|'
            if n_pipes == M
            else '\t'
            if n_tabs == M
            else ';'
        )
        self.vprint(f'Inferred separator: {sep} ({M} occurrences).', 2)
        return sep

    def find_quote_chars(self):
        lines = self.all_lines
        n_dquotes = count('"', lines)
        n_squotes = count("'", lines)
        self.n_quotes = max(n_dquotes, n_squotes)
        if self.n_quotes == 0:
            return None, None, None
        # But apostrophes...quoted or not.
        quote = "'" if n_squotes > n_dquotes else '"'
        return quote, None, None

    def find_fieldnames(self):
        fieldnames = self.header.split(self.sep)
        quote = self.quote_char
        if quote and any(
            f.startswith(quote) and not f.endswith(quote) for f in fieldnames
        ):
            return careful_split(self.header, sep, quote, '\\')
        else:
            return fieldnames

    def infer_fields(self):
        sep = self.sep
        combined = [
            self.dequote_and_split(row, i)
            for i, row in enumerate(self.data, 2)
        ]
        is_quoted = [r[2] for r in combined]
        data = [r[1] for r in combined]
        raw = [r[0] for r in combined]
        m = min(len(row) for row in data)
        M = max(len(row) for row in data)
        nFields = len(self.fieldnames)
        excel = not (m == M)
        if excel:
            self.vprint('Rows have different numbers of values.', 2)
        else:
            self.vprint('All rows complete', 2)

        self.vprint(
            f'Fieldnames {nFields}. '
            f'Min fields in row: {m}. Max fields in row: {M}\n',
            2,
        )
        if M > nFields:
            self.vprint('More cols in some rows than fields (headers)', 2)
        if nFields > M:
            self.vprint('All rows lack at least one field.', 2)
        n = max(nFields, M)

        # Number quoted by column index
        n_quoted = {
            i: sum((q[i] if i < len(q) else 0) for q in is_quoted)
            for i in range(n)
        }
        self.vprint(f'Number quoted by col index: {n_quoted}', 2)
        total_quoted = sum(n_quoted.values())
        self.vprint(f'Total number quoted: {total_quoted}', 2)

        n_cols = max(len(row) for row in data)
        n_fields = len(self.fieldnames)
        if n_fields < n_cols:
            error(
                f'Found more data columns ({n_cols}) than fieldnames '
                f'({n_fields}). Giving up.',
                raise_error=self.raise_error,
            )

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
            self.vprint(f'Multiple candidate nulls with frequency {m}', 2)
            self.vprint('\n'.join(f'  "{n}"' for n in mode_nulls))
            knowns = {k for k in mode_nulls if k in KNOWN_NULLS}
            if knowns:
                ranked = sorted(knowns, key=lambda k: KNOWN_NULLS.index(k))
                self.null = ranked[0]
            else:
                self.null = sorted(cand_nulls)[0]
        else:
            self.vprint(f'No null detected.', 2)
            self.null = None

        null_val = self.null or ''
        field_values = {
            name: [
                v
                for v in [row[i] for row in data if len(row) > i]
                if v != null_val and v != ''
            ]
            for i, name in enumerate(self.fieldnames)
        }

        # Phase 1: infer raw format for each date/datetime field
        raw_date_fmts = {}   # name -> fmt (may be AmbiguousDateFormat.*)
        raw_dt_fmts = {}     # name -> fmt (may be AmbiguousDateFormat.*)
        for name in self.fieldnames:
            t = type_info[name].most_likely_type
            if isinstance(t, str) and t in ('date', 'datetime'):
                fmt = infer_date_format_from_strings(field_values[name])
                if fmt is not None:
                    if t == 'date':
                        raw_date_fmts[name] = fmt
                    else:
                        raw_dt_fmts[name] = fmt

        # Phase 2: determine EU/US convention from unambiguous fields
        eu_count = sum(
            1 for fmt in {**raw_date_fmts, **raw_dt_fmts}.values()
            if fmt not in AMBIGUOUS_DATE_FORMATS and fmt.startswith('%d')
        )
        us_count = sum(
            1 for fmt in {**raw_date_fmts, **raw_dt_fmts}.values()
            if fmt not in AMBIGUOUS_DATE_FORMATS and fmt.startswith('%m')
        )
        if eu_count > 0 or us_count > 0:
            convention = 'eu' if eu_count >= us_count else 'us'
            convention_reason = (
                f'assuming {convention.upper()} based on other date fields'
            )
        else:
            convention = 'eu'
            convention_reason = 'defaulting to EU'

        # Phase 3: resolve ambiguous formats, warn, build final dicts
        date_only_fmts = {}
        datetime_fmts = {}
        for raw_fmts, final_fmts, label in (
            (raw_date_fmts, date_only_fmts, 'date'),
            (raw_dt_fmts, datetime_fmts, 'datetime'),
        ):
            for name, fmt in raw_fmts.items():
                if fmt in AMBIGUOUS_DATE_FORMATS:
                    resolved = resolve_ambiguous_format(
                        field_values[name], fmt, convention
                    )
                    if resolved is not None:
                        self.warn(
                            f'Field "{name}": ambiguous {label} format'
                            f' (EU or US); {convention_reason}.'
                        )
                        final_fmts[name] = resolved
                else:
                    final_fmts[name] = fmt

        # Hoist date_format (pure date fields only)
        unique_date_fmts = set(date_only_fmts.values())
        if len(unique_date_fmts) == 1:
            self.date_format = list(unique_date_fmts)[0]
            field_date_fmts = {}
        elif len(unique_date_fmts) > 1:
            named = {STRFTIME_TO_NAMED_FORMAT.get(f) for f in unique_date_fmts}
            if len(named) == 1 and None not in named:
                self.date_format = list(named)[0]
                field_date_fmts = {}
            else:
                self.date_format = None
                field_date_fmts = date_only_fmts
        else:
            self.date_format = None
            field_date_fmts = {}

        # Hoist datetime_format (datetime fields only)
        unique_dt_fmts = set(datetime_fmts.values())
        if len(unique_dt_fmts) == 1:
            self.datetime_format = list(unique_dt_fmts)[0]
            field_dt_fmts = {}
        elif len(unique_dt_fmts) > 1:
            named = {STRFTIME_TO_NAMED_FORMAT.get(f) for f in unique_dt_fmts}
            if len(named) == 1 and None not in named:
                self.datetime_format = list(named)[0]
                field_dt_fmts = {}
            else:
                self.datetime_format = None
                field_dt_fmts = datetime_fmts
        else:
            self.datetime_format = None
            field_dt_fmts = {}

        field_fmts = {**field_date_fmts, **field_dt_fmts}

        self.fields = [
            FieldMetadata(
                name=name,
                fieldtype=type_info[name].most_likely_type,
                format=field_fmts.get(name),
            )
            for name in self.fieldnames
        ]
        self.quoting = self.infer_quoting(data, is_quoted, n_quoted)

    def dequote_and_split(self, line, lineno=None):
        q = self.quote_char
        if q is not None and q in line:
            raw_row = careful_split(line, self.sep, q, self.escape)
            if raw_row is None:
                error("Can't split line", raise_error=self.raise_error)
        else:
            raw_row = line.split(self.sep)
        n = len(raw_row)
        if n > self.n_fieldnames:
            loc = f' at line {lineno}' if lineno is not None else ''
            error(
                f'Too many values for header ({n} vs {self.n_fieldnames})'
                f'{loc}.',
                raise_error=self.raise_error,
            )
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
            self.vprint(f'Null: "{self.null}"', 2)
        else:
            if self.verbosity > 0:
                self.warn(f'Unusual null: "{self.null}".')

    def dequote(self, row):
        # Strip pairs of opening and closing quote for each element in row.
        # Also restores replaced characters based on map
        # Return list of dequoted values and list of booleans
        # saying whether each was quoted
        q = self.quote_char or '"'
        is_quoted = [s.startswith(q) and s.endswith(q) for s in row]
        out = [
            s[1:-1] if s.startswith(q) and s.endswith(q) else s for s in row
        ]
        for k, v in self.restorations.items():
            out = [s.replace(k, v) for s in out]
        return out, is_quoted


def infer_format_from_flat_file(
    path, lines_to_use=1000, warner=None,
    add_defaults=False, report_added_defaults=True,
    raise_error=False, **kw
):
    inferrer = MetadataInferrer(
        path, lines_to_use, warner=warner,
        add_defaults=add_defaults,
        report_added_defaults=report_added_defaults,
        raise_error=raise_error,
        **kw
    )
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
        self.all_poss_valid = self.n_invalid == 0 or (
            self.n_distinct_invalids == 1 and self.poss_null is not None
        )

    def __str__(self):
        """
        This string function reports whether the values are all
        compatible with this type for some possible null indicator.
        """
        null = (
            (
                f': {self.n_valid} valid + {self.n_invalid} null if null is '
                f'"{self.poss_null}"'
            )
            if self.poss_null
            else ''
        )
        return f'poss {self.type_}{null}' if self.all_poss_valid else ''


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
                k: v for k, v in self.stats.items() if v.n_valid == m
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
            error('Not summarized', raise_error=self.raise_error)
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
