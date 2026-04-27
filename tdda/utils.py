import datetime
import itertools
import json
import math
import os
import re
import regex
import sys
import tomli_w
import types
import unicodedata
import urllib.parse
import yaml

from fnmatch import fnmatch


# jythonc needs explicit import of utf-8 and iso-8859-1/latin1 encoding packages
import encodings.aliases  # type:ignore
import encodings.utf_8
import encodings.ascii  # type:ignore
import encodings.latin_1  # type:ignore
import encodings.iso8859_1  # type:ignore


from collections import namedtuple

import numpy as np
import pandas as pd

import rich

rprint = rich.print
rich.reconfigure(highlight=False, soft_wrap=True)

from rich.console import Console

stdout_console = Console(highlight=False, soft_wrap=True)
stderr_console = Console(stderr=True, highlight=False, soft_wrap=True)

from tdda.state import get_config


TDDADIR = os.path.dirname(__file__)  # base tdda directory for package
CONSTRAINTSDIR = os.path.join(TDDADIR, 'constraints')
PDCONSTRAINTSDIR = os.path.join(CONSTRAINTSDIR, 'pd')
DBCONSTRAINTSDIR = os.path.join(CONSTRAINTSDIR, 'db')
CONSTRAINTSTESTDATADIR = os.path.join(CONSTRAINTSDIR, 'testdata')
TESTREPORTSDIR = os.path.join(CONSTRAINTSTESTDATADIR, 'reports')
TEMPLATESDIR = os.path.join(TDDADIR, 'templates')
REFTESTDIR = os.path.join(TDDADIR, 'referencetest')

DEFAULT_INPUT_ENCODING = 'UTF-8'

OK = 'ok'
BAD = 'bad'
NAN = float('nan')

TDDA_NF_MAP = None  # build lazily

ALT_NULL_REP = '∅'
ALT_OTHER_REP = '★'
U_ALT_NULL_REP = '∅'
ENDASH = '–'  # chr(0x2013)
MINUS_SIGN = '−'  # chr(0x2212)


TDDAPathInfo = namedtuple(
    'TDDAPathInfo', 'path stem ext md_path find_md combined'
)


class TDDAError(Exception):
    pass


class XMLError(TDDAError):
    pass


