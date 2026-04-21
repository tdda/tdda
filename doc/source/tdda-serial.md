### Command: `tdda serial`


#### NAME

`tdda serial`  - Converts, interrogates and creates serial metadata files.

#### SYNOPSIS
```x
tdda serial [FLAGS] inmetadata outmetadata  
tdda serial --to FMT [FLAGS] inmetadata outmetadata  

Converts metadata from one metadata format, in inpath,
to another, in outpath.

tdda serial [FLAGS] indata outmetadata

Creates metadata for in indata in outmetadata

tdda serial [FLAGS] inmetadata script.py

Creates Python code for reading a file in the format in inmetadata as
Python. Often, a reading library would be specified, e.g.

tdda serial a.serial a.py --to pd.r

which specifies that they Python script should use pandas.read_csv.


Supported formats FMT:

  SHORT FORM  LONG FORM/Description
  .         tdda.serial
  pd.r      pandas.read_csv
  pd.w      pandas.DataFrame.to_csv
  pl.       polars.read_csv
  pl.w      polars.DataFrame.write_csv
  csv.r     python.csv.reader
  csv.w     python.csv.writer
  csvw      CSVW
  fl        frictionless
  fless     frictionless
  fl.r      frictionless.resource
  fl.p      frictionless.package

Multiple formats can be separated by commas.

Format is usually inferred from filename if following common conventions
for tdda.serial, CSVW, and frictionless.
```
#### OPTIONS

`--to FMT`             Specify output metadata format (see list of formats above)

`-B BE, --backend BE`  Specify backend for Pandas flavours:
                         `n`: `numpy_nullable`
                         `a`: `pyarrow`
                         `o`: for original Pandas backend.

`--for FILE`            Filename for data to use when generating CSVW
                        or Frictionless data.
                        (Can also be used for `tdda.serial` and `.py` output)

`-g, --gen, --generate`  Generate (infer) metadata for flat file

`-v, --verbose`          Verose output
`-V, --Verbose`          More verose output


#### EXAMPLES

`tdda serial a.csv a.serial`
   Generate tdda.serial metadata describing format of `a.csv` in `a.serial`.

`tdda serial --to . a.csv a.serial`
    Same as previous, expicitly specifying the default, `tdda.serial`,
    output format with `.`.

`tdda serial a.csv a-metadata.json`
    Generate CSVW metadata describing format of `a.csv` in `a-metadata.json`

`tdda serial --to csvw a.csv a.json`
    Same as previous, explicitly specifying format with non-standard output name

`tdda serial a.serial a-metadata.json`
    Generate Converts `tdda.metadata` metadata to CSVW

`tdda serial a-metadata.json a.serial`
    Generate Converts `tdda.metadata` metadata to CSVW




#### BUGS

The `tdda serial` functionality is fairly new, and there are probably
still many bugs an undesirable features in the implementation.
