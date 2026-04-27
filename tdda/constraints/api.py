import sys

import pandas as pd
import polars as pl

from tdda.constraints.pd.constraints import discover_df, verify_df, detect_df
from tdda.constraints.pd.discover import discover_df_from_file
from tdda.constraints.pd.verify import verify_df_from_file
from tdda.constraints.pd.detect import detect_df_from_file

from tdda.abstractdf import get_engine_and_backend
from tdda.serial.utils import get_backend


def source_kind(src):
    """
    Attempts to identify the kind of data source src is.
    Usually it is a filepath to a known file type,
    most often a csv or other flat file, or a parquet file,
    or a DataFrame (currently a Pandas DataFrame).

    Returns:

      'parquet' if it's a parquet file

      'flat'    for any kind of text file
                (currently,any string that does not look like a parquet file)

      'pandas'  For a pandas DataFrame

      None if it doesn't look like anything known.

    """
    if type(src) == str:
        if src.endswith('.parquet'):
            return 'parquet'
        else:  # for now, assume anything else is a flat file
            return 'flat'
    elif isinstance(src, pd.DataFrame):
        return 'pandas'
    elif isinstance(src, pl.DataFrame):
        return 'polars'
    else:
        return None


def discover(
    indata,
    constraints_path=None,
    report_path=None,
    report_formats=None,
    engine=None,
    backend=None,
    verbose=True,
    **kwargs,
):
    """
    Automatically discover potentially useful constraints that characterize
    the data provided in the file.

    Input:

        *indata*:
            Data for which constraints are to be discovered.
            Can be a path to a suitable data file or a suitable
            data object (such as a DataFrame).

        *constraints_path*:
            The path to which to write the constraints.
            If None, constraints are not written.
            If '-', constraints are sent to stdout.

        *backend*:
            Backend to use (original/o, numpy_nullable/n, or pyarrow/a).

        *report_path*:
            Path for reports. Extension is ignored.
            Will write reports to variations of this path if set;
            otherwuse uses constraints_path

        *report_formats*:
            List of report formats to write from:
               html, markdown (or md), text (or txt), yaml, json, toml

        *verbose*:
            Controls level of output reporting

        *kwargs*:
            Passed to discover_df

    Returns:
        :py:class:`~tdda.constraints.pd.constraints.PandasVerification` object.
    """
    kind = source_kind(indata)

    engine, backend = get_engine_and_backend(engine, backend)
    if kind == 'pandas':
        return discover_df(
            indata,
            constraints_path,
            report_path=report_path,
            report_formats=report_formats,
            backend=backend,
            verbose=verbose,
            **kwargs,
        )
    elif kind in ('parquet', 'flat') and engine == 'pandas':
        return discover_df_from_file(
            indata,
            constraints_path,
            report_path=report_path,
            report_formats=report_formats,
            backend=backend,
            verbose=verbose,
            **kwargs,
        )
    else:
        print('Unsupported discovery mode', file=sys.stderr)
        sys.exit(1)


def verify(
    indata,
    constraints_path,
    outdata=None,
    verbose=True,
    engine=None,
    backend=None,
    md_path=None,
    **kwargs,
):
    """
    Verify that (i.e. check whether) the data provided
    satisfies the constraints in the JSON ``.tdda`` file provided.

    Inputs:

        *indata*:
             Path to a file containing data to be verified or
             object containing data to be verified.

        *constraints_path*:
             The path to a JSON ``.tdda`` file.
             Alternatively, can be an in-memory
             :py:class:`~tdda.constraints.base.DatasetConstraints` object.

        *verbose*:
            Controls level of output reporting

        *backend*:
            Backend to use (original/o, numpy_nullable/n, or pyarrow/a).

        *md_path*:
            Path to metadata for indata (if any)

        *kwargs*:
            Passed to discover_df

    Returns:
        JSON description of constraints.
    """
    kind = source_kind(indata)
    engine, backend = get_engine_and_backend(engine, backend)
    if kind == 'pandas':
        return verify_df(
            indata,
            constraints_path,
            engine=engine,
            backend=backend,
            verbose=verbose,
            **kwargs,
        )
    elif kind in ('parquet', 'flat') and engine == 'pandas':
        return verify_df_from_file(
            indata,
            constraints_path,
            verbose=verbose,
            backend=backend,
            md_path=md_path,
            **kwargs,
        )
    else:
        print('Unsupported verification mode (%s)' % kind, file=sys.stderr)
        sys.exit(1)


def detect(indata, constraints_path, outpath=None, engine=None, backend=None, **kwargs):
    """
    Check the records from the Pandas DataFrame provided, to detect
    records that fail any of the constraints in the JSON ``.tdda`` file
    provided. This is anomaly detection.

    Inputs:

        *indata*:
             Path to data to be checked or object containining data.

        *constraints_path*:
             The path to a JSON ``.tdda`` file.
             Alternatively, can be an in-memory
             :py:class:`~tdda.constraints.base.DatasetConstraints` object.

        *outpath*:
            Optional destination to write output records.
            Normally path for a CSV or parquet file.
            None for no output.

        *verbose*:
            Controls level of output reporting

        *backend*:
            Backend to use (original/o, numpy_nullable/n, or pyarrow/a).

        *kwargs*:
            Passed to discover_df

    Returns:
        :py:class:`~tdda.constraints.pd.constraints.PandasDetection` object.
    """
    kind = source_kind(indata)
    engine, backend = get_engine_and_backend(engine, backend)
    if kind == 'pandas':
        return detect_df(
            indata,
            constraints_path,
            outpath=outpath,
            engine=engine,
            backend=backend,
            **kwargs,
        )
    elif kind in ('parquet', 'flat') and engine == 'pandas':
        return detect_df_from_file(
            indata,
            constraints_path,
            outpath=outpath,
            engine=engine,
            backend=backend,
            **kwargs,
        )
    else:
        print(f'Unsupported detect mode ({kind})', file=sys.stderr)
        sys.exit(1)
