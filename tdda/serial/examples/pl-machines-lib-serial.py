from tdda.serial import (
    SerialMetadata,
    load_metadata,
    serial_to_polars_read_csv_args
)
from tdda.serial.polarsio import as_polars_serial_lib_args

md = load_metadata('machines.serial')
kwargs = serial_to_polars_read_csv_args(md, map_other_bools_to_string=True)
pl_md = SerialMetadata()
pl_md.libs['polars.read_csv'] = as_polars_serial_lib_args(kwargs)
print(pl_md.to_json())
