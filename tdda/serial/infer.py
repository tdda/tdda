import re
import os
import sys

from collections import namedtuple, Counter

from tdda.serial.dateutils import (
    AMBIGUOUS_DATE_FORMATS,
    infer_date_format_from_strings,
    resolve_ambiguous_format,
    strftime_to_yyyydate,
)
from tdda.serial.metadata import (
    SerialMetadata,
    FieldMetadata,
    FieldType,
    QUOTING_CODES,
    NAMED_FORMAT_TO_STRFTIME,
    STRFTIME_TO_NAMED_FORMAT,
)
from tdda.utils import TDDAError, warn, error, nvl, debug, testwarn
from tdda.referencetest.utils import FileType
from tdda.serial.utils import non_chars, dict_max_items


def _to_yyyy(fmt):
    if fmt is None:
        return None
    yyyy = strftime_to_yyyydate(fmt)
    return yyyy if '%' not in yyyy else fmt


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
    'NaN',
    'NaT',
    'nat',
    'NAT',
]

DATEISH = re.compile('^[0-9]{2,4}[-./][0-9]{2}[-./][0-9]{2,4}$')
ADATEISH = re.compile(
    r'^([0-9]{2,4}|[a-zA-Z]{3,9})[-. /]([0-9]{2}|[a-zA-Z]{3,9})'
    r'[-. /][0-9]{2,4}$'
    r'|^[a-zA-Z]{3,9} [0-9]{1,2}, [0-9]{2,4}$',
    re.IGNORECASE,
)

DTISH = re.compile(
    r'^[0-9]{2,4}[-./][0-9]{2}[-./][0-9]{2,4}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}.*$'
)
ADTISH = re.compile(
    r'^([0-9]{2,4}|[a-zA-Z]{3,9})[-. /]([0-9]{2}|[a-zA-Z]{3,9})'
    r'[-. /][0-9]{2,4}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}.*$'
    r'|^[a-zA-Z]{3,9} [0-9]{1,2}, [0-9]{2,4}[ T][0-9]{2}:[0-9]{2}:[0-9]{2}.*$',
    re.IGNORECASE,
)

NO_DELIMITER = chr(0)

# Strict: standard code identifier (letters, digits, underscores)
STRICT_NAME_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*$')
# Extended: allows dots, dashes, spaces (CH-style dotted/spaced names)
EXTENDED_NAME_RE = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_./ -]*$')
# Human: starts with a Unicode letter or underscore, contains anything
# printable that isn't a separator
HUMAN_NAME_RE = re.compile(r'^[^\W\d_].*$|^[a-zA-Z_]', re.UNICODE)
NUMERIC_RE = re.compile(r'^-?[0-9]+(\.[0-9]+)?$')

SEP_CHARS = (',', '|', '\t', ';')

ENCODING_FALLBACKS = ['utf-8', 'utf-8-sig', 'utf-16', 'latin-1']

# Aliases that chardet returns for latin-1 / ISO-8859-1 across versions.
_LATIN1_ALIASES = frozenset(
    [
        'latin-1',
        'latin1',
        'iso-8859-1',
        'iso8859-1',
        'iso_8859-1',
        '8859-1',
        'csisolatin1',
        'l1',
    ]
)


def normalize_encoding(enc):
    """Map chardet encoding aliases to canonical Python codec names."""
    if enc is None:
        return None
    if enc.lower().replace('_', '-') in _LATIN1_ALIASES:
        return 'latin-1'
    return enc


# Values that are almost certainly data, not field names, even if they
# look like identifiers (e.g. 'false' matches STRICT_NAME_RE).
KNOWN_DATA_VALUES = {
    'true',
    'false',
    'yes',
    'no',
    'null',
    'none',
    'nan',
    'na',
    'True',
    'False',
    'Yes',
    'No',
    'Null',
    'None',
    'Nan',
    'Na',
    'TRUE',
    'FALSE',
    'YES',
    'NO',
    'NULL',
    'NONE',
    'NAN',
    'NA',
}

MIN_VALID_OR_NULL_TYPE = 0.99  # At least this prop valid or null
MIN_NAME_RATIO = 0.75
DEFAULT_SAMPLE_LINES = 1000


def _has_cp1252_bytes(path):
    # Bytes 0x80-0x9F are printable in cp1252 but control codes in latin-1.
    # If any are present the file is almost certainly cp1252.
    with open(path, 'rb') as f:
        chunk = f.read(65536)
    return any(0x80 <= b <= 0x9F for b in chunk)


