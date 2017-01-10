import os
from setuptools import setup, find_packages
from tdda import __version__

packages = find_packages()

def package_files():
    paths = {}
    top_packages = [p for p in packages if not '.' in p]
    for package in top_packages:
        paths[package] = []
        for (path, subdirectories, filenames) in os.walk(package):
            path = path[len(package) + len(os.path.sep):]
            if not path or '.cache' in path:
                continue
            for filename in filenames:
                if not filename.endswith('.py'):
                    paths[package].append(os.path.join(path, filename))
    return paths

setup(
    name = 'tdda',
    version = __version__,
    author = 'Stochastic Solutions Limited',
    description = 'Test Driven Data Analysis',
    license = 'MIT',
    url = 'http://www.stochasticsolutions.com',
    keywords = 'tdda constraint referencetest rexpy',
    packages = packages,
    package_data = package_files(),
)

