import os
import subprocess
import sys


def main(inpath, outpath=None):
    here = os.path.dirname(os.path.abspath(inpath))
    with open(inpath, encoding='utf-8') as f:
        lines = f.readlines()
    out = []
    for line in lines:
        if line.startswith('%%generate:'):
            script = line[len('%%generate:'):].strip()
            script_path = os.path.join(here, script)
            result = subprocess.run(
                [sys.executable, script_path],
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                print(
                    f'Error running {script}:\n{result.stderr}',
                    file=sys.stderr,
                )
                sys.exit(1)
            out.append(result.stdout)
        else:
            out.append(line)
    text = ''.join(out)
    if outpath:
        with open(outpath, 'w', encoding='utf-8') as f:
            f.write(text)
    else:
        sys.stdout.write(text)


if __name__ == '__main__':
    if len(sys.argv) == 2:
        main(sys.argv[1])
    elif len(sys.argv) == 3:
        main(sys.argv[1], sys.argv[2])
    else:
        print(
            'USAGE: python preprocess.py inpath [outpath]',
            file=sys.stderr,
        )
        sys.exit(1)