def read_file_lines(
    path, initial_enc=None, lines_to_use=1000, raise_error=False
):
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
        except UnicodeError:
            continue
        except FileNotFoundError as e:
            error(str(e), raise_error=raise_error)
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
        if (
            self.n_squotes > 0
            and self.n_squotes % 2 == 0
            and self.n_squotes > self.n_backslashes * 2
        ):
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
            n.strip()[1:-1]
            if q
            and n.strip().startswith(q)
            and n.strip().endswith(q)
            and len(n.strip()) >= 2
            else n.strip()
            for n in names
        ]
        self.n_empty = sum(1 for n in stripped if not n)
        self.n_numeric = sum(1 for n in stripped if NUMERIC_RE.match(n))
        self.n_strict = sum(1 for n in stripped if STRICT_NAME_RE.match(n))
        self.n_extended = sum(
            1
            for n in stripped
            if not STRICT_NAME_RE.match(n) and EXTENDED_NAME_RE.match(n)
        )
        self.n_human = sum(
            1
            for n in stripped
            if not EXTENDED_NAME_RE.match(n) and HUMAN_NAME_RE.match(n)
        )
        self.n_name_like = self.n_strict + self.n_extended + self.n_human
        self.n_other = (
            self.n_fields - self.n_empty - self.n_numeric - self.n_name_like
        )
        self.n_with_space = sum(1 for n in stripped if n and ' ' in n)
        self.n_boolean = sum(1 for n in stripped if n in KNOWN_DATA_VALUES)
        total = self.n_fields
        name_ratio = self.n_name_like / total if total else 0
        self.looks_like_header = (
            name_ratio >= MIN_NAME_RATIO
            and self.n_empty <= 1
            and self.n_numeric == 0
            # Single-field: prose (has spaces) or known data value
            #  → not a header
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
            repr(self.sep[0])
            if len(self.sep) == 1
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


class SplitCounts:
    """Accumulated escape/stutter pattern counts across data lines."""

    def __init__(self):
        self.n_dq_stutter = 0  # "" inside a dq-quoted field
        self.n_sq_stutter = 0  # '' inside a sq-quoted field
        self.n_dq_esc = 0  # \" anywhere
        self.n_sq_esc = 0  # \' anywhere
        self.n_bs_esc = 0  # \\ anywhere
        self.n_esc_sep = 0  # \sep in unquoted field
        self.n_fast = 0  # lines taking fast path
        self.n_careful = 0  # lines taking careful path


class MetadataInferrer:
    def __init__(
        self,
        inpath,
        lines_to_use=None,
        verbosity=None,
        single_field=None,
        warner=None,
        add_defaults=False,
        report_added_defaults=True,
        raise_error=False,
        delimiter=None,
        quote_char=None,
        escape=None,
        no_escape=False,
        stutter=None,
        null=None,
        encoding=None,
        date_format=None,
        datetime_format=None,
        header_row_count=None,
        quoting=None,
    ):
        self.inpath = os.path.expanduser(inpath) if inpath else None
        self.lines_to_use = nvl(lines_to_use, DEFAULT_SAMPLE_LINES)
        self.verbosity = nvl(verbosity, 10)
        self.single_field = single_field
        self.warn = nvl(warner, warn)
        self.add_defaults = add_defaults
        self.report_added_defaults = report_added_defaults
        self.raise_error = raise_error
        self._given = {
            'sep': delimiter,
            'quote_char': quote_char,
            'escape': None if no_escape else escape,
            'no_escape': no_escape,
            'stutter': stutter,
            'null': null,
            'encoding': encoding,
            'date_format': date_format,
            'datetime_format': datetime_format,
            'header_row_count': header_row_count,
            'excel': None,
        }
        if inpath:
            self.read()
            self.process()
        else:  # No file given: just generate from params (or defaults)
            self.apply_all_given()
            self.fields = []
        if quoting is not None:
            quoting = quoting.upper()
            if quoting not in QUOTING_CODES:
                valid = ', '.join(sorted(QUOTING_CODES))
                raise TDDAError(
                    f'Invalid quoting style {quoting!r}. Valid values: {valid}.'
                )
            self.quoting = quoting

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
            header_row_count=self.header_row_count,
            map_missing_trailing_cols_to_null=self.excel or None,
            quoting=getattr(self, 'quoting', None),
        )

    def apply_all_given(self):
        for k in self._given:
            self._apply_given(k)

    def _apply_given(self, attr, name=None):
        """
        Apply a given value if provided, warning if it differs from inferred.
        """
        value = self._given.get(attr)
        if value is None and hasattr(self, attr):
            return
        inferred = getattr(self, attr, None)
        if inferred is not None and inferred != value:
            name = nvl(name, attr)
            self.vprint(f'{name}: {value!r} (inferred {inferred!r})')
        setattr(self, attr, value)

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
        if self._given['encoding'] is None:
            enc = normalize_encoding(
                nvl(FileType(self.inpath).encoding, 'UTF-8')
            )
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

        self.fls = FirstLineStats(header)
        self.ss = SampleStats(self.datalines)
        self.sep = sep = nvl(self._given['sep'], self.reconcile_sep())

        self.quote_char, self.escape, self.stutter = self.find_quote_chars()

        sep_replacement, qq_replacement = non_chars(lines, 2)
        restorations = self.restorations = {}

        escaped_sep = f'\\{sep}'
        for i, line in enumerate(lines):
            if escaped_sep in line:
                lines[i] = line.replace(escaped_sep, sep_replacement)
                restorations[sep_replacement] = sep

        self.has_header = self.fls.looks_like_header
        self.header_row_count = 1 if self.has_header else 0
        self.vprint(f'Header row: {self.has_header}.', 2)

        if self.has_header:
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
        else:
            # No header: generate synthetic field names from field count
            n_fields = len(header.split(sep)) if sep != NO_DELIMITER else 1
            self.fieldnames = [f'field{i}' for i in range(n_fields)]
            self.n_fieldnames = n_fields
            self.data = lines  # all lines are data

        self.split_data_lines()
        # Apply given quote/escape/stutter after split inference
        self._apply_given('quote_char', 'quote_char')
        if self._given['no_escape']:
            self.escape = None
        else:
            self._apply_given('escape', 'escape_char')
        self._apply_given('stutter', 'stutter_quotes')
        self.vprint(f'Inferred escape: {self.escape}.', 2)
        self.vprint(f'Inferred stutter: {self.stutter}.', 2)
        self.infer_fields()
        # Apply given null/date formats after field type inference
        self._apply_given('null', 'null_indicator')
        self._apply_given('date_format', 'date_format')
        self._apply_given('datetime_format', 'datetime_format')

    def split_data_lines(self):
        """Split all data lines, accumulating escape/stutter counts.

        Sets self.split_rows, self.is_quoted_rows, self.split_counts.
        Then calls _infer_quote_escape_stutter() to update quote_char,
        stutter, escape from the evidence gathered.
        """
        sep = self.sep
        counts = SplitCounts()
        rows = []
        is_quoted_rows = []
        start_lineno = 2 if self.has_header else 1

        for lineno, line in enumerate(self.data, start_lineno):
            if sep == NO_DELIMITER:
                fields = [line]
                iq = [False]
                counts.n_fast += 1
            elif '"' not in line and "'" not in line and '\\' not in line:
                fields = line.split(sep)
                iq = [False] * len(fields)
                counts.n_fast += 1
            else:
                fields, iq = split_line(line, sep, counts)
                # Apply restorations (escaped-sep substitution from process())
                for k, v in self.restorations.items():
                    fields = [f.replace(k, v) for f in fields]
                counts.n_careful += 1

            n = len(fields)
            if n > self.n_fieldnames:
                loc = f' at line {lineno}'
                error(
                    f'Too many values for header ({n} vs {self.n_fieldnames}){loc}.',
                    raise_error=self.raise_error,
                )

            rows.append(fields)
            is_quoted_rows.append(iq)

        self.split_rows = rows
        self.is_quoted_rows = is_quoted_rows
        self.split_counts = counts
        self._infer_quote_escape_stutter()

    def _infer_quote_escape_stutter(self):
        """Update quote_char, stutter, escape from split_counts evidence.

        stutter semantics:
          True  — saw doubled quotes (stuttering confirmed)
          False — saw backslash-escaped quotes (stutter ruled out)
          None  — no evidence either way

        escape_char semantics:
          '\\'  — saw \\, \\quote, or \\sep (meaningful backslash usage)
          None  — no such evidence (\\n etc. are not counted as evidence)
        """
        counts = self.split_counts
        dq_ev = counts.n_dq_stutter + counts.n_dq_esc
        sq_ev = counts.n_sq_stutter + counts.n_sq_esc
        if dq_ev > 0 or sq_ev > 0:
            self.quote_char = '"' if dq_ev >= sq_ev else "'"
        elif self.fls.quote_char:
            self.quote_char = self.fls.quote_char

        stutter_ev = counts.n_dq_stutter + counts.n_sq_stutter
        esc_quote_ev = counts.n_dq_esc + counts.n_sq_esc
        esc_ev = esc_quote_ev + counts.n_bs_esc + counts.n_esc_sep

        if stutter_ev > 0:
            self.stutter = True
        elif esc_quote_ev > 0:
            self.stutter = False

        if esc_ev > 0:
            self.escape = '\\'

    def reconcile_sep(self):
        if self.single_field:
            return NO_DELIMITER

        fls = self.fls
        ss = self.ss

        # Candidates from header line (may be a list of tied winners)
        header_candidates = fls.sep if isinstance(fls.sep, list) else [fls.sep]

        # Consistency of each sep char across body lines
        consistent = [c for c in SEP_CHARS if ss.consistent_sep(c)]

        # Best case: header and body agree on a single separator
        agreed = [c for c in header_candidates if c in consistent]
        if len(agreed) == 1:
            self.vprint(f'Separator {agreed[0]!r}: header and body agree.', 2)
            return agreed[0]
        if len(agreed) > 1:
            # Multiple consistent candidates that header also suggests —
            # pick the one with the highest body count (mode)
            agreed.sort(key=lambda c: ss.consistency(c)[2], reverse=True)
            self.vprint(
                f'Separator {agreed[0]!r}: multiple agreeing candidates,'
                f' picking by body frequency.',
                2,
            )
            return agreed[0]

        # Body consistent but header disagrees (or no header candidates)
        if consistent:
            consistent.sort(key=lambda c: ss.consistency(c)[2], reverse=True)
            self.vprint(
                f'Separator {consistent[0]!r}: body consistent'
                f' (header disagrees or absent).',
                2,
            )
            return consistent[0]

        # Neither header nor body gives a clean answer — fall back to old method
        self.vprint('Separator: no consistent candidate, falling back.', 2)
        return self.find_separator()

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
            return careful_split(self.header, self.sep, quote, '\\')
        else:
            return fieldnames

    def infer_fields(self):
        sep = self.sep
        data = self.split_rows
        is_quoted = self.is_quoted_rows
        m = min(len(row) for row in data)
        M = max(len(row) for row in data)
        nFields = len(self.fieldnames)
        cand_nulls = Counter()

        self.excel = m < nFields
        if self.excel:
            self.vprint('Rows have different numbers of values.', 2)
        else:
            self.vprint('All rows complete', 2)

        self.vprint(
            f'Fieldnames {nFields}. Min fields in row: {m}. Max fields in row: {M}\n',
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

        given_null = self._given.get('null')
        if given_null is not None:
            # User-supplied null: use only those values as nulls during
            # inference, not the default KNOWN_NULLS list.
            kn = given_null if isinstance(given_null, list) else [given_null]
        else:
            kn = None
        type_info = {
            col: analyse_values(
                col,
                [row[i] for row in data if len(row) > i],
                cand_nulls,
                known_nulls=kn,
            )
            for i, col in enumerate(self.fieldnames)
        }

        if cand_nulls:
            nulls = sorted(cand_nulls, key=lambda k: (-cand_nulls[k], k))
            self.null = nulls[0] if len(nulls) == 1 else nulls
            self.describe_null()
        else:
            self.vprint('No null detected.', 2)
            self.null = None

        for v in type_info.values():
            v.summarize(self.null)

        null_set = (
            set(self.null)
            if isinstance(self.null, list)
            else ({self.null} if self.null is not None else set())
        )
        field_values_hashes = {
            name: Counter(
                v
                for v in [row[i] for row in data if len(row) > i]
                if v not in null_set and v != ''
            )
            for i, name in enumerate(self.fieldnames)
        }

        # Phase 1: infer raw format for each date/datetime field
        raw_date_fmts = {}  # name -> fmt (may be AmbiguousDateFormat.*)
        raw_dt_fmts = {}  # name -> fmt (may be AmbiguousDateFormat.*)
        for name in self.fieldnames:
            t = type_info[name].most_likely_type
            if isinstance(t, str) and t in ('date', 'datetime'):
                fmt = infer_date_format_from_strings(
                    list(field_values_hashes[name])
                )
                if fmt is not None:
                    if t == 'date':
                        raw_date_fmts[name] = fmt
                    else:
                        raw_dt_fmts[name] = fmt

        # Phase 2: determine EU/US convention from unambiguous fields
        eu_count = sum(
            1
            for fmt in {**raw_date_fmts, **raw_dt_fmts}.values()
            if fmt not in AMBIGUOUS_DATE_FORMATS and fmt.startswith('%d')
        )
        us_count = sum(
            1
            for fmt in {**raw_date_fmts, **raw_dt_fmts}.values()
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
                        list(field_values_hashes[name]), fmt, convention
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
            self.date_format = _to_yyyy(list(unique_date_fmts)[0])
            field_date_fmts = {}
        elif len(unique_date_fmts) > 1:
            named = {STRFTIME_TO_NAMED_FORMAT.get(f) for f in unique_date_fmts}
            if len(named) == 1 and None not in named:
                self.date_format = _to_yyyy(
                    NAMED_FORMAT_TO_STRFTIME[list(named)[0]]
                )
                field_date_fmts = {}
            else:
                self.date_format = None
                field_date_fmts = {
                    k: _to_yyyy(v) for k, v in date_only_fmts.items()
                }
        else:
            self.date_format = None
            field_date_fmts = {}

        # Hoist datetime_format (datetime fields only)
        unique_dt_fmts = set(datetime_fmts.values())
        if len(unique_dt_fmts) == 1:
            self.datetime_format = _to_yyyy(list(unique_dt_fmts)[0])
            field_dt_fmts = {}
        elif len(unique_dt_fmts) > 1:
            named = {STRFTIME_TO_NAMED_FORMAT.get(f) for f in unique_dt_fmts}
            if len(named) == 1 and None not in named:
                self.datetime_format = _to_yyyy(
                    NAMED_FORMAT_TO_STRFTIME[list(named)[0]]
                )
                field_dt_fmts = {}
            else:
                self.datetime_format = None
                field_dt_fmts = {
                    k: _to_yyyy(v) for k, v in datetime_fmts.items()
                }
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
        if self._refine_empty_null(data, is_quoted):
            self.quoting = self.infer_quoting(data, is_quoted, n_quoted)

    def _refine_empty_null(self, data, quoted):
        """Remove '' from null list if only seen as quoted "" in string cols.

        If '' is a null candidate but every empty field in string columns
        is quoted ("") and no empty fields appear in non-string columns,
        then "" is empty string rather than null, and '' should not be
        treated as a null indicator.

        Returns True if '' was removed (caller should re-run infer_quoting).
        """
        null_list = (
            self.null
            if isinstance(self.null, list)
            else ([self.null] if self.null is not None else [])
        )
        if '' not in null_list:
            return False

        n = len(self.fieldnames)
        string_idxs = {
            i for i, f in enumerate(self.fields) if f.fieldtype == 'string'
        }

        has_unquoted_empty_in_string = False
        has_quoted_nonempty_in_string = False
        has_empty_in_nonstring = False

        for row, iq in zip(data, quoted):
            for i in range(min(n, len(row))):
                q = iq[i] if i < len(iq) else False
                if i in string_idxs:
                    if row[i] == '':
                        if not q:
                            has_unquoted_empty_in_string = True
                    elif q:
                        has_quoted_nonempty_in_string = True
                elif row[i] == '':
                    has_empty_in_nonstring = True

        if has_empty_in_nonstring:
            return False
        if not has_quoted_nonempty_in_string:
            # No quoted values in string cols: no quoting evidence that
            # distinguishes null from empty string, so don't infer '' as null.
            new_nulls = [v for v in null_list if v != '']
            self.null = (
                new_nulls[0]
                if len(new_nulls) == 1
                else (new_nulls if new_nulls else None)
            )
            return True
        if has_unquoted_empty_in_string:
            # Quoted non-empty strings + unquoted empty: '' is genuine null.
            return False

        # '' only seen as quoted "" in string cols: it's empty string, not null
        new_nulls = [v for v in null_list if v != '']
        self.null = (
            new_nulls[0]
            if len(new_nulls) == 1
            else (new_nulls if new_nulls else None)
        )
        return True

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
                f'Too many values for header ({n} vs {self.n_fieldnames}){loc}.',
                raise_error=self.raise_error,
            )
        if q:
            deq_row, is_quoted = self.dequote(raw_row)
        else:
            deq_row = raw_row[:]
            is_quoted = [False] * len(deq_row)
        return raw_row, deq_row, is_quoted

    def infer_quoting(self, data, quoted, n_quoted):
        """Infer quoting style from per-column quoted value counts.

        Returns a quoting style name (e.g. 'QUOTE_STRINGS_ONLY') or None.
        May also update self.fields to reclassify quoted int/float as string
        when QUOTE_STRINGS_ONLY is detected.
        """
        if not self.quote_char:
            return 'QUOTE_NONE'
        if not data:
            return None

        null_set = (
            set(self.null)
            if isinstance(self.null, list)
            else ({self.null} if self.null is not None else set())
        )

        n = len(self.fieldnames)
        nonnull_total = [0] * n
        nonnull_quoted = [0] * n
        null_total = [0] * n
        null_quoted = [0] * n

        for row, iq in zip(data, quoted):
            for i in range(min(n, len(row))):
                val = row[i]
                q = iq[i] if i < len(iq) else False
                if val in null_set or val == '':
                    null_total[i] += 1
                    if q:
                        null_quoted[i] += 1
                else:
                    nonnull_total[i] += 1
                    if q:
                        nonnull_quoted[i] += 1

        # Tri-state per column: True=all quoted, False=none quoted, None=mixed
        def quoting_state(nq, nt):
            if nt == 0:
                return None  # unknown: no non-null values
            if nq == 0:
                return False  # all unquoted
            if nq == nt:
                return True  # all quoted
            return 'mixed'

        col_type = [f.fieldtype for f in self.fields]
        states = [
            quoting_state(nonnull_quoted[i], nonnull_total[i])
            for i in range(n)
        ]

        string_idxs = [i for i, t in enumerate(col_type) if t == 'string']
        numeric_idxs = [
            i for i, t in enumerate(col_type) if t in ('int', 'float')
        ]
        date_idxs = [
            i for i, t in enumerate(col_type) if t in ('date', 'datetime')
        ]
        bool_idxs = [i for i, t in enumerate(col_type) if t == 'bool']

        # QUOTE_NONE: nothing quoted anywhere
        if sum(nonnull_quoted) + sum(null_quoted) == 0:
            return 'QUOTE_NONE'

        # QUOTE_ALL / QUOTE_NOTNULL: every non-null value is quoted
        total_nonnull = sum(nonnull_total)
        if total_nonnull > 0 and sum(nonnull_quoted) == total_nonnull:
            total_null = sum(null_total)
            if total_null > 0 and sum(null_quoted) == total_null:
                return 'QUOTE_ALL'
            return 'QUOTE_NOTNULL'

        # Use unquoted non-string cols as anchor: if we see genuinely unquoted
        # numeric/date/bool cols, any quoted col of those types was misclassified
        # and should be string.
        non_string_idxs = numeric_idxs + date_idxs + bool_idxs
        unquoted_non_string = [
            i for i in non_string_idxs if states[i] is False
        ]
        quoted_non_string = [i for i in non_string_idxs if states[i] is True]
        any_mixed = any(s == 'mixed' for s in states)

        if unquoted_non_string:
            if quoted_non_string:
                # Quoted cols inferred as non-string are actually string.
                for i in quoted_non_string:
                    f = self.fields[i]
                    self.warn(
                        f'Field {f.name!r}: reclassified from '
                        f'{col_type[i]} to string (quoted in '
                        f'QUOTE_STRINGS_ONLY file).'
                    )
                    self.fields[i] = FieldMetadata(
                        name=f.name,
                        fieldtype='string',
                        format=f.format,
                    )
            # Determine style from which non-string types are unquoted.
            # If dates/bools are among the unquoted, strings-only; if they're
            # quoted (or absent but numeric is unquoted), nonnumeric.
            unquoted_date_bool = [
                i for i in date_idxs + bool_idxs if states[i] is False
            ]
            quoted_date_bool = [
                i for i in date_idxs + bool_idxs if states[i] is True
            ]
            if date_idxs or bool_idxs:
                if unquoted_date_bool and not quoted_date_bool:
                    return 'QUOTE_STRINGS_ONLY'
                elif quoted_date_bool and not unquoted_date_bool:
                    return 'QUOTE_NONNUMERIC'
                # Mixed date/bool quoting: fall through to inconsistent
            else:
                # No date/bool cols to distinguish; numeric unquoted is enough
                return 'QUOTE_STRINGS_ONLY'

        if any_mixed and not any(
            s is True for s in [states[i] for i in non_string_idxs]
        ):
            return 'QUOTE_MINIMAL'

        self.warn(
            'Quoting appears inconsistent: no quoting style has been set.'
        )
        return None

    def describe_null(self):
        nulls = self.null if isinstance(self.null, list) else [self.null]
        given = self._given.get('null')
        given_set = (
            (set(given) if isinstance(given, list) else {given})
            if given is not None
            else set()
        )
        for null in nulls:
            if null in KNOWN_NULLS or null in given_set:
                self.vprint(f'Null: "{null}"', 2)
            elif self.verbosity > 0:
                self.warn(f'Unusual null: "{null}".')

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
    path,
    lines_to_use=None,
    warner=None,
    add_defaults=False,
    report_added_defaults=True,
    raise_error=False,
    delimiter=None,
    quote_char=None,
    escape=None,
    no_escape=False,
    stutter=None,
    null=None,
    encoding=None,
    date_format=None,
    datetime_format=None,
    quoting=None,
    **kw,
):
    """Infer SerialMetadata for a flat file by sampling its contents.

    Reads a sample of the file and infers delimiter, quoting style,
    encoding, field types, date formats, and null indicators.

    Args:
        path (str): Path to the flat file (CSV or similar) to sample.
        lines_to_use (int): Number of lines to sample. Uses a default
            sample size if not specified.
        warner: Optional callable for issuing warnings.
        add_defaults (bool): If True, include default values (e.g.
            standard encoding, quote char) in the inferred metadata
            even when they match the library default.
        report_added_defaults (bool): If True (the default), issue
            warnings when defaults are added. Only relevant when
            add_defaults is True.
        raise_error (bool): If True, raise an error on problems rather
            than issuing a warning.
        delimiter (str): Override the inferred field separator.
        quote_char (str): Override the inferred quote character.
        escape (str): Override the inferred escape character.
        no_escape (bool): If True, treat no escape character as given
            (do not infer one).
        stutter (bool): Override whether stutter (doubled-quote)
            escaping is used.
        null (str): Override the inferred null indicator string.
        encoding (str): Override the inferred file encoding.
        date_format (str): Override the inferred date format.
        datetime_format (str): Override the inferred datetime format.
        quoting (str): Override the inferred quoting style (e.g.
            'QUOTE_MINIMAL', 'QUOTE_ALL').
        **kw: Additional keyword arguments passed to MetadataInferrer.

    Returns:
        SerialMetadata inferred from the file.
    """
    inferrer = MetadataInferrer(
        path,
        lines_to_use,
        warner=warner,
        add_defaults=add_defaults,
        report_added_defaults=report_added_defaults,
        raise_error=raise_error,
        delimiter=delimiter,
        quote_char=quote_char,
        escape=escape,
        no_escape=no_escape,
        stutter=stutter,
        null=null,
        encoding=encoding,
        date_format=date_format,
        datetime_format=datetime_format,
        quoting=quoting,
        **kw,
    )
    return inferrer.metadata


