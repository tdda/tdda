import datetime
import itertools
import json
import math
import os
import re
import regex
import sys
import tomli_w
import types
import unicodedata
import urllib.parse
import yaml

from fnmatch import fnmatch


# jythonc needs explicit import of utf-8 and iso-8859-1/latin1 encoding packages
import encodings.aliases  # type:ignore
import encodings.utf_8
import encodings.ascii  # type:ignore
import encodings.latin_1  # type:ignore
import encodings.iso8859_1  # type:ignore


from collections import namedtuple

import numpy as np
import pandas as pd

import rich

rprint = rich.print
rich.reconfigure(highlight=False, soft_wrap=True)

from rich.console import Console

stdout_console = Console(highlight=False, soft_wrap=True)
stderr_console = Console(stderr=True, highlight=False, soft_wrap=True)

from tdda.state import get_config
from tdda.xmlgen import xml_element

TDDADIR = os.path.dirname(__file__)  # base tdda directory for package
CONSTRAINTSDIR = os.path.join(TDDADIR, 'constraints')
PDCONSTRAINTSDIR = os.path.join(CONSTRAINTSDIR, 'pd')
DBCONSTRAINTSDIR = os.path.join(CONSTRAINTSDIR, 'db')
CONSTRAINTSTESTDATADIR = os.path.join(CONSTRAINTSDIR, 'testdata')
TESTREPORTSDIR = os.path.join(CONSTRAINTSTESTDATADIR, 'reports')
TEMPLATESDIR = os.path.join(TDDADIR, 'templates')
REFTESTDIR = os.path.join(TDDADIR, 'referencetest')

DEFAULT_INPUT_ENCODING = 'UTF-8'

OK = 'ok'
BAD = 'bad'
NAN = float('nan')

TDDA_NF_MAP = None  # build lazily

ALT_NULL_REP = '∅'
ALT_OTHER_REP = '★'
U_ALT_NULL_REP = '∅'
ENDASH = '–'  # chr(0x2013)
MINUS_SIGN = '−'  # chr(0x2212)


TDDAPathInfo = namedtuple(
    'TDDAPathInfo', 'path stem ext md_path find_md combined'
)


class TDDAError(Exception):
    pass


class PassFailStats:
    def __init__(self, passes, failures, items='records'):
        self.items = items
        self.n_passes = passes
        self.n_failures = failures
        denom = max(1, passes + failures)
        self.pass_rate = passes / denom
        self.failure_rate = failures / denom

    def to_dict(self, pc=True, total_values=False):
        d = {
            'n_passes': self.n_passes,
            'n_failures': self.n_failures,
        }
        if total_values:
            d[f'n_{self.items}'] = (self.n_passes + self.n_failures,)

        if pc:
            d.update(
                {
                    'pass_rate': to_pc(self.pass_rate),
                    'failure_rate': to_pc(self.failure_rate),
                }
            )
        return d


def nvl(v, w):
    """Return w if v is None, otherwise v."""
    return w if v is None else v


def swap_ext(path, new_ext):
    """Replace the extension of path with new_ext.

    Args:
        path (str): File path whose extension to replace.
        new_ext (str): New extension, with or without a leading dot.

    Returns:
        Path with the new extension.
    """
    base, ext = os.path.splitext(path)
    dot = '' if new_ext == '' or new_ext.startswith('.') else '.'
    return base + dot + new_ext


def swap_ext_q(path, new_ext):
    """Replace the extension of path with new_ext, reporting whether it changed.

    Args:
        path (str): File path whose extension to replace.
        new_ext (str): New extension, with or without a leading dot.

    Returns:
        Tuple of (new_path, changed) where changed is True iff the
        extension differed from the original.
    """
    outpath = swap_ext(path, new_ext)
    _, ext = os.path.splitext(path)
    _, new_ext = os.path.splitext(outpath)
    return outpath, new_ext != ext


