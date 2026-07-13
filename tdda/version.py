TDDA_MAJOR_VERSION = 3
TDDA_MINOR_VERSION = 3
TDDA_EDIT = 0
TDDA_VERSION_QUALIFIER = ''
TDDA_ZERO_VERSION = '0.0.0'  # used for some reference test results.
TDDA_VERSION = '%d.%d.%02d%s' % (
    TDDA_MAJOR_VERSION,
    TDDA_MINOR_VERSION,
    TDDA_EDIT,
    TDDA_VERSION_QUALIFIER,
)
version = TDDA_VERSION


def writable_version():
    from tdda.state import get_testing

    return TDDA_ZERO_VERSION if get_testing() else version


if __name__ == '__main__':
    print(version)
