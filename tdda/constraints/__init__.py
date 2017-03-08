"""
The :py:mod:`~tdda.constraints` module provides support for
constraint generation and verification for datasets, including
CSV files and Pandas DataFrames.

The module includes:

    - Tools :py:mod:`~tdda.constraints.pddiscover` for discovering constraints
      in Pandas DataFrames saved in :py:mod:`feather` files or read from
      CSV files,
      and :py:mod:`~tdda.constraints.pdverify` for validating :py:mod:`feather`
      files against previously-generated sets of constraints.
    - A Python library :py:mod:`~tdda.constraints.pdconstraints` containing
      classes that implement constraint discovery and validation, for
      use from within other Python programs.

Prerequisites
-------------

    - :py:mod:`numpy`
    - :py:mod:`pandas`
    - :py:mod:`feather-format` (required for the :py:mod:`~tdda.constraints.pdverify` tool)

These can be installed with::

    pip install numpy
    pip install pandas
    pip install feather-format


"""
