import json
import os
import sys

from tdda.serial.pandasio import gen_pandas_kwargs


USAGE = '''
python cli.py [[foo-metadata.json] [output.py]]

python cli.py
       prints this usage information

python cli.py foo-metadata.json
       prints the Python representation of kwargs
       for pandas from csvw file foo.json

python cli.py foo-metadata.json foo.py
       writes foo.py, defining a dictionary with kwargs
       for pandas read_csv correspending to foo-metadata.json

'''


def fmt(d):
    return json.dumps(d, indent=4)


def error(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def write_pandas_kwargs(inpath, outpath):
    """
    Write the python defining kwargs to outpath based on the
    CSVW file at inpath.
    """
    if os.path.exists(os.path.dirname(outpath)):
        with open(outpath, 'w') as f:
            out = fmt(gen_pandas_kwargs(inpath))
            f.write(f'pd_kwargs = {out}\n')
    else:
        error(f'Directory {os.path.dirname(outpath)} not found.')


if __name__ == '__main__':
    if len(sys.argv) in (2, 3):
        inpath = sys.argv[1]
        if not os.path.exists(inpath):
            error(f'Directory {os.path.dirname(inpath)} not found.')

        if len(sys.argv) == 2:
            print(fmt(gen_pandas_kwargs(inpath)))
        else:
            write_pandas_kwargs(inpath, sys.argv[2])

    else:
        print(USAGE, file=sys.stderr)
        sys.exit(0 if len(sys.argv) == 1 else 1)
