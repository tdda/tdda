from tdda.serial import load_metadata, serial_to_pandas_read_csv_args, SerialMetadata
from rich import print as rprint

md = load_metadata('machines.serial')
kwargs = serial_to_pandas_read_csv_args(md)
rprint(kwargs)

# out_md = SerialMetadata()
# out_md.libs['polars.read_csv'] = kwargs
