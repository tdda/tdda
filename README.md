# Test-Driven Data Analysis (TDDA)

The `tdda` package provides Python support for
[test-driven data analysis](https://book.tdda.info)
([1-page summary](http://stochasticsolutions.com/pdf/TDDA-One-Pager.pdf),
[blog](http://www.tdda.info/pages/table-of-contents.html#table-of-contents),
[book](https://book.tdda.info)).

## Features

- **Reference Testing** (`tdda.referencetest`): extensions to `unittest` and
  `pytest` for testing data analysis pipelines. Supports file-based
  comparisons, semantic equivalence, automatic rewriting of reference results,
  and test tagging.

- **Automatic Test Generation** (`tdda gentest`): generates reference tests
  for any command-line script or program (Python, R, shell, Makefile, ...).
  *"Gentest writes tests, so you don't have to."*™

- **Constraints** (`tdda.constraints`): discovers constraints from Pandas
  DataFrames, Parquet files, flat files, and relational databases; verifies
  new data against those constraints; detects failing records.

- **Regular Expression Inference** (`tdda.rexpy`): automatically infers
  regular expressions from a column of string data.

- **Data Diff** (`tdda diff`): compares data frames in Parquet or flat files
  and reports differences in a visual format.

- **Serial Format** (`tdda.serial`): documents CSV and flat-file formats in
  `.serial` metadata files for accurate, portable reading and writing.
  Supports conversion to/from [CSVW](https://csvw.org) and
  [Frictionless](https://frictionlessdata.io) metadata.

- **Utility Functions** (`tdda.utils`): Unicode normalization (Normal Form TK),
  glyph counting, and RFC 9839 support.

## Documentation

Full documentation: [tdda.readthedocs.io](https://tdda.readthedocs.io)

## Installation

```
pip install tdda
```

To upgrade an existing installation:

```
pip install -U tdda
```

### Source installation

```
git clone https://github.com/tdda/tdda.git
cd tdda
pip install .
```

### Optional database support

```
pip install pygresql                  # PostgreSQL
pip install mysql-connector-python   # MySQL/MariaDB
pip install pymongo                  # MongoDB
```

## Testing

```
tdda test
```

## Resources

- [TDDA Blog](http://www.tdda.info)
- [Book](https://book.tdda.info)
- [Quick Reference Guide](http://www.tdda.info/pdf/tdda-quickref.pdf)
- [1-page summary](https://stochasticsolutions.com/pdf/TDDA-One-Pager.pdf)
- [Full documentation](https://tdda.readthedocs.io)
- [PyCon UK talk (video)](https://www.youtube.com/watch?v=FIw_7aUuY50)
- [Mastodon](https://mathstodon.xyz/@tdda)

## Authors

- Nick Radcliffe
- Simon Brown