def count(char, lines):
    return sum(sum(c == char for c in line) for line in lines)


def split_line(line, sep, counts):
    """Split line on sep with quote/escape handling.

    Returns (fields, is_quoted): fields are dequoted values, is_quoted is
    a per-field bool list. Accumulates escape/stutter evidence into counts.

    Detects quote char per-field from the opening character (either " or ').
    Handles backslash-escape and stutter (doubled quote) styles.
    Fast-path lines (no quotes, no backslashes) should be handled by the
    caller to avoid overhead.
    """
    fields = []
    is_quoted = []
    i = 0
    n = len(line)

    last_was_sep = False
    while True:
        last_was_sep = False
        if i < n and line[i] in ('"', "'"):
            # Quoted field
            q = line[i]
            i += 1
            chars = []
            while i < n:
                c = line[i]
                if c == '\\':
                    nxt = line[i + 1] if i + 1 < n else ''
                    if nxt == '\\':
                        counts.n_bs_esc += 1
                        chars.append('\\')
                        i += 2
                    elif nxt == q:
                        if q == '"':
                            counts.n_dq_esc += 1
                        else:
                            counts.n_sq_esc += 1
                        chars.append(q)
                        i += 2
                    else:
                        chars.append(c)
                        i += 1
                elif c == q:
                    if i + 1 < n and line[i + 1] == q:
                        # Stutter: doubled quote inside quoted field
                        if q == '"':
                            counts.n_dq_stutter += 1
                        else:
                            counts.n_sq_stutter += 1
                        chars.append(q)
                        i += 2
                    else:
                        # Closing quote
                        i += 1
                        break
                else:
                    chars.append(c)
                    i += 1
            fields.append(''.join(chars))
            is_quoted.append(True)
            # Skip separator after closing quote
            if i < n and line[i] == sep:
                i += 1
                last_was_sep = True
        else:
            # Unquoted field
            chars = []
            while i < n:
                c = line[i]
                if c == sep:
                    i += 1
                    last_was_sep = True
                    break
                elif c == '\\':
                    nxt = line[i + 1] if i + 1 < n else ''
                    if nxt == sep:
                        counts.n_esc_sep += 1
                        chars.append(sep)
                        i += 2
                    elif nxt == '\\':
                        counts.n_bs_esc += 1
                        chars.append('\\')
                        i += 2
                    elif nxt == '"':
                        counts.n_dq_esc += 1
                        chars.append('"')
                        i += 2
                    elif nxt == "'":
                        counts.n_sq_esc += 1
                        chars.append("'")
                        i += 2
                    else:
                        chars.append(c)
                        i += 1
                else:
                    chars.append(c)
                    i += 1
            fields.append(''.join(chars))
            is_quoted.append(False)

        if i >= n:
            if last_was_sep:
                # Trailing separator — add the implied empty last field
                fields.append('')
                is_quoted.append(False)
            break

    return fields, is_quoted


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

    def summarize(self, null, n_cand_nulls):
        # Potentially valid as this type if null is poss_null
        self.all_poss_valid = self.n_invalid == 0
        tot = max(self.n_valid + n_cand_nulls + self.n_invalid, 1)
        self.prop_valid_or_null = (self.n_valid + n_cand_nulls) / tot

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

    @property
    def counts(self):
        return (
            f'n_valid: {self.n_valid} n_invalid: {self.n_invalid} '
            f'n distinct poss_nulls: {self.n_distinct_poss_nulls}'
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
        self.n_cand_nulls = 0

    def summarize(self, null=None):
        for stats in self.stats.values():
            stats.summarize(null, self.n_cand_nulls)
        m = max(stats.n_valid for stats in self.stats.values())
        if m == 0:
            self.most_likely_type = 'string'
            # self.poss_null = None
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
            if self.stats[t].prop_valid_or_null < MIN_VALID_OR_NULL_TYPE:
                self.most_likely_type = 'string'
        self.summarized = True

    def __str__(self):
        if not getattr(self, 'summarized'):
            error('Not summarized', raise_error=self.raise_error)
        stats = '\n  '.join(str(v) for v in self.stats.values() if str(v))
        if not stats:
            stats = 'Poss string'
        return f'Field {self.fieldname}: {self.most_likely_type}\n  {stats}\n'


def analyse_values(fieldname, values, cand_nulls=None, known_nulls=None):
    if cand_nulls is None:
        cand_nulls = Counter()
    if known_nulls is None:
        known_nulls = KNOWN_NULLS
    stats = FieldTypeStats(fieldname)
    b = stats.stats['bool']
    i = stats.stats['int']
    f = stats.stats['float']
    d = stats.stats['date']
    dt = stats.stats['datetime']

    for v in values:
        poss_null = v in known_nulls

        if v.lower() in ('true', 'false'):
            b.n_valid += 1
        elif not poss_null:
            b.n_invalid += 1

        if v and v.isdigit() or (v[1:].isdigit() and v[:1] in '+-'):
            i.n_valid += 1
        elif not poss_null:
            i.n_invalid += 1

        if not poss_null:
            try:
                float(v)
                f.n_valid += 1
            except ValueError:
                f.n_invalid += 1

        if re.match(DATEISH, v) or re.match(ADATEISH, v):
            d.n_valid += 1
        elif not poss_null:
            d.n_invalid += 1

        if re.match(DTISH, v) or re.match(ADTISH, v):
            dt.n_valid += 1
        elif not poss_null:
            dt.n_invalid += 1

        if v in known_nulls:
            cand_nulls[v] += 1
            stats.n_cand_nulls += 1

    stats.summarize()
    return stats
