from tdda.utils import nvl, error
from tdda.serial.utils import get_backend
from tdda.state import get_config

ENGINES = {
    'pandas': 'pandas',
    'polars': 'polars',
    'pd': 'pandas',
    'pl': 'polars',
}


def process_pandas_flags(config, o):
    config = get_config(config)
    engine = 'polars' if o.polars else 'pandas' if o.pandas else None
    engine = ENGINES.get(engine, config.engine)
    if engine is None:
        error(
            f'Engine "{o.engine}" unknown. Should be pandas (pd) or polars (pl).'
        )
    else:
        config.engine = engine

    config.backend = backend = nvl(o.backend, config.pandas_backend)

    return engine, backend


def add_pandas_flags(parser):
    parser.add_argument(
        '--pandas',
        '--pd',
        action='store_true',
        help='Use Pandas as DataFrame engine.',
    )

    parser.add_argument(
        '--polars',
        '--pl',
        action='store_true',
        help='Use Polars as DataFrame engine.',
    )

    parser.add_argument(
        '--backend',
        '-B',
        type=str,
        action='store',
        help=(
            'Pandas backend choice. '
            '(n for numpy_nullable, a for pyarrow, o for original).'
        ),
    )
