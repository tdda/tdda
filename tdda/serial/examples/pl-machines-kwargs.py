from tdda.serial import (load_metadata, serial_to_polars_read_csv_args)
from rich import print as rprint

md = load_metadata('machines.serial')
kwargs = serial_to_polars_read_csv_args(md, map_other_bools_to_string=True)
rprint(kwargs)




