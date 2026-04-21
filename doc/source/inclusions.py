import os
from rich import print as rprint
import sys

typemap = {
    'py': 'python',
    'md': 'markdown',
    'json': 'json',
    'sh': 'bash',
    'txt': 'text',
    'yaml': 'yaml',
}


def main(inpath, outpath):
    with open(inpath) as f:
        lines = f.readlines()
    with open(outpath, 'w') as f:
        for line in lines:
            f.write(line)
            if line.startswith('%%'):
                p = line[2:].strip()
                if os.path.exists(p):
                    _, ext = os.path.splitext(p)
                    lang = typemap.get(ext.lstrip('.'), '')
                    f.write(f'```{lang}\n')
                    with open(p) as ff:
                        content = ff.read()
                        f.write(content)
                        if not content.endswith('\n'):
                            f.write('\n')
                    f.write('```\n')
                else:

                    rprint(f'[red]Could not read {p}.', file=sys.stderr)
    rprint(f'[green]Written {outpath}')


if __name__ == '__main__':
    if len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2])
    else:
        print('USAGE: python inclusions.py inpath.md outpath.md',
              file=sys.stderr)
        sys.exit(1)

