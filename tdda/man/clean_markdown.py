import re
import sys

TITLE_RE = r'^.*"([^"]+) manual"\s*$'

def main(f, fw):
    out = []
    synopsis = False
    for line in f:
        if line.startswith('#'):
            if line.startswith('##'):
                if 'SYNOPSIS' in line:
                    synopsis = True
                    out.append(f'##{line}')
                    out.append('```x\n')  # start pre. x as unknown language
                else:
                    if synopsis:
                        out.append('```\n')  # end pre
                    out.append(f'##{line}')
                    synopsis = False
            else:
                m = re.match(TITLE_RE, line)
                if m:
                    out.append(f'### Command: `{m.group(1)}`\n\n')
        elif synopsis:
            line = line.replace('`', '').replace('*', '')
            out.append(line)
        else:
            out.append(line)
    text = ''.join(out)
    text = text.replace('```x\n\n', '```x\n').replace('\n\n```', '\n```')
    fw.write(text)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        main(sys.stdin, sys.stdout)
    else:
        with open(sys.argv[1]) as f:
            if len(sys.argv) > 2:
                with open(sys.argv[2], 'w') as fw:
                    main(f, fw)
            else:
                main(f, sys.stdout)
