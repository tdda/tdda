import pandas
import polars

pd = pandas
pl = polars

from tdda.captureoutput import CaptureOutput
from tdda.referencetest import ReferenceTestCase, tag

from tdda.serial import csv_to_pandas, csv_to_polars
from tdda.serial.testserial import (
    TESTDATADIR,
    tdpath,
    tmppath,
)
from tdda.utils import testwarn
from tdda.referencetest.checkpandas import PandasComparison


class TestBookSerial(ReferenceTestCase):
    """
    Tests from the serial chapter of the book
    """

    def test_csv_to_polars1(self):
        """
        8.2.2.
        >>> from tdda.serial import csv_to_polars
        >>> df = csv_to_polars('elements3-old.csv', 'elements3-old.serial')

        Claim: Same as reading parquet

        Produces warning.
        """

        Warn, buf = testwarn()
        df = csv_to_polars(
            tdpath('elements3-old.csv'),
            tdpath('elements3-old.serial'),
            warner=Warn,
        )
        ref_df = polars.read_parquet(tdpath('elements3-old.parquet'))

        self.assertDataFramesEqual(df, ref_df)
        self.assertEqual(
            buf,
            [
                'Polars does not understand escape characters.\n'
                'Ignoring escape value: \\\n'
            ],
        )

    def test_csv_to_pandas1(self):
        """
        8.2.2.
        >>> from tdda.serial import csv_to_pandas
        >>> df = csv_to_pandas('elements3-old.csv', 'elements3-old.serial')

        Claim: Same as reading parquet with read_parquet if use original
        back end. By implication, not identical otherwise.
        """
        from tdda.serial import csv_to_pandas

        df = csv_to_pandas(
            tdpath('elements3-old.csv'), tdpath('elements3-old.serial')
        )
        ref_df = pandas.read_parquet(tdpath('elements3-old.parquet'))

        # matches loosely
        self.assertDataFramesEqual(df, ref_df, type_matching='loose')

        # Should *not* match exactly (types!)
        C = PandasComparison(verbose=False)
        (failures, msgs) = C.check_dataframe(
            df, ref_df, type_matching='medium'
        )
        self.assertEqual(failures, 1)  # types
        # Could check exactly the expected messages
        self.assertIn('Wrong column type', ''.join(msgs))

        df = csv_to_pandas(
            tdpath('elements3-old.csv'),
            tdpath('elements3-old.serial'),
            backend='original',
        )

        # Not quite identical: datetime64[ns] vs. datetime64[us]
        # for ApproxDiscovery. OK at medium
        self.assertDataFramesEqual(df, ref_df, type_matching='medium')

    def test_csv_to_pandas_find_md(self):
        """
        8.2.2
        >>> df = csv_to_pandas('elements3-old.csv', find_md=True)
        Says this works same as previous.
        """
        df = csv_to_pandas(tdpath('elements3-old.csv'), find_md=True)
        ref_df = csv_to_pandas(
            tdpath('elements3-old.csv'), tdpath('elements3-old.serial')
        )
        # So should be identical
        self.assertDataFramesEqual(df, ref_df, type_matching='strict')

        # Might as well add (colon for find)

        df = csv_to_pandas(tdpath('elements3-old.csv:'))
        self.assertDataFramesEqual(df, ref_df, type_matching='strict')

        # And this (to show that the metadata's actually making
        # a difference)

        df = csv_to_pandas(tdpath('elements3-old.csv'))
        C = PandasComparison(verbose=False)
        (failures, msgs) = C.check_dataframe(
            df, ref_df, type_matching='medium'
        )
        self.assertTrue(failures > 0)


if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
