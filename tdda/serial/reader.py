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
    SERIAL_METADATA_FLAVOURS,
    SerialMetadata,
    TDDASerialError,
)
from tdda.serial.csvw import CSVWMetadata, CSVW
from tdda.serial.frictionless import (
    FrictionlessMetadata,
    FRICTIONLESS_TELL_KEYS,
)

from tdda.serial.utils import (
    find_associated_metadata_file,
    find_metadata_type_from_path,
)
from tdda.state import get_config
from tdda.utils import error, is_sequence, tdda_path_info


def load_metadata(
    path,
    md_file_type=None,
    table_number=None,
    for_table_name=None,
    preferred_serial_flavour=None,
    verbosity=VERBOSITY,
):
    """Load metadata from a .serial, CSVW, or Frictionless file.

    Args:
        path (str): Path to the metadata file.
        md_file_type (str): Optional metadata file type. One of
            'tdda.serial', 'csvw', 'frictionless'.
        table_number (int): If specified, use the nth table from a
            multi-table metadata file (indexed from zero). Raises an
            error if not present.
        for_table_name (str): If specified, select the metadata from
            a multi-table metadata file by matching the end of the url
            in the metadata to this table name.
        preferred_serial_flavour (str or list): If multiple metadata
            flavours are found at the same level of a .serial file,
            the one to choose (or a priority list).
        verbosity (int): Controls warning/error output.
            2: errors and warnings to stderr.
            1: warnings to stderr only.
            0: silent.

    Returns:
        SerialMetadata (or subclass) loaded from the file.
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
        for flavour in SERIAL_METADATA_FLAVOURS:
            spec = md.get(flavour)
            if spec:
                libs[flavour] = spec
        md = SerialMetadata(libs=libs, source='tdda.serial', **kw)
    elif ext == '.json' or text.startswith('{'):
        kind, _ = find_metadata_type_from_path(path)
        structured = json.loads(text)
        if kind is None:
            kind, md = find_metadata_kind(structured)
        if kind == TDDASERIAL.key:
            md = SerialMetadata(**md)
        elif kind == 'csvw':
            md = CSVWMetadata(
                path,
                table_number=table_number,
                for_table_name=for_table_name,
                verbosity=verbosity,
            )
        elif kind == 'frictionless':
            md = FrictionlessMetadata(
                path,
                table_number=table_number,
                for_table_name=for_table_name,
                verbosity=verbosity,
            )
        elif kind:
            md = SerialMetadata(libs={kind: md})
        else:
            kind, _ = find_metadata_type_from_path(path)
            if not kind:
                if has_csvw_context(path):
                    kind = 'csvw'
                else:
                    error(f'Unrecognized metadata content in {path}')
            if kind == 'csvw':
                md = CSVWMetadata(
                    path,
                    table_number=table_number,
                    for_table_name=for_table_name,
                    verbosity=verbosity,
                )

    elif ext == '.yaml':
        md = FrictionlessMetadata(
            path,
            table_number=table_number,
            for_table_name=for_table_name,
            verbosity=verbosity,
        )
        kind = 'frictionless'
    else:
        error(
            f'Unexpected file extension {ext} for metadata '
            f'file.\nExpected .serial, .json, or .yaml.'
        )
    if md_file_type and kind != md_file_type:
        error(f'Expected {md_file_type} file; found {kind} file.')
    return md


def _get_metadata(
    rw,
    path,
    md_path=None,
    md_file_type=None,
    find_md=False,
    table_number=None,
    use_table_name=None,
    preferred=TDDASERIAL.key,
    config=None,
    verbosity=VERBOSITY,
):
    """Locate and load metadata for a CSV read or write operation.

    Internal helper; callers should use ``get_metadata_for_reader`` or
    ``get_metadata_for_writer`` instead.

    Resolves the data path from metadata (or vice versa) according to
    the specified preferences, then loads the metadata if found.

    Returns:
        tuple: ``(metadata, data_path, metadata_path)`` — any path that
        was None on entry is filled in if it could be determined.
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
            md = load_metadata(
                md_path,
                md_file_type=md_file_type,
                table_number=table_number,
                for_table_name=for_table_name,
                preferred_serial_flavour=preferred,
                verbosity=verbosity,
            )
            path = md._fullpath
            if path is None:
                error('No data specified.')

    if md_path is None:
        if is_for_reader:
            pi = tdda_path_info(path)
            path, md_path, find_md = pi.path, pi.md_path, find_md or pi.find_md
            if md_path is None and find_md:
                md_path = find_associated_metadata_file(path)
            elif path is not None:
                kind, _ = find_metadata_type_from_path(path)
                if kind:
                    md = load_metadata(
                        path,
                        md_file_type=md_file_type,
                        table_number=table_number,
                        for_table_name=for_table_name,
                        preferred_serial_flavour=preferred,
                        verbosity=verbosity,
                    )
                    actual_path = getattr(md, '_fullpath', md.path)
                    if actual_path is None:
                        error('No data specified.')
                    (
                        path,
                        md_path,
                    ) = actual_path, path

        else:
            s_config = get_config(config).serial
            md_path = s_config._md_inpath(path)

    if md is None and md_path is not None:
        md = load_metadata(
            md_path,
            md_file_type=md_file_type,
            table_number=table_number,
            for_table_name=for_table_name,
            verbosity=verbosity,
        )
    return md, path, md_path