def handle_tilde(path):
    """Expand a leading tilde in path to the user's home directory.

    Does nothing unless path is a string starting with '~'.

    Args:
        path: Path to expand. Non-strings are returned unchanged.

    Returns:
        Expanded path string, or the original value if no expansion
        was needed.
    """
    if type(path) is str and path.startswith('~'):
        return os.path.expanduser(path)
    else:
        return path


def dict_to_json(d, path=None):
    """Serialize d to formatted JSON, writing to path or returning as a string.

    Args:
        d (dict): Dictionary to serialize.
        path (str): If given, write JSON to this file; otherwise return it.

    Returns:
        Formatted JSON string, or None if path was given.
    """
    json_text = strip_lines(json.dumps(d, indent=4, ensure_ascii=False)) + '\n'
    if path:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(json_text)
    else:
        return json_text


def dict_to_yaml(d, path=None):
    """Serialize d to YAML, writing to path or returning as a string.

    Args:
        d (dict): Dictionary to serialize.
        path (str): If given, write YAML to this file; otherwise return it.

    Returns:
        YAML string, or None if path was given.
    """
    if path:
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(d, f)
    else:
        return yaml.dump(d)


def dict_to_toml(d, path=None):
    """Serialize d to TOML, writing to path or returning as a string.

    Args:
        d (dict): Dictionary to serialize.
        path (str): If given, write TOML to this file; otherwise return it.

    Returns:
        TOML string, or None if path was given.
    """
    if path:
        with open(path, 'wb') as f:
            tomli_w.dump(d, f)
    else:
        return tomli_w.dumps(d)


def json_sanitize(v):
    """Recursively convert v to a JSON-serializable value.

    Converts NaN/NaT/<NA> to None, datetimes to ISO strings (dropping
    the time part when it is midnight), objects with __dict__ to dicts,
    and leaves primitives unchanged.

    Args:
        v: Value to sanitize.

    Returns:
        JSON-serializable equivalent of v.
    """
    if repr(v) in ('nan', 'NaT', '<NA>'):
        return None
    elif v is None or type(v) in (str, int, float, bool):
        return v
    elif type(v) in (list, tuple):
        return [json_sanitize(u) for u in v]
    elif isinstance(v, dict):
        return {str(k): json_sanitize(u) for k, u in v.items()}
    elif hasattr(v, '__dict__') and v.__dict__:
        return json_sanitize(v.__dict__)
    else:
        s = str(v)
        return s[:-9] if s.endswith('00:00:00') else s  # slightly dodgy


def dump_as_json(d):
    return json.dumps(json_sanitize(d), indent=4, ensure_ascii=False)


def remove_falsy_values(d):
    return {k: v for k, v in d.items() if v}


def strip_lines(s):
    """Strip trailing whitespace from each line in s.

    Splits on newlines, strips trailing whitespace from each line, and
    rejoins. Preserves a trailing newline if the original string had one.

    Args:
        s (str): String to process.

    Returns:
        String with trailing whitespace removed from each line.
    """
    end = '\n' if s.endswith('\n') else ''
    return '\n'.join([line.rstrip() for line in s.splitlines()]) + end


def indicator_suffix(detect_passes=True):
    return OK if detect_passes else BAD


def indicator_field_name(field, constraint, name_map=None, detect_passes=True):
    suffix = indicator_suffix(detect_passes)
    if name_map:
        return f'{field}_{name_map[constraint]}_{suffix}'
    else:
        return f'{field}_{constraint}_{suffix}'


def pass_fail_stats(passes, failures, items='cases'):
    return PassFailStats(passes, failures, items=items)


def to_pc(v, mindp=2):
    pc = 100 * v
    delta = 5 * pow(10, -mindp - 1)
    if pc in (0, 100) or ((100 - pc > delta) and pc > delta):
        return f'{v * 100:.2f}%'  # won't be 100.00% or 0.00% if not exact

    threshold = 100 - pc if (pc > delta) else pc
    dps = -math.log10(threshold)
    lo_dps = int(dps)
    hi_dps = lo_dps + 1
    lo_fmt = '%%.%df' % lo_dps
    small = lo_fmt % pc
    i, f = small.split('.')
    if i == 100 or f == '0' * len(f):
        hi_fmt = '%%.%df' % hi_dps
        return f'{hi_fmt % pc}%'
    else:
        return f'{small}%'


