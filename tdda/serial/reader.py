import os
import json
import yaml

import numpy as np
import pandas as pd

from tdda.serial.base import CONTEXT_KEY, URI, MetadataError, VERBOSITY
from tdda.serial.csvw import CSVWConstants, CSVWMetadata
from tdda.serial.pandasio import to_pandas_read_csv_args

from tdda.serial.utils import (
    find_associated_metadata_file,
    find_metadata_type_from_path
)


class CSVMetadataError(Exception):
    pass


def load_metadata(path, mdtype=None, table_number=None, for_table_name=None,
                  verbosity=VERBOSITY):
    """
    Attempt to load metadata from path given.

    Args:

      path    Path to the metadata file

      mdtype    Optional metadata kind. One of
                'csvmetadata'  (csvmetadata.CSVMETADATA)
                'csvw'         (csvmetadata.CSVW)
                'fictionless'  (csvmetadata.FRICTIONLESS)

      table_number  If specified, use the nth table from a CSVW file.
                    Raise an error if not present, (indexed from zero)

      for_table_name  If specified, use choose the metadata from
                      a metadata file describing multiple tables
                      by matching the (end of the) url in the metadata
                      to this table name

      verbosity:   2: errors and warnings to stderr
                   1: warnings to stderr
                   0: don't show errors or warnings
    """
    stem, ext = os.path.splitext(path)
    lcstem, ext = stem.lower(), ext.lower()
    if ext == '.json':
        with open(path) as f:
            md = json.load(f)
        context = md.get(CONTEXT_KEY)
        if context == URI.TDDAMETADATA:
            kind = 'csvmetadata'
        elif context == URI.CSVW:
            kind = 'csvw'
            md = CSVWMetadata(path, table_number=table_number,
                              for_table_name=for_table_name,
                              verbosity=verbosity)
        else:
            kind, _ = find_metadata_type_from_path(path)
            if not kind:
                raise CSVMetadataError(
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
        raise CSVMetadataError(f'Unexpected file extension {ext} for metadata '
                               f'file.\nExpected .json or .yaml.')
    if mdtype and kind != mdtype:
        raise CSVMetadataError(f'Expected {mdtype} file; found {kind} file.')

    return md


def csv2pandas(path=None, mdpath=None, mdtype=None, findmd=False,
               upgrade_types=True, upgrade_possible_ints=False,
               return_md=False, table_number=None, use_table_name=False,
               verbosity=VERBOSITY,
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

       mdtype   Optional specification of the kind of metadata file.
                Should be one of
                    'csvmetadata'   (csvmetadata.CSVMETADATA)
                    'csvw'          (csvmetadata.CSVW)
                    'frictionless'  (csvmetadata.FRICTIONLESS)

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

       return_md   If true, returns metadata and DataFrame (as tuple)

       table_number  If set, use the specified table number (indexed
                     from zero) in the metadata

       verbosity   For metadata reader

       **kw     These keyword arguments are passed to pandas.read_csv,
                and can be used to override values from the
                metadata file.
    """
    md = None
    for_table_name = None
    if use_table_name:
        assert path is not None
        for_table_name = os.path.basename(path)
    if path is None:
        if mdpath is None:
            raise CSVMetadataError('Must provide path or mdpath')
        else:
            md = load_metadata(mdpath, mdtype=mdtype,
                               table_number=table_number,
                               for_table_name=for_table_name)
            path = md._fullpath
            if path is None:
                raise CSVMetadataError('No data specified.')


    if mdpath is None and findmd:
        mdpath = find_associated_metadata_file(path)
        if mdpath is None:
            raise CSVMetadataError('Could not find any associated metadata '
                                   f'for {os.path.abspath(path)}')

    if md is None and mdpath is not None:
        md = load_metadata(mdpath, mdtype=mdtype, table_number=table_number,
                           for_table_name=for_table_name, verbosity=verbosity)

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
            if specified_type:
                df[k] = df[k].astype(specified_type)
            elif k in dates:
                df[k] = df[k].astype('datetime64[ns]')
    if upgrade_possible_ints:
        for k in df:
            if not k in (specified_types or []):
                poss_upgrade_to_int(df, k)
    return (df, md) if return_md else df


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
