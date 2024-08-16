import json
import math
import os

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

    def to_dict(self, pc=True, raw=False, total_values=False):
        d = {
            'n_passes': self.n_passes,
            'n_failures': self.n_failures,
        }
        if total_values:
            d[f'n_{self.items}'] = self.n_passes + self.n_failures,

        if raw:
            d.update({
                'pass_rate': self.pass_rate,
                'failure_rate': self.failure_rate
            })
        if pc:
            d.update({
                'pass_pc': to_pc(self.pass_rate),
                'failure_pc': to_pc(self.failure_rate)
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

    Return (new path, changed)

    where changed is True iff the old and new extensions are different
    """
    base, ext = os.path.splitext(path)
    return base + new_ext, new_ext != ext


def dict_to_json(d):
    return strip_lines(json.dumps(d, indent=4, ensure_ascii=False)) + '\n'


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