def n_glyphs(s):
    """Return the number of user-perceived glyphs (grapheme clusters) in s."""
    return len(regex.findall(r'\X', s))


def tddadir(*path):
    """Return the full path to a location inside the base tdda directory.

    Args:
        *path: Path components to join after the tdda package root.

    Returns:
        Absolute path within the tdda package directory.
    """
    return os.path.join(TDDADIR, *path)


def constraints_testdata_path(path):
    """Return the full path to a file in the constraints testdata directory.

    Args:
        path (str): Relative path within the testdata directory.

    Returns:
        Absolute path to the file.
    """
    return os.path.join(TDDADIR, 'constraints', 'testdata', path)


def richbad(s, colour=True, cond=True):
    if colour and cond:
        return '[red]%s[/red]' % s
    else:
        return str(s)


def richgood(s, colour=True, cond=True):
    if colour and cond:
        return '[green]%s[/green]' % s
    else:
        return str(s)


def richgoodbad(s, colour=True, cond=True):
    if colour:
        c = 'green' if cond else 'red'
        return f'[{c}]{s}[/{c}]'
    else:
        return str(s)


def write_or_return(content, dump, stringify, path=None, binary=False):
    """Write content to path, or return it as a string.

    Args:
        content: Content to write or return.
        dump: Callable used to write content to a file object.
        stringify: Callable used to convert content to a string.
        path (str): If given, write to this path and return None.
        binary (bool): If True, open path in binary mode.

    Returns:
        String representation of content, or None if path was given.
    """
    if path:
        mode = 'wb' if binary else 'w'
        enc = None if binary else 'utf-8'
        with open(path, mode, encoding=enc) as f:
            dump(content, f)
        return None
    else:
        return stringify(content)


def tdda_css():
    with open(os.path.join(TEMPLATESDIR, 'tdda.css'), encoding='utf-8') as f:
        return f.read()


def constraint_val(v, kind=None):
    if type(v) is list:
        return '\n'.join(constraint_val(x) for x in v)
    elif type(v) is int:
        return str(v)
    elif type(v) is float:
        return str(v)
    elif type(v) is str:
        return v if kind in ('type', 'sign') else json.dumps(v)
    elif type(v) is bool:
        if kind == 'no_duplicates':
            return 'no' if v else ''
        return str(v).lower()
    elif type(v) is datetime.datetime:
        s = v.isoformat(timespec='seconds')
        return s[:10] if s.endswith('T00:00:00') else s
    elif type(v) is datetime.date:
        return v.isoformat()
    else:
        return repr(v)


def DQuote(string, escape=True):
    parts = string.split('"')
    if escape:
        parts = [p.replace('\\', r'\\').replace('\n', r'\n') for p in parts]
    quoted = ('\\"').join(parts)
    return '"%s"' % quoted


def squote(string, escape=True):
    parts = string.split("'")
    if escape:
        parts = [p.replace('\\', r'\\').replace('\n', r'\n') for p in parts]
    quoted = ("\\'").join(parts)
    return "'%s'" % quoted


def is_sequence(L):
    """Return True if L is a list, tuple, or other indexable/iterable non-string."""
    return (
        hasattr(L, '__getitem__') or hasattr(L, '__iter__')
    ) and not hasattr(L, 'strip')


def is_parquet(path):
    return os.splitext.path(path)[1] == '.parquet'


class Dummy(object):
    """A simple object whose attributes are set from keyword arguments.

    Useful as a lightweight stand-in wherever a plain object with
    named attributes is needed.
    """

    def __init__(self, **kwargs):
        for k in kwargs:
            self.__dict__[k] = kwargs[k]

    def to_dict(self):
        return self.__dict__


