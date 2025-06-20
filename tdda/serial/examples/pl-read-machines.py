from tdda.serial.polarsio import csv_to_polars

df = csv_to_polars('machines.psv', 'machines.serial',
                   map_other_bools_to_string=True)
print(df)

