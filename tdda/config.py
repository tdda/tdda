import datetime
import json
import os
import re
import sys

try:
    import tomllib
except ImportError:
    import tomli as tomllib
import json

import pandas as pd


DATETIME_RE = '^[0-9]{4}-[0-9]{2}-[0-9]{2}([T ][0-9]{2}:[0-9]{2}:[0-9]{2})?$'

DEFAULT_IN_METADATA = './_write.serial'

COLOUR_DOC = (
    'A named ANSI colour (red, bright_red etc.) or an RGB '
    'hex colour with leading # such as #FF0000 for pure red. '
    'Interpreted by the rich library.'
)


class ParamDoc:
    def __init__(self, doc, values=None, regex=None, allowed_doc=None):
        self.doc = doc
        self.values = values
        self.regex = regex
        self.allowed_doc = allowed_doc


class BaseConfig:
    def override(self, d, complain):
        for k, v in d.items():
            if k in self.__dict__ and not k.startswith('_'):
                self.__dict__[k] = v
            elif complain:
                part = self._part
                print(
                    f'Unknown configuration parameter {k} '
                    f'ignored{(" " + part) if part else ""}.',
                    file=sys.stderr,
                )

    def __str__(self):
        out = ['# TDDA Configuration\n']
        for k, v in self.__dict__.items():
            if isinstance(v, BaseConfig):
                out.append(v._section_str())
            elif not k.startswith('_'):
                out.append(fmt_kv(k, v))
        return '\n'.join(out)

    def _section_str(self):
        out = [f'\n\n[{self._part}]\n']
        for k, v in self.__dict__.items():
            if not k.startswith('_'):
                out.append(fmt_kv(k, v))
        return '\n'.join(out)

    def annotated_str(self):
        out = ['# TDDA Configuration\n']
        for k, v in self.__dict__.items():
            if isinstance(v, BaseConfig):
                out.append(v._annotated_section_str())
            elif not k.startswith('_'):
                doc = self.__dict__.get(f'_doc_{k}')
                out.append(fmt_annotated_kv(k, v, doc))
        return '\n'.join(out)

    def _annotated_section_str(self):
        out = [f'\n\n[{self._part}]\n']
        for k, v in self.__dict__.items():
            if not k.startswith('_'):
                doc = self.__dict__.get(f'_doc_{k}')
                out.append(fmt_annotated_kv(k, v, doc))
        return '\n'.join(out)

    def get(self, key, preferred=None, raiseOnFailure=True):
        """
        Get the appropriate value for key as follows:

        1. preferred is used if it is a scalar other than None.

        2. if preferred is a dictionary, and key is a non-None value
           in the dictionary, that is used.

        3. otherwise, the value in the Config object is returned.

        If no non-None value is found anywhere, an error is raised
        unless raiseOnFailure is set to False.
        """
        if preferred is not None:
            if isinstance(preferred, dict):
                v = preferred.get(key, None)
                if v is not None:
                    return v
            else:
                return preferred
        if hasattr(self, key):
            return getattr(self, key)
        if raiseOnFailure:
            raise AttributeError(f'No attribute {key} in {self._config_name}')
        else:
            return None


