### Command: `tdda serial`


#### NAME

`tdda serial`  - Converts, interrogates and creates serial metadata files.

#### DESCRIPTION

Use tdda serial [--to FORMAT] in.serial  out.serial
to convert metadata in.serial to out.serial in the output
format specified (or tdda.serial if none is specified).
Input and output metdata can also be CSVW files (.json)
Supported formats:

  SHORT FORM  LONG FORM
  `.`         `tdda.serial`
  `pd.r`      `pandas.read_csv`
  `pd.w`      `pandas.DataFrame.to_csv`
  `pl.`       `polars.read_csv`
  `pl.w`      `polars.DataFrame.write_csv`
  `csv.r`     `python.csv.reader`
  `s`.w`      `python.csv.writier`
  `csvw`      `CSVW`

Multiple formats can be separated by commas.
