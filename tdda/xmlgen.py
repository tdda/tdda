"""
XML generation library (forked from tdda.utils).

Local fork to support:
- Modern Python conventions (snake_case aliases)
- Google-style docstrings
- Escaping control (entitize_quotes parameter)
"""

import re
import sys


UTF8 = 'UTF-8'


class XMLError(Exception):
    pass


def UTF8Definite(s):
    """
    Converts a string to UTF-8 if it is unicode.
    Otherwise just returns the string.
    """
    return s if type(s) == bytes else s.encode(UTF8)


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
        inputEncoding='UTF-8',
        headerAttr={},
        useHardTabs=True,
        float_precision=None,
        debug=False,
        altnbsp=None,
        hardTabs=True,
        entitize_quotes=True,
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
             data is in. Output encoding is always utf-8.

        If entitize_quotes is False, quotes and apostrophes in content
             are preserved literally instead of being converted to
             &apos; and &quot; entities. Default is True (escape quotes)."""

        self.indentLevel = indentLevel
        self.tabSize = tabSize
        self.pad = padEmptyElements
        self.stack = []
        self.html = html
        self._xmlbuf = ['']
        self.out = None
        self.tab = '\t' if useHardTabs else '        '
        self.float_precision = float_precision
        self.float_fmt = (
            ('%%.%df' % float_precision) if float_precision else None
        )
        self.altnbsp = None
        self.debug = debug
        self.hardTabs = hardTabs
        self.entitize_quotes = entitize_quotes
        if output:
            self.output = output
            if output.lower() == 'stdout':
                self.out = sys.stdout
            elif output:
                self.out = open(self.output, 'wb')
        if indentLevel == 0 and not (omitHeader):
            extraAttr = ''
            if html == 5:
                self._xmlbuf.append('<!DOCTYPE html>\n')
            else:
                if headerAttr:
                    extraAttr = ''.join(
                        [
                            ' %s="%s"' % (key, headerAttr[key])
                            for key in headerAttr.keys()
                        ]
                    )
                self._xmlbuf.append(
                    '<?xml version="1.0" encoding="UTF-8"%s?>\n' % extraAttr
                )
        self.inputEncoding = inputEncoding

        if self.html:
            html_attrs = {'lang': 'en'} if html == 5 else {}
            self.write_element('html', '', html_attrs, leave='open')
            if title or css or html == 5:
                self.write_element('head', leave='open')
                if html == 5:
                    self.write_element('meta', '', {'charset': 'UTF-8'})
                    self.write_element(
                        'meta',
                        '',
                        {
                            'name': 'viewport',
                            'content': 'width=device-width, initial-scale=1.0',
                        },
                    )
                if title:
                    self.write_element('title', title)
                if css:
                    if type(css) in (list, tuple):  # list of URLs
                        for c in css:
                            self.write_element(
                                'link',
                                '',
                                {'rel': 'stylesheet', 'href': c},
                                entitize=0,
                            )
                    else:  # in-line CSS
                        self.write_element(
                            'style', css, {'type': 'text/css'}, entitize=0
                        )
                self.close_element('head')
            self.write_element('body', leave='open')

        if xsl:
            self.write_pi('xml-stylesheet', {'href': xsl, 'type': 'text/xsl'})

        if content.lower() in ('xml', 'html', 'text'):
            self.contentType = 'Content-Type: text/%s\n' % content.lower()
        elif content == '':
            self.contentType = ''
        else:
            raise XMLError('Unknown content type "%s"' % content)

    def latin_safe(self, S):
        """Remove characters in Latin-1 control character range (128-159)."""
        o = []
        for s in S:
            n = ord(s)
            if n < 128 or n >= 160:
                o.append(s)
        return ''.join(o)

    def flush(self):
        """Write buffered XML to output file if configured."""
        if self.out:
            self.out.write(UTF8Definite(self.xml(flushing=True)))
            self._xmlbuf = []

    def _entitize(self, s, entitize=1):
        """Convert string to XML entities using instance settings.

        Wrapper around xml_entitize() that uses self.entitize_quotes.

        Args:
            s (str): String to entitize
            entitize (int): Entitization level (1 or 2+). Default 1

        Returns:
            str: String with XML entities applied.
        """
        return xml_entitize(
            s,
            entitize=entitize,
            altnbsp=self.altnbsp,
            entitize_quotes=self.entitize_quotes,
        )

    def write_element(
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
        """Write an XML/HTML element with optional content and attributes.

        Args:
            name (str): Element name (e.g., 'div', 'p', 'span')
            content (str): Element content. Default ''
            attributes (dict): Element attributes as key/value pairs.
                Default {}
            leave (str): 'close' to close element immediately, 'open' to
                leave open for nested content. Default 'close'
            entitize (int): Entitization level. 1 for basic (<>&),
                2+ also converts <= and >=. Default 1
            convertWS (int): Whitespace conversion (unused). Default 0
            link (str): URL to wrap content in <a> tag. Default ''
            convertNL (int): Convert newlines to <br/>. Bit flags:
                1 for \\n, 2 for literal newlines. Default 0
            tight (bool): If True, suppress indentation and newlines
                for inline elements. Default False
            forceNL (bool): Force newline before opening tag.
                Default False
            openclose (bool): Force <tag></tag> format for empty
                elements instead of <tag/>. Default False

        Side-effects:
            Appends element to output buffer. If leave='open', pushes
            element onto stack. Flushes output if file handle configured.
        """
        if type(content) == bytes:
            content = content.decode(self.inputEncoding)
        # In HTML mode, non-void elements should use open/close tags even
        # when empty
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
        # Check if parent element (on stack) is tight
        parent_is_tight = False
        if self.stack:
            parent_tuple = self.stack[-1]
            if isinstance(parent_tuple, tuple):
                _, parent_is_tight = parent_tuple

        # Only suppress indentation if BOTH this element is tight AND parent is tight
        suppress_indent = tight and parent_is_tight

        self._xmlbuf.append(
            xml_element(
                name,
                content,
                attributes,
                leave=leave,
                entitize=entitize,
                convertWS=0,
                link='',
                convertNL=convertNL,
                indent='' if suppress_indent else self._indent_string(),
                openclose=openclose,
                entitize_quotes=self.entitize_quotes,
            )
        )
        if leave != 'close':
            self._push(name, tight)
        self.flush()

    def open_element(
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
        """Open an element for writing nested content.

        Convenience wrapper for WriteElement(..., leave='open').
        Use this when you want to write nested elements inside this one.
        Must be paired with CloseElement() later.

        Args:
            name (str): Element name
            content (str): Optional content before nested elements
            attributes (dict): Element attributes
            entitize (int): Entitization level (1 or 2+)
            convertWS (int): Whitespace conversion (unused)
            link (str): URL to wrap content in <a> tag
            tight (bool): Suppress indentation/newlines for inline
            forceNL (bool): Force newline before opening tag

        Side-effects:
            Pushes element onto stack. Must call CloseElement() later.
        """
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

    def write_cd_element(
        self, name, content='', attributes={}, leave='close', urlsafe=0
    ):
        """Write an element with CDATA section for content.

        Args:
            name (str): Element name
            content (str): Content to wrap in <![CDATA[...]]>. Default ''
            attributes (dict): Element attributes. Default {}
            leave (str): 'close' or 'open'. Default 'close'
            urlsafe (int): URL-safe encoding (not supported). Default 0

        Raises:
            XMLError: If urlsafe is non-zero (not supported in this fork).

        Side-effects:
            Appends element to output buffer. If leave='open', pushes
            element onto stack.
        """
        indent = self._indent_string()
        self._xmlbuf.append(indent + '<' + self.toString(name))
        if attributes:
            self.WriteAttributes(attributes)
        self._xmlbuf.append('>')
        if urlsafe:
            raise XMLError('urlsafe WriteCDElement not supported')
        else:
            # Note: UnicodeDefinite not included in this fork
            # (WriteCDElement not used by CheckEagle)
            self._xmlbuf.append('<![CDATA[' + content + ']]>')
        if leave == 'close':
            self._xmlbuf.append('</' + name + '>\n')
        else:
            self._push(name)
        self.flush()

    def write_pi(self, name, attributes={}):
        """Write an XML processing instruction.

        Args:
            name (str): Processing instruction name (e.g., 'xml-stylesheet')
            attributes (dict): PI attributes/pseudo-attributes. Default {}

        Side-effects:
            Appends processing instruction to output buffer.
        """
        self._xmlbuf.append('<?' + name)
        if attributes:
            self.WriteAttributes(attributes)
        self._xmlbuf.append('?>\n')

    def _indent_string(self):
        """Generate indentation string for current nesting level.

        Returns:
            str: Spaces or tabs for current indentation level.
        """
        if self.hardTabs:
            return self.tab * (
                (self.indentLevel * self.tabSize) // 8
            ) + ' ' * ((self.indentLevel * self.tabSize) % 8)
        else:
            return ' ' * (self.indentLevel * self.tabSize)

    def _push(self, name, tight=False):
        """Push element onto stack and increase indentation.

        Args:
            name (str): Element name to push
            tight (bool): If True, don't add newline. Default False

        Side-effects:
            Increments indentLevel, pushes (name, tight) tuple onto stack,
            optionally adds newline to output buffer.
        """
        if not tight:
            self._xmlbuf.append('\n')
        self.indentLevel += 1
        self.stack.append((name, tight))

    def write_content(
        self, content, leave='open', force=False, tight=False, entitize=False
    ):
        """Write content to a currently open element.

        Args:
            content (str): Content to write
            leave (str): 'open' to leave element open, 'close' to close
                after writing content. Default 'open'
            force (bool): If True, allow writing even if no element is
                open. Default False
            tight (bool): If True, suppress indentation (for inline
                content). Default False
            entitize (bool): If True, apply XML entity escaping to
                content using self._entitize(). Respects the
                self.entitize_quotes setting. Default False

        Raises:
            XMLError: If no element is open and force=False.

        Side-effects:
            Appends content to output buffer. If leave='close', closes
            the current element.
        """
        if not force and self.indentLevel < 1:
            raise XMLError('No element open for writing')
        if content:
            c = self._entitize(content) if entitize else content
            # Check if current element is tight (from stack)
            current_is_tight = False
            if self.stack:
                current_tuple = self.stack[-1]
                if isinstance(current_tuple, tuple):
                    _, current_is_tight = current_tuple
            # Suppress indentation if tight parameter OR current element is tight
            if tight or current_is_tight:
                self._xmlbuf.append(c)
            else:
                self._xmlbuf.append(self._indent_string() + c)
        if leave == 'close':
            self.close_element()

    def add_balanced_xml(self, xml):
        """Add a balanced XML section to the output.
        It is the caller's responsibility to ensure that the XML
        delivered is balanced, well-formed, in situ etc: this function
        just appends it to the output."""
        self._xmlbuf.append(xml if type(xml) == str else xml.decode('UTF-8'))

    def close_element(self, element=None, tight=False, forceNL=False):
        """Close an element previously opened with OpenElement.

        Args:
            element (str): Optional element name to verify we're closing
                the right element. If provided, raises XMLError if it
                doesn't match the most recently opened element. Default None
            tight (bool): Deprecated - tight state is now tracked on stack.
                This parameter is ignored. Default False
            forceNL (bool): Force newline before closing tag (only used
                when tight=False). Default False

        Raises:
            XMLError: If no element is open, or if element name doesn't
                match the most recently opened element.

        Side-effects:
            Pops element from stack, decrements indent level, appends
            closing tag to output buffer.
        """
        if self.indentLevel < 1:
            raise XMLError('No element open for closing')
        self.indentLevel -= 1
        stored_tuple = self.stack.pop()
        # Handle both old (string) and new (tuple) stack formats
        if isinstance(stored_tuple, tuple):
            stored_name, was_tight = stored_tuple
        else:
            stored_name, was_tight = stored_tuple, False
        if element:
            if str(element) != stored_name:
                info = '\n'.join([''] + self._xmlbuf) if self.debug else ''
                raise XMLError(
                    'Attempt to close %s with %s%s'
                    % (stored_name, element, info)
                )

        # Check if parent element (still on stack) is tight
        parent_is_tight = False
        if self.stack:
            parent_tuple = self.stack[-1]
            if isinstance(parent_tuple, tuple):
                _, parent_is_tight = parent_tuple

        if was_tight:
            # Element was opened with tight=True: no indentation before </tag>
            # Add newline after ONLY if parent is not tight
            if parent_is_tight:
                self._xmlbuf.append('</' + stored_name + '>')
            else:
                self._xmlbuf.append('</' + stored_name + '>\n')
        else:
            # Element was opened with tight=False: indentation before </tag>, newline after
            self.ForceNL(forceNL)
            self._xmlbuf.append(
                self._indent_string() + '</' + stored_name + '>\n'
            )
        self.flush()

    def force_nl(self, forceNL):
        """Add newline to output buffer if needed and forceNL is True.

        Args:
            forceNL (bool): If True and buffer doesn't end with newline,
                add one.
        """
        if forceNL and self._xmlbuf and not self._xmlbuf[-1].endswith('\n'):
            self._xmlbuf.append('\n')

    def close_all_open(self):
        """Close all open elements (for error recovery)."""
        while self.indentLevel > 0:
            self.close_element()

    def close_xml(self, forceTidy=0):
        """Finalize and close the XML document.

        Args:
            forceTidy (int): If non-zero, close all open elements
                automatically. If zero, raises XMLError if elements
                remain open. Default 0

        Raises:
            XMLError: If forceTidy=0 and elements remain open.

        Side-effects:
            Closes HTML body/html if in HTML mode. Flushes output.
            Closes output file if one was opened.
        """
        if forceTidy:
            self.CloseAllOpen()
        else:
            if self.html:
                self.close_element('body')
                self.close_element('html')
            if self.indentLevel != 0:
                raise XMLError(
                    'Attempt to terminate open XML '
                    '(items remaining %s)' % str(self.stack)
                )
        self.flush()
        if self.out and self.out != sys.stdout:
            self.out.close()

    def write_attributes(self, attributes):
        """Append formatted attributes to output buffer.

        Args:
            attributes (dict): Attributes to write.
        """
        self._xmlbuf.append(f' {xml_attributes(attributes)}')

    def write_comment(self, comment, padlines=1):
        """Write an XML comment with optional padding.

        Args:
            comment (str or list): Comment text. If list, formats as
                multi-line comment with first line and subsequent lines
                indented. Default behavior is single-line comment
            padlines (int): Number of blank lines before and after
                comment. Default 1

        Side-effects:
            Appends comment to output buffer with padding newlines.
        """
        padding = '\n' * padlines
        indent = self._indent_string()
        if type(comment) == list:
            if len(comment) > 0:
                c = comment[0].replace('--', '- - ')
                self._xmlbuf.append('%s%s<!-- %s\n' % (padding, indent, c))
                indent = '%s%s' % (indent, ' ' * 5)
                for i, cl in enumerate(comment[1:]):
                    c = cl.replace('--', '- - ')
                    if i == len(comment) - 2:  # last
                        end = ' -->\n%s' % padding
                    else:
                        end = '\n'
                    self._xmlbuf.append('%s%s%s' % (indent, c, end))

        else:
            c = comment.replace('--', '- - ')
            self._xmlbuf.append(
                '%s%s<!-- %s -->%s\n'
                % (padding, self._indent_string(), comment, padding)
            )

    def __str__(self):
        s = 'indent level = %d\n' % self.indentLevel
        s = 'indentation size = %d' % self.tabSize
        s += 'stack = %s\n' % self.stack
        s += 'xml = \n' + self.xml()
        return s

    def xml(self, flushing=False):
        """Return XML output as string.

        Args:
            flushing (bool): If True, allow returning XML even if
                elements are still open (for incremental output).
                If False, raises XMLError if elements remain open.
                Default False

        Returns:
            str: Complete XML output from buffer.

        Raises:
            XMLError: If flushing=False and elements remain open.
        """
        if self.indentLevel > 0 and not flushing:
            raise XMLError('Elements still open: %s.' % ', '.join(self.stack))
        return ''.join(self._xmlbuf)

    def to_string(self, v):
        """Convert value to string using configured encoding and formatting.

        Args:
            v: Value to convert. Can be str, bytes, float, or other type

        Returns:
            str: String representation of value. Floats are formatted
                using configured precision if set.
        """
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

    # CamelCase aliases for backward compatibility
    LatinSafe = latin_safe
    Flush = flush
    WriteElement = write_element
    OpenElement = open_element
    WriteCDElement = write_cd_element
    WritePI = write_pi
    WriteContent = write_content
    AddBalancedXML = add_balanced_xml
    CloseElement = close_element
    ForceNL = force_nl
    CloseAllOpen = close_all_open
    CloseXML = close_xml
    WriteAttributes = write_attributes
    WriteComment = write_comment
    toString = to_string


def xml_entitize(s, entitize=1, altnbsp=None, entitize_quotes=True):
    """Convert special characters to XML entities.

    Args:
        s (str): String to entitize
        entitize (int): Entitization level. 1 converts &, <, >.
            Values >1 also convert <= to &#x2264; and >= to &#x2265;.
            Default 1
        altnbsp: Alternative non-breaking space handling (unused in
            CheckEagle fork). Default None
        entitize_quotes (bool): If True, convert ' to &apos; and " to
            &quot;. If False, preserve quotes literally. Default True

    Returns:
        str: String with special characters converted to XML entities.
    """
    s = re.sub('&', '&amp;', s)
    s = re.sub('<', '&lt;', s)
    s = re.sub('>', '&gt;', s)
    if entitize > 1:
        s = re.sub('&lt;=', '&#x2264;', s)
        s = re.sub('&gt;=', '&#x2265;', s)
    if entitize_quotes:
        s = re.sub("'", '&apos;', s)
        s = re.sub('"', '&quot;', s)
    if altnbsp:
        # Note: self.nbsp not available in module-level function
        # This parameter is not used by CheckEagle
        pass
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
    entitize_quotes=True,
):
    """Generate an XML element as a string.

    Module-level function for creating XML elements. Called by
    XML.WriteElement() but can be used standalone.

    Args:
        name (str): Element name
        content (str): Element content. Default ''
        attributes (dict): Element attributes. Default {}
        leave (str): 'close' to close element, 'open' to leave open.
            Default 'close'
        entitize (int): Entitization level (1 or 2+). Default 1
        convertWS (int): Whitespace conversion (unused). Default 0
        link (str): URL to wrap content in <a> tag. Default ''
        convertNL (int): Convert newlines to <br/>. Bit flags: 1 for
            \\n, 2 for literal newlines. Default 0
        indent (str): Indentation string to prepend. Default ''
        forceNL (bool): Force newline before opening tag. Default False
        openclose (bool): Force <tag></tag> format for empty elements.
            Default False
        pad (int): If 1, pad empty elements with &#160;. Default 0
        entitize_quotes (bool): Pass to xml_entitize for content.
            Default True

    Returns:
        str: XML element as string, with newline if indent provided.
    """
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
        xmlc = xml_entitize(
            content, entitize=entitize, entitize_quotes=entitize_quotes
        )
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
