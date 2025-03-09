import datetime
import os
import re
import sys
import tomli

DATETIME_RE ='^[0-9]{4}-[0-9]{2}-[0-9]{2}([T ][0-9]{2}:[0-9]{2}:[0-9]{2})?$'

class BaseConfig:
    def override(self, d, complain):
        for k, v in d.items():
            if k in self.__dict__ and not k.startswith('_'):
                self.__dict__[k] = v
            elif complain:
                part = self._part
                print(f'Unknown configuration parameter {k} '
                      f'ignored{(" " + part) if part else ""}.',
                      file=sys.stderr)

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
        v = getattr(self, key, None)
        if v is not None:
            return v
        if raiseOnFailure:
            raise AttributeError(f'No atttibute {key} in {self._config_name}')
        else:
            return None


class Config(BaseConfig):
    def __init__(self, load=None, testing=None, complain=True):
        env = os.environ
        self._part = ''
        self._config_name = 'config'
        self.null_rep = '∅'
        self.colour = load and not testing
        self.referencetest = ReferenceTestConfig()
        self.constraints = ConstraintsConfig()
        if not testing and (load or load is None):
            self.load(complain=complain)

    def load(self, complain=True):
        config_path = os.path.expanduser('~/.tdda.toml')
        if os.path.exists(config_path):
            with open(config_path, 'rb') as f:
                d = tomli.load(f)
                rc = d.get('referencetest', None)
                if rc:
                    self.referencetest.override(rc, complain)
                cc = d.get('constraints', None)
                if cc:
                    self.constraints.override(cc, complain)
                if 'referencetest' in d:
                    del d['referencetest']
                if 'constriants' in d:
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
        if v is None:
            return self.null_rep
        if type(v) is str:
            m = re.match(DATETIME_RE, v)
            if m:
                return v[:10] if m.group(1) else v
        if type(v) is datetime.datetime:
            s = v.isoformat('T', timespec='seconds')
            return s[:10] if v.hour or v.minute or v.second else s
        return repr(v)

    def format_constraint_value(self, value, start_col, indent, max_width=79,
                                tabsize=2, rex=False):
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
        self.right_colour = 'green'
        self.mono = False
        self.bw = False
        self.left_prefix = '< '
        self.right_prefix = '> '
        self.vertical = False
        self.force_val_prefixes = False

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

    def common(self, value, dim_if_not_bw=False):
        if self.mono or (dim_if_not_bw and not self.bw):
            return f'[dim]{value}[/dim]'
        else:
            return str(value)

    def set_colours(self, left, right):
        self.left_colour, self.right_colour = left.lower(), right.lower()
        # possibly validate

    def set_prefixes(self, left, right):
        self.left_prefix, self.right_prefix = left, right
        # possibly validate

    def stripped_prefixes(self, pre='\n'):
        return (pre + self.left_prefix.strip().replace(':', ''),
                pre + self.right_prefix.strip().replace(':', ''))


class ConstraintsConfig(BaseConfig):
    def __init__(self):
        self._part = 'constraints'
        self._config_name = 'config.constraints'


