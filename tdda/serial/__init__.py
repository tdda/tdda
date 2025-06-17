from . import base

CSVMETADATA = 'csvmetadata'
CSVW = 'csvw'
FRICTIONLESS = 'frictionless'

from tdda.serial.reader import load_metadata
from tdda.serial.pandasio import csv_to_pandas
from tdda.serial.polarsio import csv_to_polars
from tdda.serial.base import (
    DateFormat,
    FieldMetadata,
    FieldType,
    SerialMetadata,
)
