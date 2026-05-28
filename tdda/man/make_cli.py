"""
Concatenate per-command Sphinx markdown files into a single cli.md,
with a top-level heading and horizontal rule separators between commands.
"""
import sys


def main(outpath, srcs):
    sections = []
    for path in srcs:
        with open(path, encoding='utf-8') as f:
            text = f.read().strip()
        sections.append(text)

    with open(outpath, 'w', encoding='utf-8') as f:
        f.write('# Command Line Reference\n\n')
        f.write('\n\n---\n\n'.join(sections))
        f.write('\n')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