def cprint(*args, colour=None, recolour=None, config=None, **kw):
    if colour is None:
        config = get_config(config)
        colour = config.get('colour')
    if colour:
        if recolour:
            rprint(*(f'[{recolour}]{a}[/{recolour}]' for a in args), **kw)
        else:
            rprint(*(str(a) for a in args), **kw)
    else:
        print(*args, **kw)


def print_stderr(*args, **kw):
    cprint(*args, recolour='red', file=sys.stderr)


def tdda_nf_map():
    lu = unicodedata.lookup
    strmap = {
        '\u2013': '-',  # EN DASH
        '\u2014': '-',  # EM DASH
        '\u2212': '-',  # MINUS SIGN
        '\u2018': "'",  # LEFT SINGLE QUOTATION MARK
        '\u2019': "'",  # RIGHT SINGLE QUOTATION MARK
        '\u02bc': "'",  # MODIFIER LETTER APOSTROPHE
        '\u0060': "'",  # GRAVE ACCENT
        # '\uFF02',  # FULLWIDTH QUOTATION MARK  # Handled by NFKC/D
        '\u201c': '"',  # LEFT DOUBLE QUOTATION MARK
        '\u201d': '"',  # RIGHT DOUBLE QUOTATION MARK
        # Handled by NFKC/D
        # '\u00A0',  # NO-BREAK SPACE
        # '\u2002',  # EN SPACE
        # '\u2003',  # EM SPACE
        # '\u2007',  # FIGURE SPACE
        # '\u2008',  # PUNCTUATION SPACE
        '\u0009': ' ',  # TAB  # unicodedata.name does not recognize!
        # Handled by NFKC/D:
        # '\u00B9',  # SUPERSCRIPT ONE
        # '\u2081',  # SUBSCRIPT ONE
        # '\u2460',  # CIRCLED DIGIT ONE
        # '\U0001D7D9',  # MATHEMATICAL DOUBLE-STRUCK DIGIT ONE
        '\u2474': '(1)',  # PARENTHESIZED DIGIT ONE
        '\u2488': '1.',  # DIGIT ONE FULL STOP
        '\u0391': 'A',  # GREEK CAPITAL LETTER ALPHA
        '\u00c5': 'A',  # LATIN CAPITAL LETTER A WITH RING ABOVE
        # '\u212B',  # ANGSTROM SIGN  # Handled by NFKC/D
        # Handled by NFKC/D:
        #'\u2026',  # HORIZONTAL ELLIPSIS
        #'\uFE19',  # PRESENTATION FORM FOR VERTICAL HORIZONTAL ELLIPSIS
        '\u22ee': '...',  # VERTICAL ELLIPSIS
        '\u22ef': '...',  # MIDLINE HORIZONTAL ELLIPSIS
        '\u22f1': '...',  # DOWN RIGHT DIAGONAL ELLIPSIS
        '\u04d5': 'ae',  # 'æ'
        '\u00e6': 'ae',  # 'æ'
        '\u04d4': 'AE',  # 'Ӕ'
        '\u00c6': 'AE',  # 'Æ'
        'ǽ': 'ae',
        'đ': 'd',
        'ð': 'd',
        'ƒ': 'f',
        'ħ': 'h',
        'ı': 'i',
        'ł': 'l',
        'ø': 'o',
        'ǿ': 'o',
        'Ø': 'O',
        'œ': 'oe',
        'Œ': 'OE',
        'ß': 'ss',
        'ŧ': 't',
    }

    return str.maketrans(strmap)