class Config(BaseConfig):
    def __init__(self, load=None, testing=None, complain=True):
        env = os.environ
        self._part = ''
        self._config_name = 'config'
        self.null_rep = '∅'
        self._doc_null_rep = ParamDoc(
            doc='Used to show nulls in some contexts.',
            regex=r'.*',
        )
        self.colour = not testing
        self._doc_colour = ParamDoc(
            doc='Controls whether output is colourized.',
            values=[True, False],
        )
        self.engine = 'pandas'
        self._doc_engine = ParamDoc(
            doc=(
                'Controls whether pandas or polars is used for CSV '
                'files by default.'
            ),
            values=['pandas', 'polars'],
        )
        self.pandas_backend = 'numpy_nullable'
        self._doc_pandas_backend = ParamDoc(
            doc='Controls default backend for CSV loading etc.',
            values={
                'n': 'numpy_nullable',
                'a': 'pyarrow',
                'o': 'original',
            },
        )

        self.referencetest = ReferenceTestConfig()
        self.constraints = ConstraintsConfig()
        self.tddadiff = TDDADiffConfig()
        self.serial = SerialConfig()
        if not testing and (load or load is None):
            self.load(complain=complain)

    def load(self, complain=True):
        config_path = cross_platform_dot_file('~/.tdda.toml')
        if os.path.exists(config_path):
            with open(config_path, 'rb') as f:
                d = tomllib.load(f)
                rc = d.get('referencetest', None)
                if rc:
                    self.referencetest.override(rc, complain)
                cc = d.get('constraints', None)
                if cc:
                    self.constraints.override(cc, complain)
                if 'referencetest' in d:
                    del d['referencetest']
                if 'constraints' in d:
                    del d['constraints']
                self.override(d, complain)

    def format_failure_values(self, failure):
        if len(failure) == 1:
            return self.format_value(failure[0])
        else:
            keys = ', '.join(self.format_value(k) for k in failure[:-1])
            return f'{keys}: {self.format_value(failure[-1])}'

    def format_value(self, v):
        if isinstance(v, list) or isinstance(v, tuple):
            return f'[{(self.format_value(V) for V in v)}]'
        if pd.isnull(v):
            return self.null_rep
        if type(v) is str:
            m = re.match(DATETIME_RE, v)
            if m:
                return v[:10] if m.group(1) else v
        if type(v) is datetime.datetime:
            s = v.isoformat('T', timespec='seconds')
            return s[:10] if v.hour or v.minute or v.second else s
        return repr(v)

    def format_constraint_value(
        self, value, start_col, indent, max_width=79, tabsize=2, rex=False
    ):
        if not isinstance(value, list) and not isinstance(value, tuple):
            return self.format_value(value)
        if len(value) == 1:
            if rex:
                return self.format_value(value[0]).strip("'")
            else:
                return self.format_value(value[0])

        s = self.format_value(value)

        if len(s) + start_col <= max_width:
            return s

        formatted = [self.format_value(v) for v in value]
        if rex:
            formatted = [v.strip("'") for v in formatted]
        lines = []
        width = max_width - indent - tabsize
        items = []
        for v in formatted:
            items.append(v)
            line = f'{", ".join(items)}'
            if len(line) > width:
                if len(items) > 1:
                    lines.append(f'{", ".join(items[:-1])}')
                    items = items[-1:]
                else:
                    lines.append(items[0])
        if items:
            lines.append(f'{", ".join(items)}')
        item_indent = ' ' * (indent + tabsize)
        close_indent = ' ' * (indent)
        item_joint = f',\n{item_indent}'
        item_joint = f',\n{item_indent}'
        return f'\n{item_indent}{item_joint.join(lines)}'


