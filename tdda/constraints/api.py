import sys

try:
    import pandas as pd
except ImportError:
    pd = None

if pd is not None:
    from tdda.constraints.pd.constraints import (discover_df,
                                                 verify_df,
                                                 detect_df)
    from tdda.constraints.pd.discover import discover_df_from_file
    from tdda.constraints.pd.verify import verify_df_from_file
    from tdda.constraints.pd.detect import detect_df_from_file


DEFAULT_BACKEND = 'pandas'


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
    elif pd and isinstance(src, pd.DataFrame):
        return 'pandas'
    else:
        return None


def discover(indata, constraints_path, verbose=True, backend=DEFAULT_BACKEND,
             **kwargs):
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

        *verbose*:
            Controls level of output reporting

        *backend*:
            Backend to use.
            Currently only pandas is supported.

        *kwargs*:
            Passed to discover_df

    Returns:
        :py:class:`~tdda.constraints.pd.constraints.PandasVerification` object.
    """
    kind = source_kind(indata)
    if indata == 'pandas':
        discover_df(indata, constraints_path, verbose=verbose, **kwargs)
    elif indata in ('parquet', 'flat') and backend == pandas:
        discover_df_from_file(indata, constraints_path, verbose=verbose,
                              **kwargs)
    else:
        print('Unsupported discovery mode', file=sys.stderr)
        sys.exit(1)


def verify(indata, constraints_path, outdata=None, verbose=True,
           backend=DEFAULT_BACKEND, **kwargs):
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
            Backend to use.
            Currently only pandas is supported.

        *kwargs*:
            Passed to discover_df

    Returns:
        JSON description of constraints.
    """
    kind = source_kind(indata)
    if kind == 'pandas':
        return verify_df(indata, constraints_path, verbose=verbose, **kwargs)
    elif kind in ('parquet', 'flat') and backend == 'pandas':
        return verify_df_from_file(indata, constraints_path, verbose=verbose,
                              **kwargs)
    else:
        print('Unsupported verification mode (%s)' % kind, file=sys.stderr)
        sys.exit(1)


def detect(df_path, constraints_path, outpath=None, backend=DEFAULT_BACKEND,
           **kwargs):
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
            Backend to use.
            Currently only pandas is supported.

        *kwargs*:
            Passed to discover_df

    Returns:
        :py:class:`~tdda.constraints.pd.constraints.PandasDetection` object.
    """
    kind = source_kind(indata)
    if indata == 'pandas':
        detect_df(indata, constraints_path, outpath=outpath,
                  verbose=verbose, **kwargs)
    elif indata in ('parquet', 'flat') and backend == pandas:
        dect_df_from_file(indata, constraints_path, verbose=verbose,
                          outpath=outpath, **kwargs)
    else:
        print('Unsupported detect mode', file=sys.stderr)
        sys.exit(1)




