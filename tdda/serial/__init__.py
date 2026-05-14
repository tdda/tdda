# from . import metadata

CSVMETADATA = 'csvmetadata'
CSVW = 'csvw'
FRICTIONLESS = 'frictionless'

from tdda.serial.reader import load_metadata
from tdda.serial.pandasio import (
    csv_to_pandas,
    pandas_to_csv,
    serial_to_pandas_read_csv_args,
)
from tdda.serial.polarsio import csv_to_polars, serial_to_polars_read_csv_args
from tdda.serial.metadata import (
    DateFormat,
    DateStyle,
    FieldMetadata,
    FieldType,
    SerialMetadata,
)
from tdda.serial.csvw import CSVWMetadata, serial_to_csvw
from tdda.serial.frictionless import FrictionlessMetadata, serial_to_frictionless
from tdda.serial.infer import infer_format_from_flat_file
