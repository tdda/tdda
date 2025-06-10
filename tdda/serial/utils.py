import os
import re

from tdda.serial.constants import TDDASERIAL

METADATA_STYLE_MAP = {
    r'^(.*)-(metadata)(\.json)$': 'csvw',
    r'^(.*)(\.serial)$': 'serial',
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
        mdpath = name + TDDASERIAL.ext
        if os.path.exists(mdpath):
            return mdpath

    for (suffixes, exts) in METADATA_STYLES:
        for suffix in suffixes:
            for ext in exts:
                mdpath = pathstem + suffix + ext
                if os.path.exists(mdpath):
                    return mdpath
    return None
