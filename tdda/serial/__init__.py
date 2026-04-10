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
    FieldMetadata,
    FieldType,
    SerialMetadata,
)