class XML:
    def __init__(
        self,
        indentLevel=0,
        tabSize=4,
        omitHeader=0,
        output=None,
        html=0,
        xsl='',
        css=[],
        title='',
        padEmptyElements=0,
        content='',
        inputEncoding=DEFAULT_INPUT_ENCODING,
        headerAttr={},
        useHardTabs=True,
        float_precision=None,
        debug=False,
        altnbsp=None,
        hardTabs=True,
    ):
        """Initialize XML.

        An XML declaration is put in unless
             omitHeader = 1 or indentLevel > 0.
        If html is set to 5, an HTML5 head <!DOCTYPE html>
        is used in place of the XML header.

        If tabSize is given, nested elements are indented by this many
             spaced (tabified).

        If output is set to 'stdout' (in any case),
        output is written to STDOUT on the fly and flushed.
        If it is set to anything else, this is used as a filename
        to write to, and again output is written on the fly and flushed.

        If html = 1, an XHTML file is written with
             - a title in the head if provided
             - a list of CSS stylesheets in the head, if css is provided
             - a head if a title or a css list is provided

        If padEmptyElements = 1, these get a non-breaking space.

        If xsl is given, this is added to the XML as an xsl-stylesheet
             processing instruction.

        If context is given, self.contentType is set to the
             appropriate string.

        If inputEncoding is given, this specifies the encoding input
             data is in. Output encoding is always utf-8."""

        self.indentLevel = indentLevel
        self.tabSize = tabSize
        self.pad = padEmptyElements
        self.stack = []
        self.html = html
        self.xmlbuf = ['']
        self.out = None
        self.tab = '\t' if useHardTabs else '        '
        self.float_precision = float_precision
        self.float_fmt = (
            ('%%.%df' % float_precision) if float_precision else None
        )
        self.altnbsp = None
        self.debug = debug
        self.hardTabs = hardTabs
        if output:
            self.output = output
            if output.lower() == 'stdout':
                self.out = sys.stdout
            elif output:
                self.out = open(self.output, 'wb')
        if indentLevel == 0 and not (omitHeader):
            extraAttr = ''
            if html == 5:
                self.xmlbuf.append('<!DOCTYPE html>\n')
            else:
                if headerAttr:
                    extraAttr = ''.join(
                        [
                            ' %s="%s"' % (key, headerAttr[key])
                            for key in headerAttr.keys()
                        ]
                    )
                self.xmlbuf.append(
                    '<?xml version="1.0" encoding="UTF-8"%s?>\n' % extraAttr
                )
        self.inputEncoding = inputEncoding

        if self.html:
            html_attrs = {'lang': 'en'} if html == 5 else {}
            self.WriteElement('html', '', html_attrs, leave='open')
            if title or css or html == 5:
                self.WriteElement('head', leave='open')
                if html == 5:
                    self.WriteElement('meta', '', {'charset': 'UTF-8'})
                if title:
                    self.WriteElement('title', title)
                if css:
                    if type(css) in (list, tuple):  # list of URLs
                        for c in css:
                            self.WriteElement(
                                'link',
                                '',
                                {'rel': 'stylesheet', 'href': c},
                                entitize=0,
                            )
                    else:  # in-line CSS
                        self.WriteElement(
                            'style', css, {'type': 'text/css'}, entitize=0
                        )
                self.CloseElement('head')
            self.WriteElement('body', leave='open')

        if xsl:
            self.WritePI('xml-stylesheet', {'href': xsl, 'type': 'text/xsl'})

        if content.lower() in ('xml', 'html', 'text'):
            self.contentType = 'Content-Type: text/%s\n' % content.lower()
        elif content == '':
            self.contentType = ''
        else:
            raise XMLError('Unknown content type "%s"' % content)

    def LatinSafe(self, S):
        o = []
        for s in S:
            n = ord(s)
            if n < 128 or n >= 160:
                o.append(s)
        return ''.join(o)

    def Flush(self):
        if self.out:
            self.out.write(utf8_definite(self.xml(flushing=True)))
            self.xmlbuf = []

    def Entitize(self, s, entitize=1):
        return xml_entitize(s, entitize=entitize, altnbsp=self.altnbsp)

    def WriteElement(
        self,
        name,
        content='',
        attributes={},
        leave='close',
        entitize=1,
        convertWS=0,
        link='',
        convertNL=0,
        tight=False,
        forceNL=False,
        openclose=False,
    ):
        if type(content) == bytes:
            content = content.decode(self.inputEncoding)
        # In HTML mode, non-void elements should use open/close tags even when empty
        if self.html and not openclose:
            # HTML void elements that can self-close
            void_elements = {
                'area',
                'base',
                'br',
                'col',
                'embed',
                'hr',
                'img',
                'input',
                'link',
                'meta',
                'param',
                'source',
                'track',
                'wbr',
            }
            if name.lower() not in void_elements:
                openclose = True
        self.xmlbuf.append(
            xml_element(
                name,
                content,
                attributes,
                leave=leave,
                entitize=entitize,
                convertWS=0,
                link='',
                convertNL=convertNL,
                indent='' if tight else self.IndentString(),
                openclose=openclose,
            )
        )
        if leave != 'close':
            self.Push(name, tight)
        self.Flush()

    def OpenElement(
        self,
        name,
        content='',
        attributes={},
        leave='close',
        entitize=1,
        convertWS=0,
        link='',
        tight=False,
        forceNL=False,
    ):
        self.WriteElement(
            name,
            content,
            attributes,
            'open',
            entitize,
            convertWS,
            link,
            tight=tight,
            forceNL=forceNL,
        )

    def WriteCDElement(
        self, name, content='', attributes={}, leave='close', urlsafe=0
    ):
        indent = self.IndentString()
        self.xmlbuf.append(indent + '<' + self.toString(name))
        if attributes:
            self.WriteAttributes(attributes)
        self.xmlbuf.append('>')
        if urlsafe:
            self.xmlbuf.append(
                '<![CDATA[' + urllib.parse.quote(str(content), safe='') + ']]>'
            )
        else:
            content = unicode_definite(content)
            self.xmlbuf.append('<![CDATA[' + content + ']]>')
        if leave == 'close':
            self.xmlbuf.append('</' + name + '>\n')
        else:
            self.Push(name)
        self.Flush()

    def WritePI(self, name, attributes={}):
        self.xmlbuf.append('<?' + name)
        if attributes:
            self.WriteAttributes(attributes)
        self.xmlbuf.append('?>\n')

    def IndentString(self):
        if self.hardTabs:
            return self.tab * (
                (self.indentLevel * self.tabSize) // 8
            ) + ' ' * ((self.indentLevel * self.tabSize) % 8)
        else:
            return ' ' * (self.indentLevel * self.tabSize)

    def Push(self, name, tight=False):
        if not tight:
            self.xmlbuf.append('\n')
        self.indentLevel += 1
        self.stack.append(name)

    def WriteContent(
        self, content, leave='open', force=False, tight=False, entitize=False
    ):
        if not force and self.indentLevel < 1:
            raise XMLError('No element open for writing')
        if content:
            c = self.Entitize(content) if entitize else content
            if tight:
                self.xmlbuf.append(c)
            else:
                self.xmlbuf.append(self.IndentString() + c)
        if leave == 'close':
            self.CloseElement()

    def AddBalancedXML(self, xml):
        """Add a balanced XML section to the output.
        It is the caller's responsibility to ensure that the XML
        delivered is balanced, well-formed, in situ etc: this function
        just appends it to the output."""
        self.xmlbuf.append(xml if type(xml) == str else xml.decode('UTF-8'))

    def CloseElement(self, element=None, tight=False, forceNL=False):
        if self.indentLevel < 1:
            raise XMLError('No element open for closing')
        self.indentLevel -= 1
        stored = self.stack.pop()
        if element:
            if str(element) != stored:
                info = '\n'.join([''] + self.xmlbuf) if self.debug else ''
                raise XMLError(
                    'Attempt to close %s with %s%s' % (stored, element, info)
                )
        if tight:
            self.xmlbuf.append('</' + stored + '>\n')
        else:
            self.ForceNL(forceNL)
            self.xmlbuf.append(self.IndentString() + '</' + stored + '>\n')
        self.Flush()

    def ForceNL(self, forceNL):
        if forceNL and self.xmlbuf and not self.xmlbuf[-1].endswith('\n'):
            self.xmlbuf.append('\n')

    def CloseAllOpen(self):
        while self.indentLevel > 0:
            self.CloseElement()

    def CloseXML(self, forceTidy=0):
        if forceTidy:
            self.CloseAllOpen()
        else:
            if self.html:
                self.CloseElement('body')
                self.CloseElement('html')
            if self.indentLevel != 0:
                raise XMLError(
                    'Attempt to terminate open XML '
                    '(items remaining %s)' % str(self.stack)
                )
        self.Flush()
        if self.out and self.out != sys.stdout:
            self.out.close()

    def WriteAttributes(self, attributes):
        self.xmlbuf.append(f' {xml_attributes(attributes)}')

    def WriteComment(self, comment, padlines=1):
        padding = '\n' * padlines
        indent = self.IndentString()
        if type(comment) == list:
            if len(comment) > 0:
                c = comment[0].replace('--', '- - ')
                self.xmlbuf.append('%s%s<!-- %s\n' % (padding, indent, c))
                indent = '%s%s' % (indent, ' ' * 5)
                for i, cl in enumerate(comment[1:]):
                    c = cl.replace('--', '- - ')
                    if i == len(comment) - 2:  # last
                        end = ' -->\n%s' % padding
                    else:
                        end = '\n'
                    self.xmlbuf.append('%s%s%s' % (indent, c, end))

        else:
            c = comment.replace('--', '- - ')
            self.xmlbuf.append(
                '%s%s<!-- %s -->%s\n'
                % (padding, self.IndentString(), comment, padding)
            )

    def __str__(self):
        s = 'indent level = %d\n' % self.indentLevel
        s = 'indentation size = %d' % self.tabSize
        s += 'stack = %s\n' % self.stack
        s += 'xml = \n' + self.xml()
        return s

    def xml(self, flushing=False):
        if self.indentLevel > 0 and not flushing:
            raise XMLError('Elements still open: %s.' % ', '.join(self.stack))
        return ''.join(self.xmlbuf)

    def toString(self, v):
        if type(v) is str:
            return v
        elif type(v) is bytes:
            return str(v, self.inputEncoding, 'ignore')
        elif type(v) is float and self.float_fmt is not None:
            s = str(self.float_fmt % v)
            while s.endswith('0') and not len(s) == 1 and not s.endswith('.0'):
                s = s[:-1]
            if s.endswith('.0') and len(s) > 2:
                s = s[:-2]
            return s
        else:
            return str(v)


