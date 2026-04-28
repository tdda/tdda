import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tdda.config import (
    BaseConfig,
    Config,
    ConstraintsConfig,
    ReferenceTestConfig,
    SerialConfig,
    TDDADiffConfig,
    fmt_value,
)

SECTIONS = [
    ('PARAMETERS', Config),
    ('PARAMETERS (referencetest)', ReferenceTestConfig),
    ('PARAMETERS (constraints)', ConstraintsConfig),
    ('PARAMETERS (tddadiff)', TDDADiffConfig),
    ('PARAMETERS (serial)', SerialConfig),
]


def md_value(value):
    if value is None:
        return 'unset'
    if isinstance(value, list) and len(value) == 1:
        value = value[0]
    return '`%s`' % fmt_value(value)


def fmt_allowed(value, doc):
    if doc is None:
        return None
    if doc.allowed_doc is not None:
        return doc.allowed_doc
    if doc.regex is not None:
        return 'Any string'
    if doc.values is None:
        return None
    vals = doc.values
    if isinstance(value, list):
        return 'Any subset of ' + ', '.join(
            '`%s`' % fmt_value(v) for v in vals
        )
    if isinstance(vals, list):
        return ', '.join('`%s`' % fmt_value(v) for v in vals)
    if isinstance(vals, dict):
        # vals is {alias: canonical}; group aliases by canonical
        groups = {}
        for alias, canonical in vals.items():
            groups.setdefault(canonical, []).append(alias)
        parts = []
        for canonical, aliases in groups.items():
            s = '`%s`' % fmt_value(canonical)
            if aliases:
                s += ' (or ' + ', '.join(
                    '`%s`' % fmt_value(a) for a in aliases
                ) + ')'
            parts.append(s)
        return ', '.join(parts)
    return None


def emit_section(title, cls):
    obj = Config(load=False) if cls is Config else cls()
    lines = [f'\n## {title}\n']
    first = True
    for k, v in obj.__dict__.items():
        if k.startswith('_'):
            continue
        if isinstance(v, BaseConfig):
            continue
        doc = obj.__dict__.get(f'_doc_{k}')
        default = md_value(v)
        allowed = fmt_allowed(v, doc)
        if not first:
            pass  # no blank line between params
        first = False
        lines.append(f'### `{k}`')
        desc = doc.doc if doc else ''
        lines.append(f'{desc}  ')
        if allowed:
            lines.append(f'**Default:** {default}  ')
            lines.append(f'**Allowed:** {allowed}')
        else:
            lines.append(f'**Default:** {default}')
    return '\n'.join(lines)


def main():
    parts = []
    for title, cls in SECTIONS:
        parts.append(emit_section(title, cls))
    print('\n'.join(parts))


if __name__ == '__main__':
    main()
