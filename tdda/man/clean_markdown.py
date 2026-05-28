import re
import sys

TITLE_RE = r'^.*"([^"]+) manual"\s*$'
CONTINUATION_RE = re.compile(r'^ {15,}\S')
FLAG_LINE_RE = re.compile(r'^[`\-]')


def main(f, fw):
    out = []
    synopsis = False
    in_options = False
    prev_was_continuation = False
    for line in f:
        if line.startswith('#'):
            if line.startswith('##'):
                if 'SYNOPSIS' in line:
                    synopsis = True
                    in_options = False
                    out.append('###' + line[2:])
                    out.append('```')  # start pre. x as unknown language
                else:
                    if synopsis:
                        out.append('```\n')  # end pre
                    in_options = 'OPTIONS' in line
                    out.append('###' + line[2:])
                    synopsis = False
            else:
                m = re.match(TITLE_RE, line)
                if m:
                    out.append(f'## `{m.group(1)}`\n\n')
            prev_was_continuation = False
        elif synopsis:
            line = line.replace('`', '').replace('*', '')
            out.append(line)
            prev_was_continuation = False
        elif in_options and CONTINUATION_RE.match(line):
            # Strip man-page indent and trailing hard break for Sphinx output
            stripped = line.strip()
            if stripped.endswith('  '):
                stripped = stripped[:-2]
            out.append(stripped + '\n')
            prev_was_continuation = True
        else:
            if in_options and prev_was_continuation and FLAG_LINE_RE.match(line):
                out.append('\n')
            out.append(line)
            prev_was_continuation = False
    text = ''.join(out)
    text = text.replace('```x\n\n', '```x\n').replace('\n\n```', '\n```')
    fw.write(text)


if __name__ == '__main__':
    if len(sys.argv) == 1:
        main(sys.stdin, sys.stdout)
    else:
        with open(sys.argv[1], encoding='utf-8') as f:
            if len(sys.argv) > 2:
                with open(sys.argv[2], 'w', encoding='utf-8') as fw:
                    main(f, fw)
            else:
                main(f, sys.stdout)
