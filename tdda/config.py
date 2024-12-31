import datetime
import re

DATETIME_RE ='^[0-9]{4}-[0-9]{2}-[0-9]{2}([T ][0-9]{2}:[0-9]{2}:[0-9]{2})?$'

class Config:
    null_rep = '∅'
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


