import json
import math
import os
import re
import regex
import yaml
import tomli_w

from collections import namedtuple

import numpy as np

class PassFailStats:
    def __init__(self, passes, failures, items='records'):
        self.items = items
        self.n_passes = passes
        self.n_failures = failures
        denom = max(1, passes + failures)
        self.pass_rate = passes / denom
        self.failure_rate = failures / denom

    def to_dict(self, pc=True, total_values=False):
        d = {
            'n_passes': self.n_passes,
            'n_failures': self.n_failures,
        }
        if total_values:
            d[f'n_{self.items}'] = self.n_passes + self.n_failures,

        if pc:
            d.update({
                'pass_rate': to_pc(self.pass_rate),
                'failure_rate': to_pc(self.failure_rate)
            })
        return d

def nvl(v, w):
    """
    This function is used as syntactic sugar for replacing null values.
    """
    return w if v is None else v


def swap_ext(path, new_ext):
    """
    Replaces the extension of path to new_ext
    """
    base, ext = os.path.splitext(path)
    return base + new_ext


def swap_ext_q(path, new_ext):
    """
    Replaces the extension of path to new_ext

    Return (new path, changed)

    where changed is True iff the old and new extensions are different
    """
    outpath = swap_ext(path, new_ext)
    _, ext = os.path.splitext(path)
    _, new_ext = os.path.splitext(outpath)
    return outpath, new_ext != ext


def dict_to_json(d, path=None):
    """
    Dumps appropriately formatted version of dictionary d to JSON.
    If path is given, it goes there; otherwise, the JSON is returned.
    """
    json_text = strip_lines(json.dumps(d, indent=4, ensure_ascii=False)) + '\n'
    if path:
        with open(path, 'w') as f:
            f.write(json_text)
    else:
        return json_text


def dict_to_yaml(d, path=None):
    """
    Dumps appropriately formatted version of dictionary d to YAML.
    If path is given, it goes there; otherwise, the YAML is returned.
    """
    if path:
        with open(path, 'w') as f:
            yaml.dump(d, f)
    else:
        return yaml.dump(d)


def dict_to_toml(d, path=None):
    """
    Dumps appropriately formatted version of dictionary d to JSON.
    If path is given, it goes there; otherwise, the JSON is returned.
    """
    if path:
        with open(path, 'wb') as f:
            tomli_w.dump(d, f)
    else:
        return tomli_w.dumps(d)


def json_sanitize(v):
    if v is np.nan:
        return None
    elif v is None or type(v) in (str, int, float, bool):
        return v
    elif type(v) in (list, tuple):
        return [json_sanitize(u) for u in v]
    elif isinstance(v, dict):
        return {str(k): str(u) for k, u in v.items()}
    else:
        s = str(v)
        return s[:-9] if s.endswith('00:00:00') else s  # slightly dodgy


def strip_lines(s):
    """
    Splits the given string into lines (at newlines), strips trailing
    whitespace from each line before rejoining.

    Is careful about last newline.
    """
    end = '\n' if s.endswith('\n') else ''
    return '\n'.join([line.rstrip() for line in s.splitlines()]) + end


def ok_field_name(field, constraint, name_map=None):
    if name_map:
        return f'{field}_{name_map[constraint]}_ok'
    else:
        return f'{field}_{constraint}_ok'


def pass_fail_stats(passes, failures, items='cases'):
    return PassFailStats(passes, failures, items=items)


def to_pc(v, mindp=2):
    pc = 100 * v
    delta = 5 * pow(10, -mindp - 1)
    if pc in (0, 100) or ((100 - pc > delta) and pc > delta):
        return f'{v * 100:.2f}%'  # won't be 100.00% or 0.00% if not exact

    threshold = 100 - pc if (pc > delta) else pc
    dps = -math.log10(threshold)
    lo_dps = int(dps)
    hi_dps = lo_dps + 1
    lo_fmt = '%%.%df' % lo_dps
    small = lo_fmt % pc
    i, f = small.split('.')
    if i == 100 or f == '0' * len(f):
        hi_fmt = '%%.%df' % hi_dps
        return f'{hi_fmt % pc}%'
    else:
        return f'{small}%'


def print_obj(o, rex=None, invert=False, as_repr=False, keys_only=False):
    """
    Print the __dict__ from o in the form:

        key (type(value)): value

    If rex is provided, print only keys matching rex.

    If invert is set to True, use rex to exclude rather than include keys.

    If as_repr is set, use repr(.) instead of str(.) for formatting value.
    """
    if rex:
        r = re.compile(rex) if rex else None
        if invert:
            for k, v in o.__dict__.items():
                if not re.match(r, k):
                    print_item(k, v, as_repr, keys_only)
        else:
            for k, v in o.__dict__.items():
                if re.match(r, k):
                    print_item(k, v, as_repr, keys_only)
    else:
        for k, v in o.__dict__.items():
            print_item(k, v, as_repr, keys_only)


def print_item(k, v, as_repr=False, keys_only=False):
    f = repr if as_repr else lambda x: x
    if keys_only:
        print(f'{k} ({type(v)})')
    else:
        print(f'{k} ({type(v)}): {f(v)}')


def n_glyphs(s):
    """
    Returns the number of glyphs in a string.
    """
    return len(regex.findall(r'\X', s))