def get_metadata_for_reader(
    path,
    md_path=None,
    md_file_type=None,
    find_md=False,
    table_number=None,
    use_table_name=None,
    preferred=TDDASERIAL.key,
    verbosity=VERBOSITY,
):
    return _get_metadata(
        rw='r',
        path=path,
        md_path=md_path,
        md_file_type=md_file_type,
        find_md=find_md,
        table_number=table_number,
        use_table_name=use_table_name,
        preferred=preferred,
        verbosity=verbosity,
    )


def get_metadata_for_writer(
    path,
    md_path=None,
    md_file_type=None,
    find_md=False,
    table_number=None,
    use_table_name=None,
    preferred=TDDASERIAL.key,
    verbosity=VERBOSITY,
):
    return _get_metadata(
        rw='w',
        path=path,
        md_path=md_path,
        md_file_type=md_file_type,
        find_md=find_md,
        preferred=preferred,
        verbosity=verbosity,
    )


def find_metadata_kind(mds, preferred=None):
    """Breadth-first search of a dict (or list of dicts) for metadata.

    Returns the kind and the sub-portion of the structure that
    represents the metadata. When multiple flavours are found at the
    same level, the ``preferred`` flavour wins; it may be a single
    string or a priority list (highest first).

    Returns:
        tuple: ``(kind, metadata_dict)``, or ``(None, None)`` if not found.
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
        for k in SERIAL_METADATA_FLAVOURS:
            if k in md:
                return k, md[k]
        if CONTEXT_KEY in md:
            context = md.get(CONTEXT_KEY)
            if context == URI.CSVW:
                kind = 'csvw'
            return kind, md
        for key in FRICTIONLESS_TELL_KEYS:
            if key in md:
                return key, md[key]
        dicts.extend([v for v in md.values() if isinstance(v, dict)])
    return find_metadata_kind(dicts, preferred)


def set_delimiter_from_path(kw, path, sep_key):
    """Set the delimiter in ``kw`` from the file extension if not already set.

    Sets ``kw[sep_key]`` to ``,``, ``\\t``, or ``|`` for ``.csv``,
    ``.tsv``, or ``.psv`` files respectively, unless a delimiter is
    already present in ``kw``.
    """
    kw = kw or {}
    if not kw.get('delimiter') and not kw.get(sep_key):
        ext = os.path.splitext(path)[1]
        if ext == '.csv':
            kw[sep_key] = ','
        elif ext == '.tsv':
            kw[sep_key] = '\t'
        elif ext == '.psv':
            kw[sep_key] = '|'
    return kw


def has_csvw_context(json_path):
    """Return True if the JSON file contains a CSVW ``@context`` signature."""
    with open(json_path) as f:
        d = json.load(f)
    if isinstance(d, dict):
        context = d.get('@context')
        if context and isinstance(context, list):
            if context[0] == CSVW.CONTEXT:
                return True
    return None
