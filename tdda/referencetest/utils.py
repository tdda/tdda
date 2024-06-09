import os
import sys

import chardet

MIN_CHARDET_CONFIDENCE=0.5

class FileType:
    BINARY_IMAGES = ('png', 'jpeg', 'jpg', 'gif', 'ps', 'eps', 'eps')
    TEXT_IMAGES = ('svg', 'ps', 'eps', 'pdf')  # pdf isn't, strictly, but...
    TEXT_FLAT_FILES = ('csv', 'tsv', 'psv')
    OTHER_TEXTS = ('txt',  'tex',
                   'md', 'markdown', 'rst', 'tex'
                   'html', 'htm', 'css', 'js',
                   'json', 'xml', 'yaml',
                   'sh', 'py', 'R', 'sql')
    TEXT_FILES = TEXT_IMAGES + TEXT_FLAT_FILES + OTHER_TEXTS
    IMAGE_FILES = BINARY_IMAGES + TEXT_IMAGES

    def __init__(self, path):
        self.orig_path = path
        self.ext = get_short_ext(path)
        name = os.path.basename(path)

        self.binary = self.ext in self.BINARY_IMAGES
        self.text   = self.ext in self.TEXT_FILES or name == 'Makefile'
        self.image  = self.ext in self.IMAGE_FILES
        self.encoding = 'iso-8859-1' if self.ext == 'pdf' else None
        if not self.image and not self.binary:
            if self.ext == PDF:
                self.encoding = 'iso-8859-1'
            else:
                detector = chardet.UniversalDetector()
                for line in open(path, 'rb'):
                    detector.feed(line)
                    if detector.done:
                        break
                detector.close()
                confidence = detector.result.get('confidence', 0.0)
                if confidence  > MIN_CHARDET_CONFIDENCE:
                    self.encoding = detector.result.get('encoding')
                    self.text = True
                else:
                    self.binary = True
        self.orig_encoding = self.encoding  # encoding might be modified

    def is_unknown(self):
        return not self.binary and not self.text


def guess_encoding(path):
    ext = get_short_ext(path)
    if ext == 'pdf':
        return 'iso-8859-1'
    return 'utf-8'


def normalize_encoding(encoding):
    lc = encoding.lower()
    return 'utf-8' if lc == 'utf8' else lc


def get_encoding(path, encoding=None):
    if encoding is None:
        return guess_encoding(path)
    else:
        return normalize_encoding(encoding)


def get_short_ext(path):
    """Returns path extension, with dot removed"""
    return os.path.splitext(path)[1].lower()[1:] if path else ''


def protected_readlines(path, filetype):
    """
    Attempts to read path base on information in filetype.

    If the file is binary, return None

    If the file can't be read using the filetype
    """
    filetype = filetype or FileType(path)
    if filetype.binary:
        return
    enc = filetype.encoding if filetype else None
    try:
        with open(path, encoding=enc) as f:
            return f.readlines()
        if filetype.is_unknown():
            filetype.text = True
    except UnicodeDecodeError:
        if filetype.text:  # really was expecting text
            try:
                with open(path, encoding='iso-8859-1') as f:
                    lines = f.readlines()
                    filetype.encoding = 'iso-8859-1'
                    return lines
            except UnicodeDecodeError:
                filetype.binary = True
                filetype.text = False
                filetype.encoding = None
                print('Could not read %s as text file; treating as binary'
                      % path, file=sys.stderr)


def normabspath(p):
    return os.path.normpath(os.path.abspath(p))
