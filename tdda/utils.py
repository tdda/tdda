import datetime
import json
import math
import os
import re
import regex
import sys
import tomli_w
import types
import yaml


#jythonc needs explicit import of utf-8 and iso-8859-1/latin1 encoding packages
import encodings.aliases     # type:ignore
import encodings.utf_8
import encodings.ascii       # type:ignore
import encodings.latin_1     # type:ignore
import encodings.iso8859_1   # type:ignore


from collections import namedtuple

import numpy as np

import rich
rprint = rich.print
rich.reconfigure(highlight=False, soft_wrap=True)


TDDADIR = os.path.dirname(__file__)  # base tdda directory for package
CONSTRAINTSDIR = os.path.join(TDDADIR, 'constraints')
PDCONSTRAINTSDIR = os.path.join(CONSTRAINTSDIR, 'pd')
DBCONSTRAINTSDIR = os.path.join(CONSTRAINTSDIR, 'db')
CONSTRAINTSTESTDATADIR = os.path.join(CONSTRAINTSDIR, 'testdata')
TEMPLATESDIR = os.path.join(TDDADIR, 'templates')
REFTESTSDIR = os.path.join(TDDADIR, 'referencetest')

DEFAULT_INPUT_ENCODING = 'UTF-8'


class XMLError(Exception):
    pass