def xml_entitize(s, entitize=1, altnbsp=None):
    s = re.sub('&', '&amp;', s)
    s = re.sub('<', '&lt;', s)
    s = re.sub('>', '&gt;', s)
    if entitize > 1:
        s = re.sub('&lt;=', '&#x2264;', s)
        s = re.sub('&gt;=', '&#x2265;', s)
    s = re.sub("'", '&apos;', s)
    s = re.sub('"', '&quot;', s)
    if altnbsp:
        s = re.sub(altnbsp, '&nbsp;', s)
    return s


def xml_attributes(attributes):
    """
    Given a dictionary or iterable of pairs of attributes (key, value),
    returns the appropriate xml string

        'a="3" b="fool"'

    with the values stringified and entitized.

    keys are assumed to be valid, entitized strings.
    """
    items = attributes.items() if isinstance(attributes, dict) else attributes
    return ' '.join(f'{a}="{xml_entitize(str(val))}"' for a, val in items)


def xml_element(
    name,
    content='',
    attributes={},
    leave='close',
    entitize=1,
    convertWS=0,
    link='',
    convertNL=0,
    indent='',
    forceNL=False,
    openclose=False,
    pad=0,
):
    # convertNL: binary field:
    #   0  to ignore newlines
    #   *1 to convert backslash n (r'\n') to <br/>
    #   1* to convert inline newline '\n' to <br/>
    out = []
    if content is None:
        print('WARNING: null content for element %s' % name, file=sys.stderr)
        content = ''
    else:
        content = str(content)
    if forceNL:
        out.append('' if out[-1].endswith('\n') else '\n')
    out.append(f'{indent}<{name}')
    if attributes:
        out.append(f' {xml_attributes(attributes)}')
    if content == '' and leave == 'close':
        if openclose:
            nl = '\n'
            out.append(f'></{name}>{nl if indent else ""}')
        else:
            out.append('/>\n' if indent else '/>')
    else:
        out.append('>')
    if link:
        out.append('<a href="xml_entitize{%s}">' % link)
    if re.match('^[ \t]+$', content) or (
        pad and content == '' and leave == 'close'
    ):
        xmlc = '&#160;'
    elif entitize:
        xmlc = xml_entitize(content, entitize=entitize)
    else:
        xmlc = content
    if convertNL & 1:
        xmlc = xmlc.replace('\\n', '<br/>')
    if convertNL & 2:
        xmlc = xmlc.replace('\n', '<br/>')
    if xmlc:
        out.append(xmlc)
    if link:
        out.append('</a>')
    if leave == 'close' and content != '':
        nl = '\n'
        out.append(f'</{name}>{nl if indent else ""}')
    return ''.join(out)


