import os
import json
import yaml

import numpy as np
import pandas as pd
import polars as pl


from tdda.serial.metadata import (
    CONTEXT_KEY,
    URI,
    VERBOSITY,
    TDDASERIAL,
    METADATA_FLAVOURS,
    SerialMetadata,
    TDDASerialError,
)
from tdda.serial.csvw import CSVWMetadata

from tdda.serial.utils import (
    find_associated_metadata_file,
    find_metadata_type_from_path
)
from tdda.state import get_config
from tdda.utils import error, is_sequence, tdda_path_info


def load_metadata(path, md_file_type=None, table_number=None,
                  for_table_name=None,
                  preferred_serial_flavour=None, verbosity=VERBOSITY):
    """
    Attempt to load metadata from path given.

    Args:

      path    Path to the metadata file

      md_file_type    Optional metadata file type. One of
                      'tdda.serial'
                      'csvw'
                      'frictionless'

      table_number  If specified, use the nth table from a CSVW file.
                    Raise an error if not present, (indexed from zero)

      for_table_name  If specified, use choose the metadata from
                      a metadata file describing multiple tables
                      by matching the (end of the) url in the metadata
                      to this table name

      preferred_serial_flavour: If multiple metadata flavours are found
                                at the same level of a .serial file,
                                the one to choose (or priority list).

      verbosity:   2: errors and warnings to stderr
                   1: warnings to stderr
                   0: don't show errors or warnings
    """
    stem, ext = os.path.splitext(path)
    lcstem, ext = stem.lower(), ext.lower()
    with open(path) as f:
        text = f.read().strip()
    if ext == '.serial':  # tdda.serial file
        md = json.loads(text)
        if not isinstance(md, dict):
            error(f'{path} does not appear to be a tdda.serial file.')
        kw = md.get('tdda.serial') or {}
        libs = {}
        for flavour in METADATA_FLAVOURS:
            spec = md.get(flavour)
            if spec:
                libs[flavour] = spec
        md = SerialMetadata(libs=libs, source='tdda.serial', **kw)
    elif ext == '.json' or text.startswith('{'):
        kind, _ = find_metadata_type_from_path(path)
        structured = json.loads(text)
        kind, md = find_metadata_kind(structured)
        if kind == TDDASERIAL.key:
            md = SerialMetadata(**md)
        elif kind == 'csvw':
            md = CSVWMetadata(path, table_number=table_number,
                              for_table_name=for_table_name,
                              verbosity=verbosity)
        elif kind:
            md = SerialMetadata(libs={kind: md})
        else:
            kind, _ = find_metadata_type_from_path(path)
            if not kind:
                error(f'Unrecognized metadata content in {path}')
            if kind == 'csvw':
                md = CSVWMetadata(path, table_number=table_number,
                                  for_table_name=for_table_name,
                                  verbosity=verbosity)

    elif ext == '.yaml':
        with open(path) as f:
            md = yaml.load(f, yaml.SafeLoader)
            kind = 'frictionless'
    else:
        error(f'Unexpected file extension {ext} for metadata '
              f'file.\nExpected .serial, .json, or .yaml.')
    if md_file_type and kind != md_file_type:
        error(f'Expected {md_file_type} file; found {kind} file.')
    return md


def _get_metadata(rw, path, md_path, md_file_type=None, find_md=False,
                  table_number=None, use_table_name=None,
                  preferred=TDDASERIAL.key,
                  verbosity=VERBOSITY):
    """
    Internal helper function for csv read and write functions.
    Users should normally use get_metadata_for_reader or
    get_metadata_for writer.

    Finds the metadata from the path, if available, or the path
    from the metadata, adhering to the preferences specified.
    Then loads the metadata, if found.

    Returns a tuple consisting of the metadata, the data path and the metadata
    path. If one of the input paths was None, it will now be updated.
    """
    assert rw in ('r', 'w')
    is_for_reader = rw == 'r'
    md = None
    for_table_name = None
    if use_table_name:
        assert path is not None
        for_table_name = os.path.basename(path)
    if path is None:
        if md_path is None:
            error('Must provide path or md_path')
        else:
            md = load_metadata(md_path, md_file_type=md_file_type,
                               table_number=table_number,
                               for_table_name=for_table_name,
                               preferred_serial_flavour=preferred)
            path = md._fullpath
            if path is None:
                error('No data specified.')

    if md_path is None:
        if is_for_reader:
            pi = tdda_path_info(path)
            path, md_path, find_md = pi.path, pi.md_path, find_md or pi.find_md
            if md_path is None and find_md:
                md_path = find_associated_metadata_file(path)
        else:
            s_config = get_config().serial
            md_path = s_config._md_inpath(path)
    if md is None and md_path is not None:
        md = load_metadata(md_path, md_file_type=md_file_type,
                           table_number=table_number,
                           for_table_name=for_table_name, verbosity=verbosity)
    return md, path, md_path


def get_metadata_for_reader(path, md_path, md_file_type=None, find_md=False,
                            table_number=None, use_table_name=None,
                            preferred=TDDASERIAL.key,
                            verbosity=VERBOSITY):
    return _get_metadata(rw='r', path=path, md_path=md_path,
                         md_file_type=md_file_type, find_md=find_md,
                         table_number=table_number,
                         use_table_name=use_table_name,
                         preferred=preferred, verbosity=verbosity)


def get_metadata_for_writer(path, md_path, md_file_type=None, find_md=False,
                            table_number=None, use_table_name=None,
                            preferred=TDDASERIAL.key,
                            verbosity=VERBOSITY):
    return _get_metadata(rw='w', path=path, md_path=md_path,
                         md_file_type=md_file_type, find_md=find_md,
                         preferred=preferred, verbosity=verbosity)


def find_metadata_kind(mds, preferred=None):
    """
    Breadth-first search of dict or list of dicts
    for a recognized blob of metadata.

    Returns the kind and subportion representing
    the metadata for the first found, or, if there are ties
    at the same leve, the preferred tdda.serial metadata flavour,
    if specified. The preferred metadata flavour can be
    a single flavour or a list. If it is a list, the preferences
    run from higherest to lowest

    If no metadata is found, returns None, None
    """
    preferred = preferred or []
    if not is_sequence(preferred):
        preferred = [preferred]
    kind = None
    dicts = []
    if not mds:
        return None, None
    if not isinstance(mds, list):
        mds = [mds]
    for md in mds:
        for preferred in preferred:
            if preferred in md:
                kind = preferred
                return preferred, md[preferred]
        for k in METADATA_FLAVOURS:
            if k in md:
                return k, md[k]
            if CONTEXT_KEY in md:
                context = md.get(CONTEXT_KEY)
                if context == URI.CSVW:
                    kind = 'csvw'
                return kind, md
        dicts.extend([v for v in md.values() if isinstance(v, dict)])
    return find_metadata_kind(dicts, preferred)
