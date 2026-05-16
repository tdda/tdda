# Installation

If you don't need source, the simplest way to install the TDDA library is
to do a normal `pip` install:

```
pip install tdda
```

If you have multiple Python installations and want to ensure you use the
right one, use:

```
python -m pip install tdda
```

replacing `python` with whatever you need to use to run your target
version of Python.

:::{note}
If you run as a user who cannot write to the system's site-packages
directory, this will install only for the current user. If you want
`tdda` available for all users, you may need root access and to use
`sudo pip install tdda`, with the usual caveats that this affects the
system Python (or whichever Python you specify).
:::

If you prefer to install in a virtual environment, see
[Virtual Environments](#virtual-environments), though this may be
inconvenient if you use the library or tools regularly.

## Upgrading

Add `--upgrade` or `-U` after `install` in the commands above
to upgrade an existing installation.
This is a general pattern for `pip`:

```
pip install -U tdda
```

or:

```
python -m pip install -U tdda
```

## Source installation

The [tdda](https://github.com/tdda/tdda) project is hosted on Github at
[github.com/tdda/tdda](https://github.com/tdda/tdda).

Clone the repository with:

```
git clone git@github.com:tdda/tdda.git
```

or:

```
git clone https://github.com/tdda/tdda.git
```

Then install from the cloned directory:

```
cd tdda
pip install .
```

If you plan to modify the source and want changes to take effect without
reinstalling, use an editable install instead:

```
pip install -e .
```

:::{note}
If you see a `pyproject.toml` in the repository and are tempted to run
`pip install -r pyproject.toml`, don't: that only installs the listed
*dependencies*, not `tdda` itself. The `tdda` command-line tools and the
`tdda` Python package will not be available.
:::


## Virtual Environments

Virtual environments (venvs) are good practice in many circumstances, but may not
be the most convenient choice for `tdda`. If you install `tdda` in a
dedicated venv, the `tdda` command-line tools are only available when that
venv is activated. This is particularly awkward for
[`tdda gentest`](cli.md#tdda-gentest) and reference testing, where tests
run commands as subprocesses and may be shared with others or run in CI
environments that know nothing about your venv. In practice, either a
global install or installing `tdda` as a dependency of each project that
uses it tends to work better.

That said, if you do want to use a venv, with the standard `venv` module:

```
python -m venv .venv
. .venv/bin/activate        # Linux/Mac
.venv\Scripts\activate      # Windows
pip install tdda
```

With [uv](https://docs.astral.sh/uv/), which is significantly faster:

```
uv venv
. .venv/bin/activate
uv pip install tdda
```

or for a source install:

```
uv venv
. .venv/bin/activate
uv pip install -e .
```

If you only want to run a `tdda` command occasionally without a permanent
install, [uvx](https://docs.astral.sh/uv/guides/tools/) can run it in a
temporary environment, e.g. to validate data in `data.csv` using constraints
in `constraints.tdda`:

```
uvx tdda verify data.csv constraints.tdda
```

This works well for commands like [`tdda discover`](cli.md#tdda-discover),
[`tdda verify`](cli.md#tdda-verify), [`tdda detect`](cli.md#tdda-detect),
and [`tdda diff`](cli.md#tdda-diff). It is not suitable for
[`tdda gentest`](cli.md#tdda-gentest): the generation step will work, but
the generated tests import from `tdda.referencetest`, so running them will
fail with an `ImportError` unless `tdda` is installed in the
environment where the tests are run.

## Checking the installation

If all has gone well, you should be able to type:

```
tdda
```

and it will show you some help.

You should also be able to use:

```python
>>> import tdda
>>> tdda.__version__
```

from your Python successfully.

To run the test suite:

```
tdda test
```

Some tests will be skipped if you haven't configured any databases,
which is fine.


(optional_installations)=

## Optional Installations for using Databases

Extra libraries are required to access some of the constraint-generation
and verification functionality, depending on the data sources that you
wish to use.

* `pygresql` (required for PostgreSQL database tables)
* `MySQL-python` or `mysqlclient` or `mysql-connector-python`
  (required for MySQL/MariaDB database tables)
* `pymongo` (required for MongoDB document collections)


These can be installed with (some/all of):

```
pip install pygresql
pip install pymongo
```

and, for MySQL, **one** of:

```
pip install MySQL-python
pip install mysqlclient
pip install mysql-connector-python
```

