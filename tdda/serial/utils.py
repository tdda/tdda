import os
import re

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



METADATA_STYLE_MAP = {
    r'^(.*)-(metadata)(\.json)$': 'csvw',
    r'^(.*)(\.serial)$': 'tdda.serial',
    r'^(.*\.).*(package|resource|schema).*(\.json)': 'frictionless',
}

METADATA_STYLES = (
    (('-metadata',
      '-csvmetadata',
      '-csv-metadata',
      '.csvmetadata',
      '.csv-metadata',),
     ('.json',)),
    (('.schema', '.resource', '.package'), ('.json', '.yaml'))
)


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
    for r, kind in METADATA_STYLE_MAP.items():
        m = re.match(r, path)
        if m:
            return kind, m.groups()
    return None, None


def find_associated_metadata_file(path):
    """
    Check whether there appears to be a metadata file associated with the
    (presumed) CSV file given.

    Types of metadata file supported are csvw, tdda.serial, and frictionless.

    If so, returns the metadata path.

    Returns None if no associated metadata is found.
    """
    base = os.path.expanduser(path)
    pathstem = os.path.splitext(base)[0]

    # tdda.serial
    for name in (base, pathstem):
        md_path = name + TDDASERIAL.ext
        if os.path.exists(md_path):
            return md_path

    for (suffixes, exts) in METADATA_STYLES:
        for suffix in suffixes:
            for ext in exts:
                md_path = pathstem + suffix + ext
                if os.path.exists(md_path):
                    return md_path
    return None


def get_backend(backend):
    if backend is None:
        c = get_config()
        backend = c.get('pandas_backend')
    if backend not in BACKEND_MAP:
        error(f'Pandas backend {backend} unknown.\n'
              f'Should be one of: {" ".join(BACKENDS)}.')
    return BACKEND_MAP[backend]


def choose_md_path(path, flavour=None):
    # TODO: use flavour for csvw etc.
    return swap_ext(path, '.serial')
