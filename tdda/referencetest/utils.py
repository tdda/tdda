import fnmatch
import json
import os
import re
import sys
import yaml

try:
    from yaml import CLoader as YAMLLoader, CDumper as YAMLDumper
except ImportError:
    from yaml import Loader as YAMLLoader, Dumper as YAMLDumper


import chardet

import pandas as pd
import polars as pl

from tdda.utils import TDDAError, error

MIN_CHARDET_CONFIDENCE = 0.5


class FileType:
    BINARY_IMAGES = ('png', 'jpeg', 'jpg', 'gif', 'ps', 'eps', 'eps')
    TEXT_IMAGES = ('svg', 'ps', 'eps', 'pdf')  # pdf isn't, strictly, but...
    TEXT_FLAT_FILES = ('csv', 'tsv', 'psv')
    OTHER_TEXTS = (
        'txt',
        'tex',
        'md',
        'markdown',
        'rst',
        'texhtml',
        'htm',
        'css',
        'js',
        'json',
        'xml',
        'yaml',
        'sh',
        'py',
        'R',
        'sql',
    )
    TEXT_FILES = TEXT_IMAGES + TEXT_FLAT_FILES + OTHER_TEXTS
    IMAGE_FILES = BINARY_IMAGES + TEXT_IMAGES

    def __init__(self, path):
        self.orig_path = path
        self.ext = get_short_ext(path)
        name = os.path.basename(path)

        self.binary = self.ext in self.BINARY_IMAGES
        self.text = self.ext in self.TEXT_FILES or name == 'Makefile'
        self.image = self.ext in self.IMAGE_FILES
        self.encoding = 'iso-8859-1' if self.ext == 'pdf' else None
        if not self.image and not self.binary:
            if self.ext == 'pdf':
                self.encoding = 'iso-8859-1'
            else:
                detector = chardet.UniversalDetector()
                with open(path, 'rb') as f:
                    for line in f.readlines():
                        detector.feed(line)
                        if detector.done:
                            break
                detector.close()
                confidence = detector.result.get('confidence', 0.0)
                if confidence > MIN_CHARDET_CONFIDENCE:
                    self.encoding = detector.result.get('encoding')
                    self.text = True
                else:
                    self.binary = True
        self.orig_encoding = self.encoding  # encoding might be modified

    def is_unknown(self):
        return not self.binary and not self.text


def guess_encoding(path):
    ext = get_short_ext(path)
    if ext == 'pdf':
        return 'iso-8859-1'
    return 'utf-8'


def normalize_encoding(encoding):
    lc = encoding.lower()
    return 'utf-8' if lc == 'utf8' else lc


def get_encoding(path, encoding=None):
    if encoding is None:
        return guess_encoding(path)
    else:
        return normalize_encoding(encoding)


def get_short_ext(path):
    """Returns path extension, with dot removed"""
    return os.path.splitext(path)[1].lower()[1:] if path else ''


def protected_readlines(path, filetype):
    """
    Attempts to read path base on information in filetype.

    If the file is binary, return None

    If the file can't be read using the filetype
    """
    filetype = filetype or FileType(path)
    if filetype.binary:
        return
    enc = filetype.encoding if filetype else None
    try:
        with open(path, encoding=enc) as f:
            return f.readlines()
        if filetype.is_unknown():
            filetype.text = True
    except UnicodeDecodeError:
        if filetype.text:  # really was expecting text
            try:
                with open(path, encoding='iso-8859-1') as f:
                    lines = f.readlines()
                    filetype.encoding = 'iso-8859-1'
                    return lines
            except UnicodeDecodeError:
                filetype.binary = True
                filetype.text = False
                filetype.encoding = None
                print(
                    'Could not read %s as text file; treating as binary'
                    % path,
                    file=sys.stderr,
                )


def normabspath(p):
    return os.path.normpath(os.path.abspath(p))


# Helper functions for reference testing of JSON and YAML


def normalize_json(s, remove_keys=None):
    """
    Take a JSON string and normalize it by
    indenting consistently and sorting dictionary keys.
    If an iterable remove_keys is provided, remove all
    specified keys from all dictionaries in lines.

    The JSON can be provided as a string or as a list of lines.
    """
    if isinstance(s, list):
        s = '\n'.join(s)  # lines from .splitlines()
    obj = json.loads(s)
    if remove_keys:
        obj = remove_dict_keys(obj, set(remove_keys))
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False)


def normalize_yaml(s, remove_keys=None):
    """
    Take a YAML string and normalize it by
    indenting consistently and sorting dictionary keys.
    If an iterable remove_keys is provided, remove all
    specified keys from all dictionaries in lines.

    The JSON can be provided as a string or as a list of lines.
    """
    if isinstance(s, list):
        s = '\n'.join(s)  # lines from .splitlines()
    obj = yaml.load(s, Loader=YAMLLoader)
    if remove_keys:
        obj = remove_dict_keys(obj, set(remove_keys or []))
    return yaml.dump(obj, indent=2, sort_keys=True, allow_unicode=True)


def remove_dict_keys(o, keys):
    """
    Remove any keys from o if o is a dictionary and recurse.
    """
    if isinstance(o, dict):
        return {
            k: remove_dict_keys(v, keys) for k, v in o.items() if k not in keys
        }
    elif isinstance(o, list) or isinstance(o, tuple):
        return [remove_dict_keys(v, keys) for v in o]
    else:
        return o