class PassFailStats:
    def __init__(self, passes, failures, items='records'):
        self.items = items
        self.n_passes = passes
        self.n_failures = failures
        denom = max(1, passes + failures)
        self.pass_rate = passes / denom
        self.failure_rate = failures / denom

    def to_dict(self, pc=True, total_values=False):
        d = {
            'n_passes': self.n_passes,
            'n_failures': self.n_failures,
        }
        if total_values:
            d[f'n_{self.items}'] = (self.n_passes + self.n_failures,)

        if pc:
            d.update(
                {
                    'pass_rate': to_pc(self.pass_rate),
                    'failure_rate': to_pc(self.failure_rate),
                }
            )
        return d


def nvl(v, w):
    """
    This function is used as syntactic sugar for replacing null values.
    """
    return w if v is None else v


def swap_ext(path, new_ext):
    """
    Replaces the extension of path to new_ext
    """
    base, ext = os.path.splitext(path)
    dot = '' if new_ext == '' or new_ext.startswith('.') else '.'
    return base + dot + new_ext


def swap_ext_q(path, new_ext):
    """
    Replaces the extension of path to new_ext

    Return (new path, changed)

    where changed is True iff the old and new extensions are different
    """
    outpath = swap_ext(path, new_ext)
    _, ext = os.path.splitext(path)
    _, new_ext = os.path.splitext(outpath)
    return outpath, new_ext != ext


def handle_tilde(path):
    """
    Handle paths starting tilde.

    Does nothing unless path is a string and starts with '~'
    """
    if type(path) is str and path.startswith('~'):
        return os.path.expanduser(path)
    else:
        return path


def dict_to_json(d, path=None):
    """
    Dumps appropriately formatted version of dictionary d to JSON.
    If path is given, it goes there; otherwise, the JSON is returned.
    """
    json_text = strip_lines(json.dumps(d, indent=4, ensure_ascii=False)) + '\n'
    if path:
        with open(path, 'w') as f:
            f.write(json_text)
    else:
        return json_text


def dict_to_yaml(d, path=None):
    """
    Dumps appropriately formatted version of dictionary d to YAML.
    If path is given, it goes there; otherwise, the YAML is returned.
    """
    if path:
        with open(path, 'w') as f:
            yaml.dump(d, f)
    else:
        return yaml.dump(d)


def dict_to_toml(d, path=None):
    """
    Dumps appropriately formatted version of dictionary d to JSON.
    If path is given, it goes there; otherwise, the JSON is returned.
    """
    if path:
        with open(path, 'wb') as f:
            tomli_w.dump(d, f)
    else:
        return tomli_w.dumps(d)


