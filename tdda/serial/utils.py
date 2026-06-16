import os
import re

from collections import namedtuple

from tdda.serial.constants import TDDASERIAL
from tdda.state import get_config
from tdda.utils import error, swap_ext

BACKENDS = ['numpy_nullable', 'pyarrow', 'original']
OG_BACKEND = 'original'

BACKEND_MAP = {
    'original': 'original',
    'numpy_nullable': 'numpy_nullable',
    'pyarrow': 'pyarrow',
    'o': 'original',
    'n': 'numpy_nullable',
    'a': 'pyarrow',
}


CSVW_MD_RE = r'^(.*?)[-.]((csv[-.]?)?metadata)(\.json)$'

TDDA_SERIAL_RE = r'^(.*)(\.serial)$'
FRICTIONLESS_MD_RE = r'^(.*)[-.].*(package|resource|schema).*(\.json|\.yaml)'
METADATA_STYLE_MAP = {
    TDDA_SERIAL_RE: 'tdda.serial',
    CSVW_MD_RE: 'csvw',
    FRICTIONLESS_MD_RE: 'frictionless',
}

METADATA_STYLES = (
    (
        (
            '-metadata',
            '-csvmetadata',
            '-csv-metadata',
            '.csvmetadata',
            '.csv-metadata',
        ),
        ('.json',),
    ),
    (('.schema', '.resource', '.package'), ('.json', '.yaml')),
)


class PYTHON_TEMPLATES:
    PANDAS_READ = """
import pandas as pd

def read_data(inpath):
    return pd.read_csv(
        inpath,
        %s
    )

"""

    POLARS_READ = """
import polars as pl

def read_data(inpath):
    return pl.read_csv(
        inpath,
        %s
    )

"""

    POLARS_READ_POSTPROC = """
import polars as pl

def read_data(inpath):
    df = pl.read_csv(
        inpath,
        %s
    )

%s
    return df

"""

    PANDAS_WRITE = """
import pandas as pd

def write_data(df, outpath):
    df.to_csv(
        outpath,
        %s
    )

"""

    POLARS_WRITE = """
import polars as pl

def write_data(df, outpath):
    df.write_csv(
        outpath,
        %s
    )

"""

    POLARS_WRITE_WITH_CAST = """
import polars as pl

def write_data(df, outpath):
    df = df.with_columns(
%s    )
    df.write_csv(
        outpath,
        %s
    )

"""


DataFrameWithMetadata = namedtuple('DataFrameWithMetadata', 'df md')


def find_metadata_type_from_path(path):
    """
    Check whether path follows a known pattern for a metadata file path
    for csvw, tdda.serial, frictionless. If so, return the metadata type
      - 'csvw',
      - 'tdda.serial'
      - 'frictionless'
      - or 'frictionless package'.
    Returns None if the path is not recognized as some kinds of CSV metadata.
    """
    name = os.path.basename(path)
    for r, kind in METADATA_STYLE_MAP.items():
        m = re.match(r, name)
        if m:
            return kind, m.groups()
    return None, None


def find_associated_metadata_file(path, raise_error=False):
    """
    Check whether there appears to be a metadata file associated with the
    (presumed) CSV file given.

    Types of metadata file supported are csvw, tdda.serial, and frictionless.

    If so, returns the metadata path.

    Returns None if no associated metadata is found.
    """
    base = os.path.expanduser(path)
    pathstem = os.path.splitext(base)[0]

    # tdda.serial — exact match
    for name in (base, pathstem):
        md_path = name + TDDASERIAL.ext
        if os.path.exists(md_path):
            return md_path

    # tdda.serial, frictionless schema/package, and CSVW — wildcard match (@ acts as glob *)
    data_stem = os.path.basename(pathstem)
    directory = os.path.dirname(base) or '.'
    wildcard_exts = (
        TDDASERIAL.ext,
        '.schema.json', '.schema.yaml',
        '.package.json', '.package.yaml',
        '-metadata.json',
        '-csvmetadata.json',
        '-csv-metadata.json',
        '.csvmetadata.json',
        '.csv-metadata.json',
    )
    matches = []
    try:
        entries = os.listdir(directory)
    except OSError:
        entries = []
    for entry in entries:
        for wext in wildcard_exts:
            if '@' in entry and entry.endswith(wext):
                pattern_stem = entry[: -len(wext)]
                pattern = re.escape(pattern_stem).replace('@', '.*')
                if re.fullmatch(pattern, data_stem):
                    matches.append(os.path.join(directory, entry))
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        error(
            f'Ambiguous wildcard metadata for {path!r}:\n'
            + '\n'.join(f'  {m}' for m in sorted(matches)),
            raise_error=raise_error,
        )

    for suffixes, exts in METADATA_STYLES:
        for suffix in suffixes:
            for ext in exts:
                md_path = pathstem + suffix + ext
                if os.path.exists(md_path):
                    return md_path
    return None


def get_backend(backend, config):
    if backend is None:
        c = get_config(config)
        backend = c.get('pandas_backend')
    if backend not in BACKEND_MAP:
        error(
            f'Pandas backend {backend} unknown.\n'
            f'Should be one of: {" ".join(BACKENDS)}.'
        )
    return BACKEND_MAP[backend]


def choose_md_path(path, flavour=None):
    # TODO: use flavour for csvw etc.
    return swap_ext(path, '.serial')


def format_template_args(kw, flavour=None, dtypes=None):
    """Format a kwargs dict as a string for use in a code template."""

    def f(x):
        s12 = ' ' * 12
        s8 = ' ' * 8
        joint = f',\n{s12}'
        if isinstance(x, dict) and len(x) >= 1:
            prefix = ''
            if flavour == 'polars' and dtypes:
                vals = list(dtypes.values())
                if any(v in vals for v in x.values()):
                    prefix = 'pl.'
            pairs = joint.join(
                f'{repr(k)}: {prefix}{repr(v)}' for k, v in x.items()
            )
            return '{\n%s%s\n%s}' % (s12, pairs, s8)
        elif isinstance(x, list) and len(x) > 1:
            L = joint.join(f'{repr(v)}' for v in x)
            return '[\n%s%s\n%s]' % (s12, L, s8)
        else:
            return repr(x)

    return ',\n        '.join(f'{k}={f(v)}' for k, v in kw.items())


def fill_template(template, kw, flavour=None, dtypes=None):
    args = format_template_args(kw, flavour=flavour, dtypes=dtypes)
    return (template % args).lstrip()


def non_chars(lines, n):
    """
    Find n characters not in line (a string).

    Return as tuple
    """
    n_found = 0
    c = 0x80
    out = []
    while n_found < n:
        if all(chr(c) not in line for line in lines):
            out.append(chr(c))
            n_found += 1
        c += 1
    return tuple(out)


def dict_max_items(d):
    """
    Filter dictionary d, with integer values, to only those
    items with the maximum value (typically highest frequency)
    """
    if not d:
        return d
    m = max(d.values())
    return {k: v for k, v in d.items() if v == m}
