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
    """Discover constraints characterizing the data provided.

    Args:
        indata: Data for which constraints are to be discovered. Can be
            a path to a data file (CSV, parquet, or other flat file) or
            a DataFrame (Pandas or Polars).
        constraints_path: Path to write discovered constraints to. If
            ``None``, constraints are not written. If ``'-'``,
            constraints are written to stdout.
        report_path: Path for reports (extension ignored). Writes
            reports to variations of this path if set; otherwise uses
            ``constraints_path``.
        report_formats: List of report formats to write. Options:
            ``'html'``, ``'markdown'`` (or ``'md'``), ``'text'`` (or
            ``'txt'``), ``'yaml'``, ``'json'``, ``'toml'``.
        engine: DataFrame engine: ``'pandas'`` or ``'polars'``.
        backend: Pandas backend: ``'numpy_nullable'`` (or ``'n'``),
            ``'pyarrow'`` (or ``'a'``), or ``'original'`` (or ``'o'``).
        verbose: Controls level of output reporting. Default is
            ``True``.
        **kwargs: Additional keyword arguments passed to
            ``discover_df``.

    Returns:
        DatasetConstraints: Discovered constraints.
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
    """Verify that the data provided satisfies the constraints in the
    ``.tdda`` file provided.

    Args:
        indata: Path to a data file or a DataFrame to be verified.
        constraints_path: Path to a JSON ``.tdda`` file, or an
            in-memory ``DatasetConstraints`` object.
        outdata: Optional destination for output data.
        verbose: Controls level of output reporting. Default is
            ``True``.
        engine: DataFrame engine: ``'pandas'`` or ``'polars'``.
        backend: Pandas backend: ``'numpy_nullable'`` (or ``'n'``),
            ``'pyarrow'`` (or ``'a'``), or ``'original'`` (or ``'o'``).
        md_path: Path to metadata for ``indata``, if any.
        **kwargs: Additional keyword arguments passed to ``verify_df``.

    Returns:
        PandasVerification: Verification results.
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


def detect(
    indata, constraints_path, outpath=None, engine=None, backend=None, **kwargs
):
    """Detect records that fail any of the constraints in the ``.tdda``
    file provided.

    Args:
        indata: Path to a data file or a DataFrame to be checked.
        constraints_path: Path to a JSON ``.tdda`` file, or an
            in-memory ``DatasetConstraints`` object.
        outpath: Optional path for output records (CSV or parquet).
            ``None`` for no output.
        engine: DataFrame engine: ``'pandas'`` or ``'polars'``.
        backend: Pandas backend: ``'numpy_nullable'`` (or ``'n'``),
            ``'pyarrow'`` (or ``'a'``), or ``'original'`` (or ``'o'``).
        **kwargs: Additional keyword arguments passed to ``detect_df``.

    Returns:
        PandasDetection: Detection results.
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
