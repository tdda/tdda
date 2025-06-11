import os
import json
import yaml

import numpy as np
import pandas as pd
import polars as pl

from collections import namedtuple

from tdda.serial.base import (
    CONTEXT_KEY,
    URI,
    SerialMetadataError,
    VERBOSITY,
    TDDASERIAL,
    METADATA_FLAVOURS,
    SerialMetadata,
)
from tdda.serial.csvw import CSVWConstants, CSVWMetadata
from tdda.serial.pandasio import to_pandas_read_csv_args
from tdda.serial.polarsio import to_polars_read_csv_args

from tdda.serial.utils import (
    find_associated_metadata_file,
    find_metadata_type_from_path
)
from tdda.utils import err


class TDDASerialError(Exception):
    pass


DataFrameWithMetadata = namedtuple('DataFrameWithMetadata', 'df md')


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
                                at the same level of a .tddaserial file,
                                the one to choose.

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
            err(f'{path} does not appear to be a tdda.serial file.')
        kw = md.get('tdda.serial')
        libs = {}
        for flavour in METADATA_FLAVOURS:
            spec = md.get(flavour)
            if spec:
                libs[flavour] = spec
        md = SerialMetadata(libs=libs, fill_from_lib=not kw, **kw)
    elif ext == '.json' or text.startswith('{'):
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
                raise TDDASerialError(
                    f'Unrecognized metadata content in {path}'
                )
            if kind == 'csvw':
                md = CSVWMetadata(path, table_number=table_number,
                                  for_table_name=for_table_name,
                                  verbosity=verbosity)

    elif ext == '.yaml':
        with open(path) as f:
            md = yaml.load(f, yaml.SafeLoader)
            kind = 'frictionless'
    else:
        raise TDDASerialError(f'Unexpected file extension {ext} for metadata '
                               f'file.\nExpected .json or .yaml.')
    if md_file_type and kind != md_file_type:
        raise TDDASerialError(
                  f'Expected {md_file_type} file; found {kind} file.'
              )

    return md


def get_metadata_for_reader(path, mdpath, md_file_type, findmd,
                            table_number, use_table_name, preferred,
                            verbosity):
    """
    Helper function for csv reader functions.

    Finds the metadata from the path, if available, or the path
    from the metadata, adhering to the preferences specified.
    Then loads the metadata, if found.

    Returns a tuple consisting of the metadata, the data path and the metadata
    path. If one of the input paths was None, it will now be updated.
    """
    md = None
    for_table_name = None
    if use_table_name:
        assert path is not None
        for_table_name = os.path.basename(path)
    if path is None:
        if mdpath is None:
            raise TDDASerialError('Must provide path or mdpath')
        else:
            md = load_metadata(mdpath, md_file_type=md_file_type,
                               table_number=table_number,
                               for_table_name=for_table_name,
                               preferred_serial_flavour=preferred)
            path = md._fullpath
            if path is None:
                raise TDDASerialError('No data specified.')


    if mdpath is None and findmd:
        mdpath = find_associated_metadata_file(path)
        if mdpath is None:
            raise TDDASerialError('Could not find any associated metadata '
                                   f'for {os.path.abspath(path)}')

    if md is None and mdpath is not None:
        md = load_metadata(mdpath, md_file_type=md_file_type,
                           table_number=table_number,
                           for_table_name=for_table_name, verbosity=verbosity)
    return md, path, mdpath


def csv2pandas(path=None, mdpath=None, md_file_type=None, findmd=False,
               upgrade_types=True, upgrade_possible_ints=False,
               return_md=False, table_number=None, use_table_name=False,
               preferred=None, verbosity=VERBOSITY,
               **kw):
    """
    Load the data from a CSV file into a Pandas DataFrame use pandas.read_csv
    and extra metadata.

    Args:

       path     The path to the data file (usually CSV) to be read.
                If this is None, the mdpath must be set and contain
                the path to the data.

       mdpath   The optional path to the associated metadata file.

                If path is None, this must be set and contain the
                path to the data (CSV file).

                If path is not None, the path in the metadata file
                is ignored.

                If mdpath is None, path must not be None.
                In this case, if findmd is set to True, this function
                will try to find an associated metadata file and use
                that if possible, and will raise an error if it cannot
                be found.

       md_file_type   Optional specification of the kind of metadata file.
                      Should be one of
                          'tdda.serial'
                          'csvw'
                          'frictionless'

       findmd   If this is set to True, the library will try to find
                associated metadata based on filename conventions.
                This should not be set if mdpath is provided.
                If assocaited metadata cannot be found, an error
                will be raised when this is set.

       upgrade_types   If True (the default), this will upgrade
                       some columns read_csv will create as object
                       (dtype object) to stricter types.

       upgrade_possible_ints   If True (not the default), any float
                               columns with nulls but with no fractional
                               components will be upgraded to Ints.

       return_md   If true, returns DataFrame and metadata (as tuple)

       table_number  If set, use the specified table number (indexed
                     from zero) in the metadata

       preferred  Normally, if tdda.serial metadata is used,
                  csv2pandas will use the panda.read_csv metadata flavour
                  if present. This can be set to 'tdda.serial'
                  or 'csvw' to override that.

       verbosity   For metadata reader

       **kw     These keyword arguments are passed to pandas.read_csv,
                and can be used to override values from the
                metadata file.
    """
    md, path, mdpath = get_metadata_for_reader(
         path=path, mdpath=mdpath, md_file_type=md_file_type,
         findmd=findmd, table_number=table_number,
         use_table_name=use_table_name,
         preferred=preferred or 'pandas.read_csv',
         verbosity=verbosity
     )

    if md:
        md_kw = to_pandas_read_csv_args(md)
    if md and kw:
        md_kw.update(kw)
        kw = md_kw
    elif md:
        kw = md_kw
    df = pd.read_csv(path, **kw)

    specified_types = kw.get('dtype')
    dates = (kw.get('date_format') or {}).keys()
    if upgrade_types and specified_types:
        for k in df:
            df[k].dtype == np.dtype('O')
            specified_type = specified_types.get(k)
            try:
                if specified_type:
                    df[k] = df[k].astype(specified_type)
                elif k in dates:
                    df[k] = df[k].astype('datetime64[ns]')
            except ValueError:  # probably time-zone aware date
                pass
    if upgrade_possible_ints:
        for k in df:
            if not k in (specified_types or []):
                poss_upgrade_to_int(df, k)
    return DataFrameWithMetadata(df, md) if return_md else df