def normal_form_tk(
    s, remove_accents=True, strip=False, standardize_space=False, nfkd=False
):
    """Map s to TDDA Normal Form TK (NFTK) with options for KC or KD
    and also some whitespace normalization options.

    NFTK applies Unicode Compatibility Normalization (NFKC or NFKD)
    plus additional mappings for commonly confused characters, with
    optional accent removal and space normalization.

    Extra mappings beyond NFKC/NFKD include:
        - Dashes and minus signs → ASCII hyphen-minus
        - Curly quotes and apostrophes → ASCII ' and "
        - Tab and a few other whitespace forms → space
        - Some combined characters like œ → oe

    Args:
        s (str): String to normalize.
        remove_accents (bool): Strip combining diacritical marks
            (default True).
        strip (bool): Strip leading and trailing whitespace
            (default False).
        standardize_space (bool): Collapse runs of spaces to a single
            space (default False).
        nfkd (bool): Use NFKD base form instead of the default NFKC
            (default False).

    Returns:
        Normalized string.

    Note:
        Unless the whitespace handling is required, the short form
        ``nftk()`` should normally be used (or ``nftkd()`` if decomposed
        form is required in edge cases).
    """
    global TDDA_NF_MAP
    if TDDA_NF_MAP is None:
        TDDA_NF_MAP = tdda_nf_map()

    form = 'NFKD' if nfkd else 'NFKC'
    normalized = unicodedata.normalize('NFKD', s)
    if remove_accents:
        normalized = ''.join(
            c for c in normalized if not unicodedata.combining(c)
        )
    normalized = normalized.translate(TDDA_NF_MAP)
    if strip:
        normalized = normalized.strip()
    if standardize_space:
        while '  ' in normalized:
            normalized = normalized.replace('  ', ' ')
    return unicodedata.normalize(form, normalized)


def nftk(s):
    """Normalize s to TDDA Normal Form TKC (NFKC base, accents stripped).

    Equivalent to nftkc(s). Applies Unicode Compatibility Normalization
    KC, maps various quotes, dashes, and similar characters to ASCII
    equivalents, and strips combining diacritical marks.

    The difference between TKC and TKD is canonical composition vs.
    decomposition after compatibility normalization. They differ mainly
    for characters with combining marks, such as some Hangul syllable
    blocks (e.g. 가).

    Args:
        s (str): String to normalize.

    Returns:
        Normalized string in TK form.
    """
    return normal_form_tk(s)

nftkc = nftk


def nftkd(s):
    """Normalize s to TDDA Normal Form TKD (NFKD base, accents stripped).

    Applies Unicode Compatibility Normalization KD, maps various quotes,
    dashes, and similar characters to ASCII equivalents, and strips
    combining diacritical marks.

    The difference between TKC and TKD is canonical composition vs.
    decomposition after compatibility normalization. They differ mainly
    for characters with combining marks, such as some Hangul syllable
    blocks (e.g. 가).

    Args:
        s (str): String to normalize.

    Returns:
        Normalized string in TKD form.
    """
    return normal_form_tk(s, nfkd=True)




def rednz(v):
    if v == 0:
        return '0'
    else:
        return xml_element('span', f'{v:,}', attributes={'class': 'tdred'})


def redblack(v, red):
    if red:
        return xml_element('span', v, attributes={'class': 'tdred'})
    else:
        return v


def coloured_tick_cross(ok):
    colour = 'tdgreen' if ok else 'tdred'
    mark = '✓' if ok else '✗'
    return xml_element('span', mark, attributes={'class': colour})


def richprint(*args, **kw):
    stdout_console.print(*args, **kw)


def warn(*args, buf=None, verbose=True, **kw):
    if buf:
        buf.append(args)
    elif verbose:
        stderr_console.print(*args, style='yellow', **kw)


def error(*args, raise_error=False, exit=True, **kw):
    if raise_error:
        raise TDDAError('\n'.join(args) if args else 'error')
    stderr_console.print(*args, style='red', **kw)
    if exit:
        sys.exit(1)


def debug(*args, buf=None, verbose=True, **kw):
    if buf:
        buf.append(args)
    elif verbose:
        stderr_console.print(*args, style='blue', **kw)


def listify(v, sort=False):
    """Convert v to a list if it is not already one.

    Tuples are converted to lists; None becomes []; scalars become [v].

    Args:
        v: Value to listify.
        sort (bool): If True, return the list sorted (default False).

    Returns:
        v as a list.
    """
    L = (
        v
        if isinstance(v, list)
        else list(v)
        if isinstance(v, tuple)
        else []
        if v is None
        else [v]
    )
    return sorted(L) if sort else L


