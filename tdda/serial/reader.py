import os
import json
import yaml

import numpy as np
import pandas as pd

from tdda.serial.base import CONTEXT_KEY, URI, MetadataError
from tdda.serial.csvw import CSVWConstants, CSVWMetadata
from tdda.serial.pandasio import to_pandas_read_csv_args

from tdda.serial.utils import (
    find_associated_metadata_file,
    find_metadata_type_from_path,
)



def load_metadata(path, mdtype=None):
    """
    Attempt to load metadata from path given.

    Args:

      path    Path to the metadata file

      mdtype    Optional metadata kind. One of
                'csvmetadata'  (csvmetadata.CSVMETADATA)
                'csvw'         (csvmetadata.CSVW)
                'fictionless'  (csvmetadata.FRICTIONLESS)


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
            md = CSVWMetadata(path)
        else:
            kind, _ = find_metadata_type_from_path(path)
            if not kind:
                raise CSVMetadataError(
                    f'Unrecognized metadata content in {path}'
                )


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
               upgrade_types=True,  **kw):
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
                       (dtype='O') to stricter types.

       **kw     These keyword arguments are passed to pandas.read_csv,
                and can be used to override values from the
                metadata file.
    """
    md = None
    if path is None:
        if mdpath is None:
            raise CSVMetadataError('Must provide path or mdpath')
        else:
            md = load_metadata(mdpath, mdtype=mdtype)
            path = md._fullpath
            if path is None:
                raise CSVMetadataError('No data specified.')


    if mdpath is None and findmd:
        mdpath = find_associated_metadata_file(path)
        if mdpath is None:
            raise CSVMetadataError('Could not find any associated metadata '
                                   f'for {os.path.abspath(path)}')

    if md is None and mdpath is not None:
        md = load_metadata(mdpath, mdtype=mdtype)

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
    return df
