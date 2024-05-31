import os
import re

METADATA_STYLE_MAP = {
    r'^(.*)-(metadata)(\.json)$': 'csvw',
    r'^(.*)-(csvmetadata)(\.json)$': 'csvmetadata',
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
    for csvw, csvmetadata, frictionless. If so, return the metadata type
      - 'csvw',
      - 'csvmetadata'
      - 'fictionless'
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

    Types of metadata file supported are csvw, csvmetadata, and frictionless.

    If so, returns the metadata path.

    Returns None if no associated metadata is found.
    """
    base = os.path.expanduser(path)
    pathstem = os.path.splitext(base)[0]
    for (suffixes, exts) in METADATA_STYLES:
        for suffix in suffixes:
            for ext in exts:
                mdpath = pathstem + suffix + ext
                if os.path.exists(mdpath):
                    return mdpath
    return None