def delistify(L):
    """Return the sole element of L if it is a singleton sequence, else L."""
    return L[0] if (is_sequence(L) and len(L) == 1) else L


def tdda_path_info(inpath):
    inpath = handle_tilde(inpath)
    if ':' in inpath and not os.path.exists(inpath):
        if inpath.endswith(':'):
            path = inpath[:-1]
            stem, ext = os.path.splitext(path)
            return TDDAPathInfo(path, stem, ext, None, True, inpath)
        parts = inpath.split(':')
        if len(parts) == 2:
            path, md_path = parts
            stem, ext = os.path.splitext(path)
            return TDDAPathInfo(
                path, stem, ext, handle_tilde(md_path), False, inpath
            )
        # else
        # ignore for now

    stem, ext = os.path.splitext(inpath)
    return TDDAPathInfo(inpath, stem, ext, None, False, inpath)


def globlike_match(patterns, names):
    if patterns is None or names is None:
        return []
    if isinstance(patterns, str):
        patterns = [patterns]
    return [name for name in names if any(fnmatch(name, p) for p in patterns)]


def testwarn():
    buf = []
    f = lambda *args, **kw: buf.extend(args)
    return f, buf


testwarn.__test__ = False


def find_free_name(names, candidates=None):
    candidates = candidates or ['f']
    for c in candidates:
        if c not in names:
            return c
    n = 1
    c = f'{candidates[0]}_{n}'
    while c in names:
        n += 1
    return c


def is_windows():
    return sys.platform.startswith('win')


def dict_to_tex_macros(d, outpath=None, verbose=False):
    defs = ''.join(
        '\\def\\%s{%s}\n' % (tex_name(k), tex_encode(str(v)))
        for k, v in d.items()
    )
    if outpath:
        with open(outpath, 'w', encoding='utf-8') as f:
            f.write(defs)
        if verbose:
            print(f'Written {outpath}.')
    return defs


def tex_encode(s, number=False, para=False):
    if not type(s) is str:
        print(
            'tex_encode: input type (%s); expected type (%s)' % (type(s), str)
        )
        print(s)
        raise Exception('Wrong type sent to tex_encode')
    if s is None:
        return r'\hbox{$\varnothing$}'
    s = s.replace('\\', r'\verb+\+')
    s = s.replace('&', r'\&')
    s = s.replace('{', r'\{')
    s = s.replace('}', r'\}')
    s = s.replace('^', r'\^')
    s = s.replace('_', r'\_')
    s = s.replace('$', r'\$')
    s = s.replace('£', r'\pounds{}')
    s = s.replace('#', r'\#')
    s = s.replace('<=', r'$\le$')
    s = s.replace('>=', r'$\ge$')
    s = s.replace('≤', r'$\le$')
    s = s.replace('≥', r'$\ge$')
    s = s.replace(ALT_NULL_REP, r'\hbox{$\varnothing$}')
    s = s.replace(ALT_OTHER_REP, r'\hbox{$\bigstar$}')

    s = s.replace('<', '$<$')
    s = s.replace('>', '$>$')
    s = s.replace(r'$\le$ x $<$', r'$\le x <$')
    s = s.replace('·', r'$\cdot$')
    s = s.replace('%', r'\%')
    s = s.replace('~', r'$\sim$')
    s = s.replace('©', r'\copyright{}')
    s = s.replace(ENDASH, '--')
    s = s.replace(MINUS_SIGN, '--')
    s = s.replace('—', '---')
    s = s.replace('⎵', r'\textvisiblespace{}')

    if number and s.startswith('-'):
        s = '$%s$' % s
    elif s.startswith('-'):
        plain = (
            s.replace(',', '')
            .replace(' ', '')
            .replace('%', '')
            .replace('--', '-')
            .replace(r'\$', '')
            .replace(r'\pounds{}', '')
        )
        try:
            x = float(plain)
            s = '$%s$' % s
        except ValueError:
            pass
    return s + ('\n\n' if para else '')