def remove_dict_keys_and_sort(o, keys):
    """
    Remove any keys from o if o is a dictionary and recurse.
    """
    if isinstance(o, dict):
        return {
            k: remove_dict_keys_and_sort(v, keys)
            for k, v in sorted(o.items())
            if k not in keys
        }
    elif isinstance(o, list) or isinstance(o, tuple):
        return [remove_dict_keys_and_sort(v, keys) for v in o]
    else:
        return o


def _norm_path_string(s):
    """Normalise a single path string from Windows to POSIX style."""
    s = re.sub(r'[A-Za-z]:\\', '/', s)
    return s.replace('\\', '/')


def _norm_paths_in_obj(obj, norm_paths, key=None):
    """Recursively normalise path strings in a parsed JSON object."""
    if norm_paths is True:
        key_matches = True
    else:
        patterns = (
            [norm_paths] if isinstance(norm_paths, str) else list(norm_paths)
        )
        key_matches = key is not None and any(
            fnmatch.fnmatch(key, p) for p in patterns
        )

    if isinstance(obj, dict):
        return {
            k: _norm_paths_in_obj(v, norm_paths, key=k)
            for k, v in obj.items()
        }
    elif isinstance(obj, (list, tuple)):
        return [_norm_paths_in_obj(v, norm_paths, key=key) for v in obj]
    elif isinstance(obj, str) and key_matches:
        return _norm_path_string(obj)
    else:
        return obj


def apply_preprocess(x, xforms):
    """Apply one or more transformation functions to x, left to right.

    Args:
        x: The value to transform.
        xforms: A callable or list of callables to apply in sequence.
    """
    if xforms is None:
        return x
    if callable(xforms):
        return xforms(x)
    for f in xforms:
        x = f(x)
    return x


def to_posix_newlines(s):
    """Convert Windows line endings to Unix in a string."""
    return s.replace('\r\n', '\n')


def normalize_json_for_comparison(lines, remove_keys=None, norm_paths=None,
                                   preprocess=None):
    """Normalize JSON for comparison.

    Applies user preprocessing, then parses, applies structural transforms
    (remove_keys, norm_paths), and re-serializes with sorted keys, 2-space
    indent, and Unicode preserved.

    Args:
        lines: JSON as a string or list of lines.
        remove_keys: Optional set/list of key names to remove at any depth.
        norm_paths: If `True`, normalise Windows paths in all string values.
            If a string or list of strings, treat as fnmatch key globs.
        preprocess: Optional function or list of functions applied to the
            JSON string before parsing. If a list `[f, g]` is given,
            `g(f(·))` is computed, where `·` is the JSON string.
    """
    s = '\n'.join(lines) if isinstance(lines, list) else lines
    s = apply_preprocess(s, preprocess)
    obj = json.loads(s)
    if remove_keys:
        obj = remove_dict_keys(obj, set(remove_keys))
    serialized = json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False)
    if norm_paths:
        serialized = norm_paths_in_json(serialized, norm_paths)
    return serialized.splitlines()


def norm_paths_in_json(s, norm_paths):
    """Normalise path strings in a JSON string.

    Parses the JSON, applies path normalisation to string values, and
    returns the result as a normalized JSON string (sorted keys, 2-space
    indent, unicode preserved).

    Args:
        s: A JSON string or list of lines.
        norm_paths: `True` to normalise all string values, or a string/list
            of fnmatch-style key globs to restrict normalisation to values
            of matching keys.
    """
    if isinstance(s, list):
        s = '\n'.join(s)
    obj = json.loads(s)
    obj = _norm_paths_in_obj(obj, norm_paths)
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=False)


def diffcmd():
    return 'fc' if os.name and os.name != 'posix' else 'diff'


def copycmd():
    return 'copy' if os.name and os.name != 'posix' else 'cp'


_HEAVY_TO_LIGHT = str.maketrans('┏━┳┓┃┡╇┩', '┌─┬┐│├┼┤')


def normalise_rich_table(s):
    """
    Normalise Rich table box-drawing characters by mapping heavy header
    border chars to their light equivalents. Useful as a preprocess
    function when comparing Rich table output across platforms.
    """
    if isinstance(s, list):
        return [line.translate(_HEAVY_TO_LIGHT) for line in s]
    return s.translate(_HEAVY_TO_LIGHT)


def diff_parquet_pattern():
    """
    Returns a regex pattern that matches the 'Compare with:' diff command
    line in DataFrame comparison output, for either 'diff' (Unix/Mac) or
    'fc' (Windows).
    """
    cmds = '|'.join({'diff', diffcmd()})
    return (r'(%s) .*/actual-df[0-9]+\.parquet'
            r' .*/expected-df[0-9]+\.parquet') % cmds


def json_normalizer(remove_keys=None):
    """
    Returns a JSON normalizer with key removal
    (if remove_keys are supplied).
    """
    if remove_keys is None:
        return normalize_json
    else:
        return lambda s: normalize_json(s, remove_keys=remove_keys)


def yaml_normalizer(remove_keys=None):
    """
    Returns a YAML normalizer with key removal
    (if remove_keys are supplied).
    """
    if remove_keys is None:
        return normalize_yaml
    else:
        return lambda s: normalize_yaml(s, remove_keys=remove_keys)
