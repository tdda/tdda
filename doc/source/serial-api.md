# TDDA Serial API

## `tdda.serial`

### Reading CSV Files

```{eval-rst}
.. autofunction:: tdda.serial.csv_to_pandas
```

```{eval-rst}
.. autofunction:: tdda.serial.csv_to_polars
```

### Writing CSV Files

```{eval-rst}
.. autofunction:: tdda.serial.pandas_to_csv
```

### Loading Metadata

```{eval-rst}
.. autofunction:: tdda.serial.load_metadata
```

### Inferring Metadata

```{eval-rst}
.. autofunction:: tdda.serial.infer_format_from_flat_file
```

### Metadata Classes

```{eval-rst}
.. autoclass:: tdda.serial.SerialMetadata
   :members:
```

```{eval-rst}
.. autoclass:: tdda.serial.FieldMetadata
   :members:
```

```{eval-rst}
.. autoclass:: tdda.serial.FieldType
   :members:
```

```{eval-rst}
.. autoclass:: tdda.serial.DateFormat
   :members:
```

```{eval-rst}
.. autoclass:: tdda.serial.DateStyle
   :members:
```

### Format Conversion

```{eval-rst}
.. autofunction:: tdda.serial.serial_to_csvw
```

```{eval-rst}
.. autofunction:: tdda.serial.serial_to_frictionless
```

```{eval-rst}
.. autoclass:: tdda.serial.CSVWMetadata
   :members:
```

```{eval-rst}
.. autoclass:: tdda.serial.FrictionlessMetadata
   :members:
```

### Low-level Arguments

```{eval-rst}
.. autofunction:: tdda.serial.serial_to_pandas_read_csv_args
```

```{eval-rst}
.. autofunction:: tdda.serial.serial_to_polars_read_csv_args
```
