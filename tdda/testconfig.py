import os
import shutil
import tempfile

from tdda.config import Config
from tdda.referencetest import ReferenceTestCase


class TestConfig(ReferenceTestCase):
    def testSerialInMetadataPath(self):
        config = Config(testing=True)  # empty, no load
        cwd = os.getcwd()

        csvfile = '/any/old/dirpath/a.csv'
        default_in_d = '/any/old/dirpath/_write.serial'
        default_in_cwd = './_write.serial'

        sc = config.serial

        # default: should be _write.serial in the temporary directory
        # where a (nominally) is.
        self.assertEqual(sc._get_inpath_list(csvfile), [default_in_d])
        self.assertEqual(sc._get_inpath_list(), [default_in_cwd])

        homedir_file = '~/write.serial'
        abspath_file = '/any/old/dirpath/abs_write.serial'

        sc.md_inpath.extend([homedir_file, abspath_file])

        homedir = os.path.expanduser('~')
        abs_homedir_file = os.path.join(homedir, 'write.serial')

        # as before, plus the homedir file as an absolute path.
        # plus the absolute path given.
        self.assertEqual(
            sc._get_inpath_list(csvfile),
            [
                default_in_d,
                abs_homedir_file,
                abspath_file,
            ],
        )

        # as previous, but with default as ./_write_serial
        self.assertEqual(
            sc._get_inpath_list(),
            [
                default_in_cwd,
                abs_homedir_file,
                abspath_file,
            ],
        )

        # No default
        sc.md_inpath = []
        self.assertEqual(sc._get_inpath_list(csvfile), [])
        self.assertEqual(sc._get_inpath_list(), [])

        # None default
        sc.md_inpath = None
        self.assertEqual(sc._get_inpath_list(csvfile), [])
        self.assertEqual(sc._get_inpath_list(), [])


if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=True)
