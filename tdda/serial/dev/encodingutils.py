LATIN_1_9_DIFFS = [0xA4, 0xA6, 0xA8] + list(range(0xbc, 0xbf))
CP1252_EXTRAS = list(n for n in range(0x80, 0xA0)
                     if n not in {0x81, 0x8d, 0x8f, 0x90, 0x9d})


class Chars:
    def __init__(self, n):
        self.N = n
        b = bytearray([n])
        for enc in ('iso-8859-1', 'iso-8859-15', 'cp1252'):
            try:
                self.__dict__[enc] = b.decode(enc)
            except UnicodeDecodeError:
                self.__dict__[enc] = None

    def all_same(self):
        return len(set(v for k, v in self.__dict__.items() if k != 'N')) == 1

    def __str__(self):
        return ' '.join(f'{k:5}: {hex(v) if type(v) == int else str(v):5}'
                        for k, v in sorted(self.__dict__.items()))


def write_8bit_file(enc, alt, content, suffix):
    encoded = content.decode(enc)
    path = f'../testdata/sig-{suffix}.csv'
    with(open(path, 'w', encoding=enc)) as f:
        f.write('encoding,altname,hello,sig\n')
        f.write(f'{enc},{alt},hello,{encoded}\n')
    print(f'Written {path}.')


def write_utf_file(enc, latins, cp1252):
    path = f'../testdata/sig-equiv-{enc}.csv'
    w1 = latins.decode('iso-8859-1')
    w2 = latins.decode('iso-8859-15')
    w3 = latins.decode('cp1252') + cp1252.decode('cp1252')
    with(open(path, 'w', encoding=enc)) as f:
        f.write('encoding,hello,latin1,latin9,cp1252\n')
        f.write(f'{enc},hello,{w1},{w2},{w3}\n')
    print(f'Written {path}.')


def main():
    codes = {
      n: Chars(n)
      for n in range(0, 0x100)
    }
    for n, v in codes.items():
        if not v.all_same():
            print(v)

    cp1252_extras = bytearray(CP1252_EXTRAS)
    latins = bytearray(LATIN_1_9_DIFFS)

    write_8bit_file('cp1252', 'windows1252', latins + cp1252_extras, 'cp1252')
    write_8bit_file('iso-8859-1', 'latin1', latins, 'latin1')
    write_8bit_file('iso-8859-15', 'latin9', latins, 'latin9')

    write_utf_file('utf8', latins, cp1252_extras)
    write_utf_file('utf16', latins, cp1252_extras)





if __name__ == '__main__':
    main()