def json_sanitize(v):
    if repr(v) in ('nan', 'NaT', '<NA>'):
        return None
    elif v is None or type(v) in (str, int, float, bool):
        return v
    elif type(v) in (list, tuple):
        return [json_sanitize(u) for u in v]
    elif isinstance(v, dict):
        return {str(k): json_sanitize(u) for k, u in v.items()}
    elif hasattr(v, '__dict__') and v.__dict__:
        return json_sanitize(v.__dict__)
    else:
        s = str(v)
        return s[:-9] if s.endswith('00:00:00') else s  # slightly dodgy


def dump_as_json(d):
    return json.dumps(json_sanitize(d), indent=4, ensure_ascii=False)


def remove_falsy_values(d):
    return {k: v for k, v in d.items() if v}


def strip_lines(s):
    """
    Splits the given string into lines (at newlines), strips trailing
    whitespace from each line before rejoining.

    Is careful about last newline.
    """
    end = '\n' if s.endswith('\n') else ''
    return '\n'.join([line.rstrip() for line in s.splitlines()]) + end


def indicator_suffix(detect_passes=True):
    return OK if detect_passes else BAD


def indicator_field_name(field, constraint, name_map=None, detect_passes=True):
    suffix = indicator_suffix(detect_passes)
    if name_map:
        return f'{field}_{name_map[constraint]}_{suffix}'
    else:
        return f'{field}_{constraint}_{suffix}'


def pass_fail_stats(passes, failures, items='cases'):
    return PassFailStats(passes, failures, items=items)


def to_pc(v, mindp=2):
    pc = 100 * v
    delta = 5 * pow(10, -mindp - 1)
    if pc in (0, 100) or ((100 - pc > delta) and pc > delta):
        return f'{v * 100:.2f}%'  # won't be 100.00% or 0.00% if not exact

    threshold = 100 - pc if (pc > delta) else pc
    dps = -math.log10(threshold)
    lo_dps = int(dps)
    hi_dps = lo_dps + 1
    lo_fmt = '%%.%df' % lo_dps
    small = lo_fmt % pc
    i, f = small.split('.')
    if i == 100 or f == '0' * len(f):
        hi_fmt = '%%.%df' % hi_dps
        return f'{hi_fmt % pc}%'
    else:
        return f'{small}%'


def n_glyphs(s):
    """
    Returns the number of glyphs in a string.
    """
    return len(regex.findall(r'\X', s))


def tddadir(*path):
    """
    Returns the full path to path where path is in the base tdda directory
    """
    return os.path.join(TDDADIR, *path)


def constraints_testdata_path(path):
    """
    Returns the full path to path where path is in the constraints
    testdata directory
    """
    return os.path.join(TDDADIR, 'constraints', 'testdata', path)


def richbad(s, colour=True, cond=True):
    if colour and cond:
        return '[red]%s[/red]' % s
    else:
        return str(s)


def richgood(s, colour=True, cond=True):
    if colour and cond:
        return '[green]%s[/green]' % s
    else:
        return str(s)


def richgoodbad(s, colour=True, cond=True):
    if colour:
        c = 'green' if cond else 'red'
        return f'[{c}]{s}[/{c}]'
    else:
        return str(s)


def write_or_return(content, dump, stringify, path=None, binary=False):
    """
    If path has a value, write content to it and return None.
    Use binary mode for writing if binary it set.
    """
    if path:
        mode = 'wb' if binary else 'w'
        with open(path, mode) as f:
            dump(content, f)
        return None
    else:
        return stringify(content)


def tdda_css():
    with open(os.path.join(TEMPLATESDIR, 'tdda.css')) as f:
        return f.read()


def constraint_val(v, kind=None):
    if type(v) is list:
        return '\n'.join(constraint_val(x) for x in v)
    elif type(v) is int:
        return str(v)
    elif type(v) is float:
        return str(v)
    elif type(v) is str:
        return v if kind in ('type', 'sign') else json.dumps(v)
    elif type(v) is bool:
        if kind == 'no_duplicates':
            return 'no' if v else ''
        return str(v).lower()
    elif type(v) is datetime.datetime:
        s = v.isoformat(timespec='seconds')
        return s[:10] if s.endswith('T00:00:00') else s
    elif type(v) is datetime.date:
        return v.isoformat()
    else:
        return repr(v)


def DQuote(string, escape=True):
    parts = string.split('"')
    if escape:
        parts = [p.replace('\\', r'\\').replace('\n', r'\n') for p in parts]
    quoted = ('\\"').join(parts)
    return '"%s"' % quoted


def squote(string, escape=True):
    parts = string.split("'")
    if escape:
        parts = [p.replace('\\', r'\\').replace('\n', r'\n') for p in parts]
    quoted = ("\\'").join(parts)
    return "'%s'" % quoted