def csv2polars(path=None, mdpath=None, md_file_type=None, findmd=False,
               upgrade_types=True, upgrade_possible_ints=False,
               return_md=False, table_number=None, use_table_name=False,
               preferred=None, verbosity=VERBOSITY,
               **kw):
    """
    Load the data from a CSV file into a Pandas DataFrame use pandas.read_csv
    and extra metadata.

    Args:

       path     The path to the data file (usually CSV) to be read.
                If this is None, the mdpath must be set and contain
                the path to the data.

       mdpath   The optional path to the associated metadata file.

                If path is None, this must be set and contain the
                path to the data (CSV file).

                If path is not None, the path in the metadata file
                is ignored.

                If mdpath is None, path must not be None.
                In this case, if findmd is set to True, this function
                will try to find an associated metadata file and use
                that if possible, and will raise an error if it cannot
                be found.

       md_file_type   Optional specification of the kind of metadata file.
                      Should be one of
                          'tdda.serial'
                          'csvw'
                          'frictionless'

       findmd   If this is set to True, the library will try to find
                associated metadata based on filename conventions.
                This should not be set if mdpath is provided.
                If assocaited metadata cannot be found, an error
                will be raised when this is set.

       upgrade_types   If True (the default), this will upgrade
                       some columns read_csv will create as object
                       (dtype object) to stricter types.

       upgrade_possible_ints   If True (not the default), any float
                               columns with nulls but with no fractional
                               components will be upgraded to Ints.

       return_md   If true, returns DataFrame and metadata (as tuple)

       table_number  If set, use the specified table number (indexed
                     from zero) in the metadata

       preferred  Normally, if tdda.serial metadata is used,
                  csv2pandas will use the polars.read_csv metadata flavour
                  if present. This can be set to 'tdda.serial'
                  or 'csvw' to override that.

       verbosity   For metadata reader

       **kw     These keyword arguments are passed to pandas.read_csv,
                and can be used to override values from the
                metadata file.
    """
    md, path, mdpath = get_metadata_for_reader(
         path=path, mdpath=mdpath, md_file_type=md_file_type,
         findmd=findmd, table_number=table_number,
         use_table_name=use_table_name,
         preferred=preferred or 'polars.read_csv',
         verbosity=verbosity
     )
    if md:
        md_kw = to_polars_read_csv_args(md)
    if md and kw:
        md_kw.update(kw)
        kw = md_kw
    elif md:
        kw = md_kw
    df = pl.read_csv(path, **kw)
    return DataFrameWithMetadata(df, md) if return_md else df



def poss_upgrade_to_int(df, name):
    field = df[name]
    if str(field.dtype).startswith('float'):
        n_nulls = sum(field.isnull())
        if n_nulls > 0:
            # Could be float as result of nulls
            int_col = field.astype(pd.Int64Dtype())
            n_same = sum(int_col.dropna() == field.dropna())
            if n_same + n_nulls == field.shape[0]:
                # no floats have fractional parts
                df[name] = int_col
        else:
            int_col = field.astype('int')
            n_same = sum(int_col== field)
            if n_same == field.shape[0]:
                # no floats have fractional parts
                df[name] = int_col


def find_metadata_kind(mds, preferred=''):
    """
    Breadth-first search of dict or list of dicts
    for a recognized blob of metadata.

    Returns the kind and subportion representing
    the metadata for the first found, or, if there are ties
    at the same leve, the preferred tdda.serial metadata flavour,
    if specified.

    If no metadata is found, returns None, None
    """
    kind = None
    dicts = []
    if not mds:
        return None, None
    if not isinstance(mds, list):
        mds = [mds]
    for md in mds:
        if preferred and preferred in md:
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





