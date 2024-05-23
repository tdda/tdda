import json
import os
import requests
import sys

from collections import Counter

BASEURL = 'https://w3c.github.io/csvw/tests'
CSVW_TEST_DIR = '../testdata/csvw'
N_TESTS = 270

def get_val(keyname, lines):
    key, val = lines.pop(), lines.pop()
    if not key == keyname:
        print(f'"{keyname}" != "{key}" (val: "{val}")')
        sys.exit(1)
    return val


def get_pair(lines):
    key = lines.pop() if lines else None
    val = lines.pop() if lines else ''
    return key, val


def parse(outpath):

    with open('csvw-tests-raw.txt') as f:
        lines = f.readlines()
    lines = [line.strip() for line in reversed(lines)]

    d = {}

    n = 0
    line = lines.pop()
    while lines and n < N_TESTS:
        entry = {}
        if line.startswith('manifest-json#'):
            rest = line.split('#')[1]
            number, name = [v.strip() for v in rest.split(':', 1)]
            entry['number'] = number
            entry['name'] = name
            entry['desc'] = lines.pop()
            notes = []
            line = lines.pop()
            while line != 'type':
                notes.append(line)
                line = lines.pop()
            entry['notes'] = '\n'.join(notes)
            entry['type'] = lines.pop()
            entry['approval'] = get_val('approval', lines)
            entry['action'] = get_val('action', lines)
            while True:
                key, val = get_pair(lines)
                if key is None or key.startswith('manifest-json#'):
                    line = key
                    break
                entry[key] = val
            d[number] = entry
            n += 1

    assert n == N_TESTS
    with open(outpath, 'w') as f:
        json.dump(d, f, indent=4)
    print(f'Written {outpath}.')
    return d


def download(details):
    if not os.path.exists(CSVW_TEST_DIR):
        os.makedirs(CSVW_TEST_DIR)
    dirs = Counter()
    failures = []
    for i, (test, d) in enumerate(details.items(), 1):
        print(i, test)
        for kind in ('action', 'result', 'Implicit'):
            if pathspec := d.get(kind):
                for path in pathspec.split(' '):
                    url = os.path.join(BASEURL, path)
                    r = requests.get(url)
                    directory = os.path.dirname(path)
                    if directory:
                        physical = os.path.join(CSVW_TEST_DIR, directory)
                        if not directory in dirs:
                            if not os.path.exists(physical):
                                os.makedirs(physical)
                                print(f'Created {physical}.')
                        dirs[directory] += 1
                    if r.status_code == 200:
                        with open(os.path.join(CSVW_TEST_DIR, path), 'w') as f:
                            f.write(r.text)
                    else:
                        print(f'Failed to download {url}.', file=sys.stderr)
                        failures.append(url)
    print('\nDirectories:')
    for k, v in dirs.items():
        print(v, k)
    if failures:
        print('\nDOWNLOAD FAILURES:')
        for url in failures:
            print(f'Failed to download {url}.', file=sys.stderr)
    else:
        print('\nNo download failures.')


if __name__ == '__main__':
    d = parse('csvwtests.json')
    download(d)

