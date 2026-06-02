# Reference Tests

```{eval-rst}
.. automodule:: tdda.referencetest
    :members:
```

## Methods and Functions

```{eval-rst}
.. automodule:: tdda.referencetest.referencetest
    :members: ReferenceTest, tag
```

## `unittest` Framework Support

```{eval-rst}
.. automodule:: tdda.referencetest.referencetestcase
    :members: ReferenceTestCase, main
```

## `pytest` Framework Support

```{eval-rst}
.. automodule:: tdda.referencetest.referencepytest
    :members: ref, set_defaults, set_default_data_location
```

(reference_test_examples)=

## Supplied Reference Test Examples

The `tdda.referencetest` module includes a set of examples,
for both `unittest` and `pytest`.

To copy these examples, run the command:

```
tdda examples referencetest [directory]
```

If `directory` is not supplied, `referencetest_examples` will be used.

Alternatively, you can copy all examples using the following command:

```
tdda examples
```

which will create a number of separate subdirectories.

```{include} ../../tdda/referencetest/examples/README.md
:heading-offset: 1
:start-line: 2
```