DIGITS = {
    '1': 'One',
    '2': 'Two',
    '3': 'Three',
    '4': 'Four',
    '5': 'Five',
    '6': 'Six',
    '7': 'Seven',
    '8': 'Eight',
    '9': 'Nine',
    '0': 'Zero',
}

TENS = {
    '10': 'Ten',
    '20': 'Twenty',
    '30': 'Thirty',
    '40': 'Forty',
    '50': 'Fifty',
    '60': 'Sixty',
    '70': 'Seventy',
    '80': 'Eighty',
    '90': 'Ninety',
}


def tex_name(name):
    out = camelName(name)
    return remap(powers_of_ten(out), DIGITS)


def remap(s, d):
    return ''.join(d.get(c, c) for c in s)


def powers_of_ten(s):
    r = (
        s.replace('000000', 'mn')
        .replace('00000', 'xxk')
        .replace('0000', 'xk')
        .replace('000', 'k')
        .replace('00', 'Hundred')
    )
    for tens, name in TENS.items():
        r = r.replace(tens, name)
    return r


def camelName(name):
    out = []
    cap = False
    for c in name:
        if cap:
            c = c.upper()
        cap = False
        if c in '-_':
            cap = True
        else:
            out.append(c)
    return ''.join(out) if out else 'v'


def split_string_list(s):
    """Split string on commas, spaces, allowing dups"""
    L = [w.strip() for w in s.replace(',', ' ').split(' ')]
    return [w for w in L if w]


def plural(n, s, pl=None, inc_n=True, full_plural=None):
    """Return a count-and-noun string such as '3 fields' or '1 field'.

    Args:
        n (int): Count.
        s (str): Singular noun stem.
        pl (str): Suffix to append for plural; defaults to 's'.
        inc_n (bool): If True (default), prefix the noun with n.
        full_plural (str): Full plural word, overriding s + pl.

    Returns:
        Formatted string such as '1 field' or '3 fields', or just the
        noun (singular or plural) when inc_n is False.
    """
    if full_plural is not None:
        p = full_plural
    elif pl is None:
        p = s + 's'
    else:
        p = '%s%s' % (s, pl)

    if inc_n:
        return '%s %s' % (n, s if n == 1 else p)
    else:
        return s if n == 1 else p


def string_list(list_, conjunction='and', oxford=False):
    """Join a list of items into a natural-language string.

    Args:
        list_ (list): Items to join.
        conjunction (str): Word before the last item (default 'and').
        oxford (bool): If True, add a comma before the conjunction
            when there are more than two items (default False).

    Returns:
        Items joined as e.g. 'a, b and c', or 'none' for an empty list.
    """
    list_ = list(list_)
    if len(list_) == 0:
        return 'none'
    if len(list_) == 1:
        return str(list_[0])
    oxford_comma = ',' if (oxford and len(list_) > 2) else ''
    return ', '.join((str(L) for L in list_[:-1])) + '%s %s %s' % (
        oxford_comma,
        conjunction,
        list_[-1],
    )


def oxford_list(list_, conjunction='and'):
    return string_list(list_, conjunction, oxford=True)


def valid_level(level):
    if level == 'permissive':
        return 'loose'
    elif level is None:
        return 'strict'
    if not (level is None or level in ('strict', 'medium', 'loose')):
        raise ValueError(
            f'Type match level must be one of strict, medium, '
            f'or loose(/permissive), not {level}'
        )
    return level


def unicode_definite(s):
    return s.decode('UTF-8') if type(s) == bytes else s


def utf8_definite(s):
    return s if type(s) == bytes else s.encode('UTF-8')