class ReferenceTestConfig(BaseConfig):
    def __init__(self):
        self._part = 'referencetest'
        self._config_name = 'config.referencetest'
        self.left_colour = 'red'
        self._doc_left_colour = ParamDoc(
            doc='Colour for left (actual) side of diffs.',
            allowed_doc=COLOUR_DOC,
        )
        self.right_colour = 'green'
        self._doc_right_colour = ParamDoc(
            doc='Colour for right (expected) side of diffs.',
            allowed_doc=COLOUR_DOC,
        )
        self.failure_colour = 'red'
        self._doc_failure_colour = ParamDoc(
            doc='Colour used to highlight failures.',
            allowed_doc=COLOUR_DOC,
        )
        self.mono = False
        self._doc_mono = ParamDoc(
            doc='Use bold instead of colour for diffs.',
            values=[True, False],
        )
        self.bw = False
        self._doc_bw = ParamDoc(
            doc='Black and white mode: no colour or bold.',
            values=[True, False],
        )
        self.left_prefix = '< '
        self._doc_left_prefix = ParamDoc(
            doc='Prefix string for left (actual) diff lines.',
            regex=r'.*',
        )
        self.right_prefix = '> '
        self._doc_right_prefix = ParamDoc(
            doc='Prefix string for right (expected) diff lines.',
            regex=r'.*',
        )
        self.vertical = False
        self._doc_vertical = ParamDoc(
            doc='Show diffs vertically rather than side by side.',
            values=[True, False],
        )
        self.force_val_prefixes = False
        self._doc_force_val_prefixes = ParamDoc(
            doc='Always show left/right prefixes on diff lines.',
            values=[True, False],
        )
        self.type_checking = 'strict'
        self._doc_type_checking = ParamDoc(
            doc='How strictly to check types in reference test comparisons.',
            values=['strict', 'medium', 'loose'],
        )
        self.log_failures = False
        self._doc_log_failures = ParamDoc(
            doc='Log failing test IDs to file for use with tdda tag.',
            values=[True, False],
        )

    def left_diff(self, value, force_prefix=None):
        annotated = self.left_annotated(value, force_prefix)
        if self.bw or self.mono:
            return f'[bold]{annotated}[/bold]'
        else:
            colour = self.left_colour
            return f'[{colour}]{annotated}[/{colour}]'

    def right_diff(self, value, force_prefix=None):
        annotated = self.right_annotated(value, force_prefix)
        if self.bw or self.mono:
            return f'[bold]{annotated}[/bold]'
        else:
            colour = self.right_colour
            return f'[{colour}]{annotated}[/{colour}]'

    def left_annotated(self, value, force_prefix=None):
        prefix = self.left_prefix if force_prefix else ''
        return f'{prefix}{value}'

    def right_annotated(self, value, force_prefix=None):
        prefix = self.right_prefix if force_prefix else ''
        return f'{prefix}{value}'

    def common(self, value, dim_if_not_bw=False, plain=False):
        if (not plain) and (self.mono or (dim_if_not_bw and not self.bw)):
            return f'[dim]{value}[/dim]'
        else:
            return str(value)

    def format_failure(self, content):
        if self.bw or self.mono:
            return f'[bold]{content}[/bold]'
        else:
            colour = self.failure_colour
            return f'[{colour}]{content}[/{colour}]'

    def set_colours(self, left, right):
        self.left_colour, self.right_colour = left.lower(), right.lower()
        # possibly validate

    def set_prefixes(self, left, right):
        self.left_prefix, self.right_prefix = left, right
        # possibly validate

    def stripped_prefixes(self, pre='\n'):
        return (
            pre + self.left_prefix.strip().replace(':', ''),
            pre + self.right_prefix.strip().replace(':', ''),
        )


class ConstraintsConfig(BaseConfig):
    def __init__(self):
        self._part = 'constraints'
        self._config_name = 'config.constraints'

        self.interleave = True
        self._doc_interleave = ParamDoc(
            doc='Interleave pass and fail results in verify output.',
            values=[True, False],
        )
        self.per_constraint = True
        self._doc_per_constraint = ParamDoc(
            doc='Report results per constraint rather than per field.',
            values=[True, False],
        )
        self.detect_passes = True  # ok fields. False for _bad fields
        self._doc_detect_passes = ParamDoc(
            doc='Include passing fields in detect output.',
            values=[True, False],
        )
        self.report_formats = []
        self._doc_report_formats = ParamDoc(
            doc='List of additional report formats to generate.',
            values=['html', 'md', 'txt', 'json', 'yaml', 'toml'],
        )
        self.write_all_records = False
        self._doc_write_all_records = ParamDoc(
            doc='Write all records to detect output, not just failures.',
            values=[True, False],
        )
        self.int_bools = False
        self._doc_int_bools = ParamDoc(
            doc='Use integers (0/1) rather than booleans in detect output.',
            values=[True, False],
        )
        self.verify_required_fields = None
        self._doc_verify_required_fields = ParamDoc(
            doc='Verify that all required fields are present.',
            values=[True, False],
        )
        self.verify_allowed_fields = None
        self._doc_verify_allowed_fields = ParamDoc(
            doc='Verify that no fields are present outside the allowed set.',
            values=[True, False],
        )
        self.write_required_fields = False
        self._doc_write_required_fields = ParamDoc(
            doc='Discover should include the required-fields constraint.',
            values=[True, False],
        )
        self.write_allowed_fields = False
        self._doc_write_allowed_fields = ParamDoc(
            doc='Discover should include an allowed-fields constraint.',
            values=[True, False],
        )


