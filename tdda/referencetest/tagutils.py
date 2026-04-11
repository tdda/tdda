import os
import shutil

REFTEST = os.path.dirname(__file__)
TDDA = os.path.dirname(REFTEST)
TESTDATA = os.path.join(REFTEST, 'testdata')

TEST_FILES = (
    '__init__.py',
    'test_tagging.py',
    'test_tagsa.py',
    'test_tagsb.py',
    'test_tagsc.py',
)


def copy_files(src=TESTDATA, dest=None, files=TEST_FILES):
    for p in files:
        shutil.copy(os.path.join(src, p), os.path.join(dest, p))