def handle_rfc9839_forbiddens(text, delete=True):
    """Remove or replace RFC 9839 forbidden characters from text.

    Forbidden characters are:
        - Surrogates: U+D800–U+DFFF
        - C0 controls except tab (U+09), LF (U+0A), CR (U+0D): U+00–U+1F
        - DEL and C1 controls: U+7F–U+9F
        - Noncharacters: U+FDD0–U+FDEF (32 chars) and U+xFFFE/U+xFFFF
          for all 17 Unicode planes (34 chars)

    Args:
        text (str): Text to clean.
        delete (bool): If True (default), remove forbidden characters.
            If False, replace them with U+FFFD (REPLACEMENT CHARACTER).

    Returns:
        Cleaned text with forbidden characters removed or replaced.
    """
    replacement = unicodedata.lookup('REPLACEMENT CHARACTER')
    result = []
    for char in text:
        code_point = ord(char)

        # Check surrogates (U+D800-U+DFFF)
        if 0xD800 <= code_point <= 0xDFFF:
            if not delete:
               result.append(replacement)
            continue

        # Check C0 controls (except tab/LF/CR)
        # U+00-U+1F except 09 (tab), 0A (LF), 0D (CR)
        if 0x00 <= code_point <= 0x1F and code_point not in (
            0x09,
            0x0A,
            0x0D,
        ):
            if not delete:
               result.append(replacement)
            continue

        # Check DEL and C1 controls (U+7F-U+9F)
        if 0x7F <= code_point <= 0x9F:
            if not delete:
               result.append(replacement)
            continue

        # Check noncharacters
        # U+FDD0-U+FDEF (32 noncharacters)
        if 0xFDD0 <= code_point <= 0xFDEF:
            if not delete:
               result.append(replacement)
            continue

        # U+xFFFE and U+xFFFF for all 17 planes
        if (code_point & 0xFFFF) in (0xFFFE, 0xFFFF):
            if not delete:
               result.append(replacement)
            continue

        # Character is allowed
        result.append(char)

    return ''.join(result)



def check_unicode_assignables(text, field_name):
    """Return warnings for RFC 9839 forbidden characters found in text.

    Checks for but does not reject characters outside the Unicode
    Assignables subset: surrogates, C0 controls (except tab/LF/CR),
    DEL and C1 controls, and noncharacters.

    Args:
        text (str): Text to check.
        field_name (str): Label used in warning messages.

    Returns:
        List of warning strings, one per category of problematic
        character found, or an empty list if the text is clean.
    """
    warnings = []
    problematic_chars = set()

    for char in text:
        code_point = ord(char)

        # Check surrogates (U+D800-U+DFFF)
        if 0xD800 <= code_point <= 0xDFFF:
            problematic_chars.add(
                (code_point, 'surrogate', f'U+{code_point:04X}')
            )

        # Check C0 controls (except tab/LF/CR)
        # U+00-U+1F except 09 (tab), 0A (LF), 0D (CR)
        elif 0x00 <= code_point <= 0x1F and code_point not in (
            0x09,
            0x0A,
            0x0D,
        ):
            problematic_chars.add(
                (code_point, 'C0 control', f'U+{code_point:04X}')
            )

        # Check DEL and C1 controls (U+7F-U+9F)
        elif 0x7F <= code_point <= 0x9F:
            problematic_chars.add(
                (code_point, 'DEL/C1 control', f'U+{code_point:04X}')
            )

        # Check noncharacters
        # U+FDD0-U+FDEF (32 noncharacters)
        elif 0xFDD0 <= code_point <= 0xFDEF:
            problematic_chars.add(
                (code_point, 'noncharacter', f'U+{code_point:04X}')
            )

        # U+xFFFE and U+xFFFF for all 17 planes
        elif (code_point & 0xFFFF) in (0xFFFE, 0xFFFF):
            problematic_chars.add(
                (code_point, 'noncharacter', f'U+{code_point:04X}')
            )

    # Generate warnings
    if problematic_chars:
        # Group by type for clearer messages
        by_type = {}
        for code_point, char_type, code_str in sorted(problematic_chars):
            if char_type not in by_type:
                by_type[char_type] = []
            by_type[char_type].append(code_str)

        for char_type, codes in sorted(by_type.items()):
            if len(codes) <= 5:
                code_list = ', '.join(codes)
            else:
                code_list = (
                    ', '.join(codes[:5]) + f', and {len(codes) - 5} more'
                )
            warnings.append(
                f'{field_name}: Contains {char_type} characters: {code_list}'
            )

    return warnings