class TDDADiffConfig(BaseConfig):
    def __init__(self):
        self._part = 'tddadiff'
        self._config_name = 'config.tddadiff'

        self.type_checking = 'medium'
        self._doc_type_checking = ParamDoc(
            doc='How strictly to check types when comparing dataframes.',
            values=['strict', 'medium', 'loose'],
        )
        self.find_md = False
        self._doc_find_md = ParamDoc(
            doc='Find associated metadata when comparing dataframes with tdda diff.',
            values=[True, False],
        )


class SerialConfig(BaseConfig):
    def __init__(self):
        self._part = 'serial'
        self._config_name = 'config.serial'

        self.md_inpath = [DEFAULT_IN_METADATA]  # list/single dir/None
        self._doc_md_inpath = ParamDoc(
            doc=(
                'Path(s) to search for serial metadata files; '
                'relative paths are resolved relative to the CSV file.'
            ),
        )

    def _get_inpath_list(self, csvpath=None):
        path = self.md_inpath
        paths = [path] if isinstance(path, str) else (path or [])
        paths = [
            os.path.normpath(os.path.expanduser(p))
            if p.startswith('~')
            else os.path.expanduser(p)
            for p in paths
        ]
        if csvpath:
            dir_ = os.path.dirname(os.path.abspath(csvpath))
            paths = [
                p
                if os.path.isabs(p)
                else os.path.join(dir_, os.path.basename(p))
                for p in paths
            ]
        return paths

    def _md_inpath(self, csvpath=None):
        paths = self._get_inpath_list(csvpath)
        for p in paths:
            if os.path.exists(p):
                return p
        return None


def _invert_alias_dict(d):
    result = {}
    for alias, canonical in d.items():
        result.setdefault(canonical, []).append(alias)
    return result


def fmt_allowed(value, doc):
    """Return the allowed-values comment string, or None if no comment."""
    if doc is None:
        return None
    if doc.allowed_doc:
        return doc.allowed_doc
    if doc.regex:
        return None
    if doc.values is None:
        return None
    if isinstance(doc.values, dict):
        inverted = _invert_alias_dict(doc.values)
        groups = []
        for canonical, aliases in inverted.items():
            parts = (
                [json.dumps(canonical, ensure_ascii=False)]
                + [json.dumps(a, ensure_ascii=False) for a in aliases]
            )
            groups.append(' / '.join(parts))
        return '; '.join(groups)
    elif isinstance(value, list):
        items = ', '.join(
            json.dumps(v, ensure_ascii=False) for v in doc.values
        )
        return f'any subset of: {items}'
    else:
        parts = []
        for v in doc.values:
            if isinstance(v, bool):
                parts.append(str(v).lower())
            else:
                parts.append(json.dumps(v, ensure_ascii=False))
        return '; '.join(parts)


MIN_COMMENT_COL = 36


