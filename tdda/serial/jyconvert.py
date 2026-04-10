import json
import os
import sys

from tdda.serial.frictionless import (
    isyaml,
    load_json_or_yaml,
    write_json_or_yaml,
)
from tdda.utils import error, swap_ext


def main(*paths):
    if not args:
        error('Usage: jyconvert foo.[yaml|json]')
    for path in args:
        d = load_json_or_yaml(path)
        if isyaml(path):
            outpath = swap_ext(path, 'json')
        else:
            outpath = swap_ext(path, 'yaml')
        write_json_or_yaml(d, outpath, verbose=True)


if __name__ == '__main__':
    args = sys.argv[1:]
    main(*args)
