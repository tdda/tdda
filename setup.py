import os
from setuptools import setup, find_packages

# version import is from tdda subdirectory here, not from some other install.
from tdda.version import version as __version__

def read(fname):
    # read contents of file
    return open(os.path.join(os.path.dirname(__file__), fname)).read()

def data(path, pathitems, exclusions=None):
    # build list of additional files to package up from a subdirectory
    names = []
    for relpath in pathitems:
        subpath = path + [relpath]
        dirname = os.path.join(*subpath)
        for name in os.listdir(dirname):
            if exclusions and name in exclusions:
                continue
            pathname = os.path.join(relpath, name)
            fullpathname = os.path.join(dirname, name)
            if os.path.isdir(fullpathname):
                names.extend(data(path, [pathname]))
            else:
                names.append(pathname)
    return names

setup(
    name='tdda',
    version=__version__,
    description='Test Driven Data Analysis',
    long_description=read('README.md'),
    author='Stochastic Solutions Limited',
    author_email='info@StochasticSolutions.com',
    license='MIT',
    url='http://www.stochasticsolutions.com',
    download_url='https://github.com/tdda/tdda',
    keywords='tdda constraint referencetest rexpy',
    packages=find_packages(),
    package_data={
        'tdda.referencetest': data(['tdda', 'referencetest'], ['examples']),
        'tdda.referencetest.tests': data(['tdda', 'referencetest', 'tests'],
                                         ['testdata']),
        'tdda.constraints': data(['tdda', 'constraints'],
                                 ['testdata', 'examples'],
                                 exclusions=['accounts1k.csv',
                                             'accounts25k.csv'])
                            + ['tdda_json_file_format.md'],
        'tdda.rexpy': data(['tdda', 'rexpy'], ['examples']),
        'tdda.gentest': data(['tdda', 'gentest'], ['examples']),
        'tdda': ['README.md', 'LICENSE.txt'],
    },
    entry_points = {
        'console_scripts': [
            'tdda = tdda.constraints.console:main',
            'rexpy = tdda.rexpy.rexpy:main',
        ],
    },
    zip_safe=False,
    install_requires=['numpy>=1.20.3', 'pandas>=1.5.2'],
)