def _wrap_comment(base, allowed, sep, max_width=79):
    """Wrap 'base  # allowed' to max_width, returning multi-line string."""
    hash_col = max(MIN_COMMENT_COL, len(base) + 2)
    padding = ' ' * (hash_col - len(base))
    first_prefix = base + padding + '# '
    cont_prefix = ' ' * hash_col + '# '

    if len(first_prefix + allowed) <= max_width:
        return first_prefix + allowed

    chunks = allowed.split(sep)
    trail = sep.rstrip()  # appended to non-final lines to preserve separator

    result_lines = []
    current = []
    for chunk in chunks:
        candidate = sep.join(current + [chunk])
        prefix = first_prefix if not result_lines else cont_prefix
        if len(prefix + candidate) <= max_width or not current:
            current.append(chunk)
        else:
            result_lines.append(sep.join(current) + trail)
            current = [chunk]
    if current:
        result_lines.append(sep.join(current))

    out = []
    for i, ln in enumerate(result_lines):
        prefix = first_prefix if i == 0 else cont_prefix
        out.append(prefix + ln)
    return '\n'.join(out)


def fmt_annotated_kv(key, value, doc):
    """Return annotated TOML line(s) for key with allowed-values comment."""
    is_multiselect = (doc and isinstance(doc.values, list)
                      and isinstance(value, list))
    if isinstance(value, list) and len(value) == 1 and not is_multiselect:
        display = fmt_value(value[0])
    else:
        display = fmt_value(value) if value is not None else None
    allowed = fmt_allowed(value, doc)
    if value is None:
        base = f'# {key}'
    else:
        base = f'{key} = {display}'
    if allowed is None:
        return base
    if doc and doc.allowed_doc:
        sep = ' '       # prose: word-wrap
    elif doc and isinstance(doc.values, dict):
        sep = '; '      # alias groups
    elif doc and isinstance(value, list):
        sep = ', '      # multi-select items
    else:
        sep = '; '      # enum options
    return _wrap_comment(base, allowed, sep)


def cross_platform_dot_file(unix_dot_path):
    path = os.path.expanduser(unix_dot_path)
    if not os.path.exists(path):
        d, f = os.path.split(path)
        assert f.startswith('.')
        alt_path = os.path.join(d, f[1:])
        if os.path.exists(alt_path):
            return alt_path
    return path


def fmt_kv(key, value):
    if value is None:
        return f'# {key}'
    else:
        return f'{key} = {fmt_value(value)}'


def fmt_value(value):
    if type(value) in (int, float):
        v = repr(value)
    elif type(value) is str:
        v = json.dumps(value, ensure_ascii = False)
    elif type(value) in (list, tuple):
        v = '[%s]' % ', '.join(fmt_value(v) for v in value)
    elif str(type(value)).startswith('date'):
        v = value.isoformat()
    elif type(value) is bool:
        v = str(value).lower()
    elif value is None:
        # problem in TOML
        v =  'null'
    elif isinstance(value, dict):
        v = '{\n%s\n}' % (',\n'.join(fmt_kv(k, v) for k, v in value.items()))
    else:
        raise Exception(f'{repr(value)}: (type: {type(value)})')
    return v


def show_config(*args):
    from tdda.config import Config
    from tdda.man.utils import print_help
    annotated = False
    mode = 'current'
    for arg in args:
        if arg in ('-a', '--annotated', 'annotated'):
            annotated = True
        elif arg in ('current', '-c', '--current'):
            mode = 'current'
        elif arg in ('default', '--default', '-d'):
            mode = 'default'
        elif arg in ('file', '--file', '-f'):
            mode = 'file'
        elif arg in ('-h', '--help', 'help'):
            mode = 'help'
        else:
            print(f'Unknown config option: {arg}', file=sys.stderr)
            sys.exit(1)
    if mode == 'help':
        print_help('config', sys.stdout)
    elif mode == 'file':
        config_path = cross_platform_dot_file('~/.tdda.toml')
        if os.path.exists(config_path):
            print(f'\nConfig file is {config_path}:\n')
            with open(config_path, encoding='utf-8') as f:
                print(f.read())
                print()
    elif mode == 'current':
        c = Config(load=True)
        print(c.annotated_str() if annotated else str(c))
    elif mode == 'default':
        c = Config(load=False)
        print(c.annotated_str() if annotated else str(c))