def is_sequence(L):
    """
    Tests whether L is a list, tuple or something similar
    (in particular, that it can be indexed).
    """
    return (
        hasattr(L, '__getitem__') or hasattr(L, '__iter__')
    ) and not hasattr(L, 'strip')


def is_parquet(path):
    return os.splitext.path(path)[1] == '.parquet'


class Dummy(object):
    """
    A dummy object. For whatever.
    """

    def __init__(self, **kwargs):
        for k in kwargs:
            self.__dict__[k] = kwargs[k]

    def to_dict(self):
        return self.__dict__


def cprint(*args, colour=None, recolour=None, config=None, **kw):
    if colour is None:
        config = get_config(config)
        colour = config.get('colour')
    if colour:
        if recolour:
            rprint(*(f'[{recolour}]{a}[/{recolour}]' for a in args), **kw)
        else:
            rprint(*(str(a) for a in args), **kw)
    else:
        print(*args, **kw)


def print_stderr(*args, **kw):
    cprint(*args, recolour='red', file=sys.stderr)


def tdda_nf_map():
    lu = unicodedata.lookup
    strmap = {
        '\u2013': '-',  # EN DASH
        '\u2014': '-',  # EM DASH
        '\u2212': '-',  # MINUS SIGN
        '\u2018': "'",  # LEFT SINGLE QUOTATION MARK
        '\u2019': "'",  # RIGHT SINGLE QUOTATION MARK
        '\u02bc': "'",  # MODIFIER LETTER APOSTROPHE
        '\u0060': "'",  # GRAVE ACCENT
        # '\uFF02',  # FULLWIDTH QUOTATION MARK  # Handled by NFKC/D
        '\u201c': '"',  # LEFT DOUBLE QUOTATION MARK
        '\u201d': '"',  # RIGHT DOUBLE QUOTATION MARK
        # Handled by NFKC/D
        # '\u00A0',  # NO-BREAK SPACE
        # '\u2002',  # EN SPACE
        # '\u2003',  # EM SPACE
        # '\u2007',  # FIGURE SPACE
        # '\u2008',  # PUNCTUATION SPACE
        '\u0009': ' ',  # TAB  # unicodedata.name does not recognize!
        # Handled by NFKC/D:
        # '\u00B9',  # SUPERSCRIPT ONE
        # '\u2081',  # SUBSCRIPT ONE
        # '\u2460',  # CIRCLED DIGIT ONE
        # '\U0001D7D9',  # MATHEMATICAL DOUBLE-STRUCK DIGIT ONE
        '\u2474': '(1)',  # PARENTHESIZED DIGIT ONE
        '\u2488': '1.',  # DIGIT ONE FULL STOP
        '\u0391': 'A',  # GREEK CAPITAL LETTER ALPHA
        '\u00c5': 'A',  # LATIN CAPITAL LETTER A WITH RING ABOVE
        # '\u212B',  # ANGSTROM SIGN  # Handled by NFKC/D
        # Handled by NFKC/D:
        #'\u2026',  # HORIZONTAL ELLIPSIS
        #'\uFE19',  # PRESENTATION FORM FOR VERTICAL HORIZONTAL ELLIPSIS
        '\u22ee': '...',  # VERTICAL ELLIPSIS
        '\u22ef': '...',  # MIDLINE HORIZONTAL ELLIPSIS
        '\u22f1': '...',  # DOWN RIGHT DIAGONAL ELLIPSIS
        '\u04d5': 'ae',  # 'æ'
        '\u00e6': 'ae',  # 'æ'
        '\u04d4': 'AE',  # 'Ӕ'
        '\u00c6': 'AE',  # 'Æ'
        'ǽ': 'ae',
        'đ': 'd',
        'ð': 'd',
        'ƒ': 'f',
        'ħ': 'h',
        'ı': 'i',
        'ł': 'l',
        'ø': 'o',
        'ǿ': 'o',
        'Ø': 'O',
        'œ': 'oe',
        'Œ': 'OE',
        'ß': 'ss',
        'ŧ': 't',
    }

    return str.maketrans(strmap)