class XML:

    def __init__(self, indentLevel=0, tabSize=4, omitHeader=0,
                 output=None, html=0, xsl='', css=[],
                 title='', padEmptyElements=0, content='',
                 inputEncoding=DEFAULT_INPUT_ENCODING,
                 headerAttr={}, useHardTabs=True,
                 float_precision=None, debug=False,
                 altnbsp=None):
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
        self.float_fmt = (('%%.%df' % float_precision) if float_precision
                                                       else None)
        self.altnbsp = None
        self.debug = debug
        if output:
            self.output = output
            if output.lower() == 'stdout':
                self.out = sys.stdout
            elif output:
                self.out = open(self.output, 'wb')
        if indentLevel == 0 and not(omitHeader):
            extraAttr = ''
            if html == 5:
                self.xmlbuf.append('<!DOCTYPE html lang="en">\n')
            else:
                if headerAttr:
                    extraAttr = ''.join([' %s="%s"' % (key, headerAttr[key])
                                         for key in headerAttr.keys()])
                self.xmlbuf.append('<?xml version="1.0" encoding="UTF-8"%s?>\n'
                                   % extraAttr)
        self.inputEncoding = inputEncoding

        if self.html:
            self.WriteElement('html', leave='open')
            if title or css:
                self.WriteElement('head', leave='open')
                if html == 5:
                    self.WriteElement('meta', '', {'charset': 'UTF-8'})
                if title:
                    self.WriteElement('title', title)
                if css:
                    if type(css) in (list, tuple):  # list of URLs
                        for c in css:
                            self.WriteElement('style', '',
                                               {'type': 'text/css',
                                                'href': c,
                                                'rel': 'stylesheet'})
                    else:  # in-line CSS
                        self.WriteElement('style', css, {'type': 'text/css'})
                self.CloseElement('head')
            self.WriteElement('body', leave='open')

        if xsl:
            self.WritePI('xml-stylesheet', {'href': xsl,
                                             'type': 'text/xsl'})

        if content.lower() in('xml', 'html', 'text'):
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
            self.out.write(UTF8Definite(self.xml(flushing=True)))
            self.xmlbuf = []

    def Entitize(self, s, entitize=1, asUnicode=True):
        s = re.sub('&', '&amp;', s)
        s = re.sub('<', '&lt;', s)
        s = re.sub('>', '&gt;', s)
        if entitize > 1:
            s = re.sub('&lt;=', '&#x2264;', s)
            s = re.sub('&gt;=', '&#x2265;', s)
        s = re.sub(u"'", '&apos;', s)
        s = re.sub('"', '&quot;', s)
        if self.altnbsp:
            s = re.sub(self.nbsp, '&nbsp;', s)
        return self.toString(s) if asUnicode else s

    def WriteElement(self, name, content='', attributes={},
                     leave='close', entitize=1, convertWS=0,
                     link='', convertNL=0, tight=False, forceNL=False,
                     openclose=False):
        # convertNL: binary field:
        #   0  to ignore newlines
        #   *1 to convert backslash n (r'\n') to <br/>
        #   1* to convert inline newline '\n' to <br/>
        indent = '' if tight else self.IndentString()
        if content is None:
            print('WARNING: null content for element %s' % name,
                  file=sys.stderr)
            content = ''
        else:
            content = self.toString(content)
        self.ForceNL(forceNL)
        self.xmlbuf.append(indent + '<' + self.toString(name))
        if attributes:
            self.WriteAttributes(attributes)
        if content == '' and leave == 'close':
            if openclose:
                self.xmlbuf.append('></%s>%s' % (self.toString(name),
                                                  '' if tight else '\n'))
            else:
                self.xmlbuf.append('/>' if tight else '/>\n')
        else:
            self.xmlbuf.append('>')
        if link:
            self.xmlbuf.append('<a href="%s">' % link)
        if (re.match('^[ \t]+$', content)
                    or (self.pad and content == '' and leave == 'close')):
            xmlc = '&#160;'
        elif entitize:
            xmlc = self.Entitize(content, entitize)
        else:
            xmlc = content
        if convertNL & 1:
            xmlc = xmlc.replace('\\n', '<br/>')
        if convertNL & 2:
            xmlc = xmlc.replace('\n', '<br/>')
        if xmlc:
            self.xmlbuf.append(xmlc)
        if link:
            self.xmlbuf.append('</a>')
        if leave == 'close':
            if content != '':
                self.xmlbuf.append('</' + self.toString(name)
                                   + ('>' if tight else '>\n'))
        else:
            self.Push(name, tight)
        self.Flush()

    def OpenElement(self, name, content='', attributes={},
                         leave='close', entitize=1, convertWS=0,
                         link='', tight=False, forceNL=False):
        self.WriteElement(name, content, attributes, 'open',
                          entitize, convertWS, link, tight=tight,
                          forceNL=forceNL)

    def WriteCDElement(self, name, content='', attributes={},
                        leave='close', urlsafe=0):
        indent = self.IndentString()
        self.xmlbuf.append(indent + '<' + self.toString(name))
        if attributes:
            self.WriteAttributes(attributes)
        self.xmlbuf.append('>')
        if urlsafe:
            self.xmlbuf.append('<![CDATA['
                               + str(encode_uri_component(content))
                               + ']]>')
        else:
            content = UnicodeDefinite(content)
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
        return (self.tab * ((self.indentLevel * self.tabSize) // 8)
                + ' ' * ((self.indentLevel * self.tabSize) % 8))

    def Push(self, name, tight=False):
        if not tight:
            self.xmlbuf.append('\n')
        self.indentLevel += 1
        self.stack.append(name)

    def WriteContent(self, content, leave='open', force=False, tight=False,
                     entitize=False):
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
        self.xmlbuf.append(xml if type(xml) == str
                               else xml.decode('UTF-8'))

    def CloseElement(self, element=None, tight=False, forceNL=False):
        if self.indentLevel < 1:
            raise XMLError('No element open for closing')
        self.indentLevel -= 1
        stored = self.stack.pop()
        if element:
            if str(element) != stored:
                info = '\n'.join([''] + self.xmlbuf) if self.debug else ''
                raise XMLError('Attempt to close %s with %s%s'
                               % (stored, element, info))
        if tight:
            self.xmlbuf.append('</' + stored + '>')
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
                raise XMLError('Attempt to terminate open XML '
                                    '(items remaining %s)'
                                        % str(self.stack))
        self.Flush()
        if self.out and self.out != sys.stdout:
            self.out.close()

    def WriteAttributes(self, attributes):
        if type(attributes) == type({}):
            for a in attributes:
                val = attributes[a]
                if type(val) is bytes:
                    val = str(val, self.inputEncoding, 'ignore')
                if type(a) is bytes:
                    a = str(a, self.inputEncoding, 'ignore')
                self.xmlbuf.append(' %s="%s"' % (self.toString(a),
                                   self.Entitize(self.toString(val))))
        else:   # tuple
            for (k, v) in attributes:
                self.xmlbuf.append(' %s="%s"'
                                   % (self.toString(k),
                                      self.Entitize(self.toString(v))))

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
            self.xmlbuf.append('%s%s<!-- %s -->%s\n' % (padding,
                                                     self.IndentString(),
                                                     comment, padding))

    def __str__(self):
        s = 'indent level = %d\n' % self.indentLevel
        s = 'indentation size = %d' % self.tabSize
        s += 'stack = %s\n' % self.stack
        s += 'xml = \n' + self.xml()
        return s

    def xml(self, flushing=False):
        if self.indentLevel > 0 and not flushing:
            raise XMLError('Elements still open: %s.'
                           % ', '.join(self.stack))
        return ''.join(self.xmlbuf)

    def toString(self, v):
        if type(v) is str:
            return v
        elif type(v) is bytes:
            return str(v, self.inputEncoding, 'ignore')
        elif type(v) is float and self.float_fmt is not None:
            s = str(self.float_fmt % v)
            while (s.endswith('0') and not len(s) == 1
                   and not s.endswith('.0')):
                s = s[:-1]
            if s.endswith('.0') and len(s) > 2:
                s = s[:-2]
            return s
        else:
            return str(v)


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
            d[f'n_{self.items}'] = self.n_passes + self.n_failures,

        if pc:
            d.update({
                'pass_rate': to_pc(self.pass_rate),
                'failure_rate': to_pc(self.failure_rate)
            })
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
    return base + new_ext


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
    if v is np.nan:
        return None
    elif v is None or type(v) in (str, int, float, bool):
        return v
    elif type(v) in (list, tuple):
        return [json_sanitize(u) for u in v]
    elif isinstance(v, dict):
        return {str(k): str(u) for k, u in v.items()}
    else:
        s = str(v)
        return s[:-9] if s.endswith('00:00:00') else s  # slightly dodgy


def strip_lines(s):
    """
    Splits the given string into lines (at newlines), strips trailing
    whitespace from each line before rejoining.

    Is careful about last newline.
    """
    end = '\n' if s.endswith('\n') else ''
    return '\n'.join([line.rstrip() for line in s.splitlines()]) + end


def ok_field_name(field, constraint, name_map=None):
    if name_map:
        return f'{field}_{name_map[constraint]}_ok'
    else:
        return f'{field}_{constraint}_ok'


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


def print_obj(o, rex=None, invert=False, as_repr=False, keys_only=False):
    """
    Print the __dict__ from o in the form:

        key (type(value)): value

    If rex is provided, print only keys matching rex.

    If invert is set to True, use rex to exclude rather than include keys.

    If as_repr is set, use repr(.) instead of str(.) for formatting value.
    """
    if rex:
        r = re.compile(rex) if rex else None
        if invert:
            for k, v in o.__dict__.items():
                if not re.match(r, k):
                    print_item(k, v, as_repr, keys_only)
        else:
            for k, v in o.__dict__.items():
                if re.match(r, k):
                    print_item(k, v, as_repr, keys_only)
    else:
        for k, v in o.__dict__.items():
            print_item(k, v, as_repr, keys_only)


def print_item(k, v, as_repr=False, keys_only=False):
    f = repr if as_repr else lambda x: x
    if keys_only:
        print(f'{k} ({type(v)})')
    else:
        print(f'{k} ({type(v)}): {f(v)}')


def n_glyphs(s):
    """
    Returns the number of glyphs in a string.
    """
    return len(regex.findall(r'\X', s))


def tddadir(path):
    """
    Returns the full path to path where path is in the base tdda directory
    """
    return os.path.join(TDDADIR, path)


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
        return json.dumps(v)
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


class Dummy(object):
    """
    A dummy object. For whatever.
    """
    def __init__(self, **kwargs):
        for k in kwargs:
            self.__dict__[k] = kwargs[k]

    def to_dict(self):
        return self.__dict__


def cprint(*args, colour=None, **kw):
    if isinstance(colour, dict):
        colour = colour.get('colour', None)
    if colour is True:
        rprint(*args, **kw)
    else:
        print(*args, **kw)