def normal_form_tk(
    s, remove_accents=True, strip=False, standardize_space=False, nfkd=False
):
    """
    Maps a string to TDDA normal form (NFTK), which is normal
    Unicode Normal Form TKC (or TKD, if specified)
    with some extra mappings of commonly confused characters
    and the option to strip accents, and to normalize and trim space.

    ARGS:
        s:                 String to be normalized
        remove_accents:    If True many accents are removed (default True)
        strip:             Strips leading and trailing space if True
        standardize_space: Replaces multiple spaces with single space
        nfkd:              If True, returns NFKD rather than the default NFKC

    Main non-"kompatability" adjustments are:

        Replace dashes and minus signs with ASCII -
        Replace curly and left quotes/apostrophes to ASCII ' and "
        Replace each TAB character with a (single) space.

    """
    global TDDA_NF_MAP
    if TDDA_NF_MAP is None:
        TDDA_NF_MAP = tdda_nf_map()

    form = 'NFKD' if nfkd else 'NFKC'
    normalized = unicodedata.normalize('NFKD', s)
    if remove_accents:
        normalized = ''.join(
            c for c in normalized if not unicodedata.combining(c)
        )
    normalized = normalized.translate(TDDA_NF_MAP)
    if strip:
        normalized = normalized.strip()
    if standardize_space:
        while '  ' in normalized:
            normalized = normalized.replace('  ', ' ')
    return unicodedata.normalize(form, normalized)


def rednz(v):
    if v == 0:
        return '0'
    else:
        return xml_element('span', f'{v:,}', attributes={'class': 'tdred'})


def redblack(v, red):
    if red:
        return xml_element('span', v, attributes={'class': 'tdred'})
    else:
        return v


def coloured_tick_cross(ok):
    colour = 'tdgreen' if ok else 'tdred'
    mark = '✓' if ok else '✗'
    return xml_element('span', mark, attributes={'class': colour})


def richprint(*args, **kw):
    stdout_console.print(*args, **kw)


def warn(*args, buf=None, verbose=True, **kw):
    if buf:
        buf.append(args)
    elif verbose:
        stderr_console.print(*args, style='yellow', **kw)


def error(*args, raise_error=False, exit=True, **kw):
    if raise_error:
        raise TDDAError('\n'.join(args) if args else 'error')
    stderr_console.print(*args, style='red', **kw)
    if exit:
        sys.exit(1)


def debug(*args, buf=None, verbose=True, **kw):
    if buf:
        buf.append(args)
    elif verbose:
        stderr_console.print(*args, style='blue', **kw)


def listify(v, sort=False):
    """
    If v is not a list, convert it to a list.
    In particularly, turn a scalar, v, into [v]
    """
    L = (
        v
        if isinstance(v, list)
        else list(v)
        if isinstance(v, tuple)
        else []
        if v is None
        else [v]
    )
    return sorted(L) if sort else L


def delistify(L):
    """
    Turn L into a scalar if it is a singleton list (or similar).
    """
    return L[0] if (is_sequence(L) and len(L) == 1) else L


def tdda_path_info(inpath):
    inpath = handle_tilde(inpath)
    if ':' in inpath and not os.path.exists(inpath):
        if inpath.endswith(':'):
            path = inpath[:-1]
            stem, ext = os.path.splitext(path)
            return TDDAPathInfo(path, stem, ext, None, True, inpath)
        parts = inpath.split(':')
        if len(parts) == 2:
            path, md_path = parts
            stem, ext = os.path.splitext(path)
            return TDDAPathInfo(
                path, stem, ext, handle_tilde(md_path), False, inpath
            )
        # else
        # ignore for now

    stem, ext = os.path.splitext(inpath)
    return TDDAPathInfo(inpath, stem, ext, None, False, inpath)


def globlike_match(patterns, names):
    if patterns is None or names is None:
        return []
    if isinstance(patterns, str):
        patterns = [patterns]
    return [name for name in names if any(fnmatch(name, p) for p in patterns)]


def testwarn():
    buf = []
    f = lambda *args, **kw: buf.extend(args)
    return f, buf


testwarn.__test__ = False


def find_free_name(names, candidates=None):
    candidates = candidates or ['f']
    for c in candidates:
        if c not in names:
            return c
    n = 1
    c = f'{candidates[0]}_{n}'
    while c in names:
        n += 1
    return c


def is_windows():
    return sys.platform.startswith('win')


def dict_to_tex_macros(d, outpath=None, verbose=False):
    defs = ''.join(
        '\\def\\%s{%s}\n' % (tex_name(k), tex_encode(str(v)))
        for k, v in d.items()
    )
    if outpath:
        with open(outpath, 'w') as f:
            f.write(defs)
        if verbose:
            print(f'Written {outpath}.')
    return defs


def tex_encode(s, number=False, para=False):
    if not type(s) is str:
        print(
            'tex_encode: input type (%s); expected type (%s)' % (type(s), str)
        )
        print(s)
        raise Exception('Wrong type sent to tex_encode')
    if s is None:
        return r'\hbox{$\varnothing$}'
    s = s.replace('\\', r'\verb+\+')
    s = s.replace('&', r'\&')
    s = s.replace('{', r'\{')
    s = s.replace('}', r'\}')
    s = s.replace('^', r'\^')
    s = s.replace('_', r'\_')
    s = s.replace('$', r'\$')
    s = s.replace('£', r'\pounds{}')
    s = s.replace('#', r'\#')
    s = s.replace('<=', r'$\le$')
    s = s.replace('>=', r'$\ge$')
    s = s.replace('≤', r'$\le$')
    s = s.replace('≥', r'$\ge$')
    s = s.replace(ALT_NULL_REP, r'\hbox{$\varnothing$}')
    s = s.replace(ALT_OTHER_REP, r'\hbox{$\bigstar$}')

    s = s.replace('<', '$<$')
    s = s.replace('>', '$>$')
    s = s.replace(r'$\le$ x $<$', r'$\le x <$')
    s = s.replace('·', r'$\cdot$')
    s = s.replace('%', r'\%')
    s = s.replace('~', r'$\sim$')
    s = s.replace('©', r'\copyright{}')
    s = s.replace(ENDASH, '--')
    s = s.replace(MINUS_SIGN, '--')
    s = s.replace('—', '---')
    s = s.replace('⎵', r'\textvisiblespace{}')

    if number and s.startswith('-'):
        s = '$%s$' % s
    elif s.startswith('-'):
        plain = (
            s.replace(',', '')
            .replace(' ', '')
            .replace('%', '')
            .replace('--', '-')
            .replace(r'\$', '')
            .replace(r'\pounds{}', '')
        )
        try:
            x = float(plain)
            s = '$%s$' % s
        except ValueError:
            pass
    return s + ('\n\n' if para else '')


DIGITS = {
    '1': 'One',
    '2': 'Two',
    '3': 'Three',
    '4': 'Four',
    '5': 'Five',
    '6': 'Six',
    '7': 'Seven',
    '8': 'Eight',
    '9': 'Nine',
    '0': 'Zero',
}

TENS = {
    '10': 'Ten',
    '20': 'Twenty',
    '30': 'Thirty',
    '40': 'Forty',
    '50': 'Fifty',
    '60': 'Sixty',
    '70': 'Seventy',
    '80': 'Eighty',
    '90': 'Ninety',
}


def tex_name(name):
    out = camelName(name)
    return remap(powers_of_ten(out), DIGITS)


def remap(s, d):
    return ''.join(d.get(c, c) for c in s)


def powers_of_ten(s):
    r = (
        s.replace('000000', 'mn')
        .replace('00000', 'xxk')
        .replace('0000', 'xk')
        .replace('000', 'k')
        .replace('00', 'Hundred')
    )
    for tens, name in TENS.items():
        r = r.replace(tens, name)
    return r


def camelName(name):
    out = []
    cap = False
    for c in name:
        if cap:
            c = c.upper()
        cap = False
        if c in '-_':
            cap = True
        else:
            out.append(c)
    return ''.join(out) if out else 'v'


def split_string_list(s):
    """Split string on commas, spaces, allowing dups"""
    L = [w.strip() for w in s.replace(',', ' ').split(' ')]
    return [w for w in L if w]


def plural(n, s, pl=None, inc_n=True, full_plural=None):
    """
    Returns a string like '23 fields' or '1 field' where the
    number is n, the stem is s and the plural is either stem + 's',
    stem + pl, or full_plural (if provided).

    If inc_n is False, just returns s, singular or pluralized (no number)
    based on n.
    """
    if full_plural is not None:
        p = full_plural
    elif pl is None:
        p = s + 's'
    else:
        p = '%s%s' % (s, pl)

    if inc_n:
        return '%s %s' % (n, s if n == 1 else p)
    else:
        return s if n == 1 else p


def string_list(list_, conjunction='and', oxford=False):
    """Returns a string from the list of the form "A, B, C and D"""
    list_ = list(list_)
    if len(list_) == 0:
        return 'none'
    if len(list_) == 1:
        return str(list_[0])
    oxford_comma = ',' if (oxford and len(list_) > 2) else ''
    return ', '.join((str(L) for L in list_[:-1])) + '%s %s %s' % (
        oxford_comma,
        conjunction,
        list_[-1],
    )


def oxford_list(list_, conjunction='and'):
    return string_list(list_, conjunction, oxford=True)


def valid_level(level):
    if level == 'permissive':
        return 'loose'
    elif level is None:
        return 'strict'
    if not (level is None or level in ('strict', 'medium', 'loose')):
        raise ValueError(
            f'Type match level must be one of strict, medium, '
            f'or loose(/permissive), not {level}'
        )
    return level


def unicode_definite(s):
    return s.decode('UTF-8') if type(s) == bytes else s


def utf8_definite(s):
    return s if type(s) == bytes else s.encode('UTF-8')
