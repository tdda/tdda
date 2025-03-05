import os
import regex as re

from collections import OrderedDict, namedtuple

from tdda.utils import XML


RE_FLAGS = re.UNICODE | re.DOTALL
URL_RE = re.compile(r'^(http://|https://|file://).+$', RE_FLAGS)
GRAPH_RE = re.compile(r'^graph://.+$', RE_FLAGS)
MARKDOWN_URL_RE = re.compile(r'^\s*\[(.+)\]\((.+)\)\s*$', RE_FLAGS)

COL_HEAD_COLOUR = '#E0E0E0'
ROW_HEAD_COLOUR = '#A8A8A8'

HTML_REPEAT_HEADERS = False


class Dummy:
    pass


ColWidthInfo = namedtuple('ColWidthInfo', 'data header word tex')


def colour_class(fn):
    fns = OrderedDict((
        ('rgb', rgb_bool),
        ('zred', z_red),
        ('nzred', nz_red),
        ('nzgreen', nz_green),
        ('n1red', n1_red),
        ('nnsred', nns_red),
        ('rankred', ranking_red),
        ('tt', tt),
    ))
    cls = fns.get(fn)
    if fn is not None and fn != 'None' and cls is None:
        raise Exception(('Unknown text colour function %s.\n'
                               'Functions available:\n' % fn)
                              + ('\n'.join('    %s: %s' % (k, v.__doc__)
                                           for (k, v) in fns.items())))
    return cls


class Table:
    def __init__(self, header, rows, colourSpec=None,
                 fixedCellColourSchemes=None,
                 transpose=False, groupHeader=None, shortlinks=False,
                 repeatHeader=0, colHeadPadding=None, colPadding=None,
                 gridlines=0, session=None,
                 commonHeadColour=False, forceBGColour=False,
                 attr=None,
                 command=None, justify=None, cellClasses=None,
                 cellClassFns=None,
                 structuredHeader=None, colourCells=True, htmlrows=None,
                 headerHovers=None, nColsAsRowHeaders=0,
                 tddaMetadata=None, truncatedRecords=0,
                 colSeps=None, onelineheader=None, colTypes=None, name=None,
                 emptyIfEmpty=False, rawValues=None, cellColourerOffsets=None,
                 footnote=None, tt=False, texParaHeaders=False):
        """
        A general table, with (optional) column headers but no row headers.

        header       optional list of headers (as strings) (None or [] to omit)

        rows         list of lists of (formatted) row values

        colourSpec is normally None, which maps to rainbow colours
        starting from red

        fixedCellColourSchemes is a hash specifying particular column numbers
        that must be coloured using particular schemes.   It's indexed from
        zero.

        transpose, if true, causes columns and rows to be swapped

        groupHeader allows a second level of header to be added above the
        regular column headers, typically grouping columns

        shortlinks, if true, causes only the last part of URLs to be shown
        in tables (the anchor still points to the full URL)

        repeatHeader is an integer: if set to N, the header is repeated
        after every group of N ordinary rows.

        colHeadPadding is a list of numbers between 1 and 8, one for each
        column, specifying how much to pad the column header by. This is used
        to force columns to be wider than they otherwise would.

        colPadding is a list of numbers between 1 and 8, one for each
        column, specifying how much to pad the column by.

        gridlines affects text table formatting. If set to 1, tight
        ASCII row and column separators are drawn; if set to 2,
        padded ASCII row and column separators are drawn.

        session is the session drawing the table; used for better error
        reporting

        commonHeadColour controls the colouring of the group header,
        if there is one.

        forceBGColour allows background-colouring of columns without
        text colouring; by default, if there are any columns with text
        colouring, then there is no background colour anywhere.

        attr in an optional dictionary of attributes to add to the table.
        (This will override sortable and scrollable.)

        command indicates that cell contents are to be formatted as
        preformatted

        justify: none for default justification (right), but can be set
        to any of 'l', 'c' or 'r' for left, centred or right-justified cells.

        cellClasses: An optional list of lists matching the dimensions of
        values. If this is present, any attributes present will be added
        as class tags the relevant td tags on the coloured HTML output.

        cellClassFns: An optional list of names of functions, one per column.
        Any non-None values wil be taken as names of functions to call on the
        (unformatted) value of the cell to compute its CSS class.
        At the moment, 'rgb' is the only allowed function.

        structuredHeader is a list of lists of the form
            [[nCols1, nRows1, groupHead1], [nCols2, nRows2, groupHead2], ...]
        where normally sum(nCols#) = len(header).
        These sit above the normal header.
        If nRows > 1, the header should be shorter.

        htmlrows: pre-formatted (raw) HTML values; used by rex.

        headerHovers: optional list of hover-text values for headers

        nColsAsRowHeaders: number of extra columns to use as row headers

        tddaMetadata: extra parameters passed to cellClassFunctions,
        when used.

        truncateRecords: when non-zero, a message is added below the
        table indicating the number of records omitted from the table.

        colSeps is an optional dictionary of columns before which a column
        separator should be inserted. The keys should be integers, with
        0 meaning insert a separator column before the first column (0),
        and N meaning insert a column after the last column if the table
        has N columns. (Of course, values between 1 and N - 1 would be more
        usual.) The value is reserved to specify the kind of separator,
        but for the moment should just be non-null.

        colTypes is an optional list of column types. This is required
        for conversion to Excel.

        name is optional; currently used by Excel conversion.

        emptyIfEmpty: if set, when tehre are no rows, the table returns
        an empty string for toString, and toHTML.

        tt: forces typewriter type (monospace)
        """
        self.colHeadAttr = ('bgcolor', ROW_HEAD_COLOUR if commonHeadColour
                                                       else COL_HEAD_COLOUR)
        self.rowHeadAttr = ('bgcolor', ROW_HEAD_COLOUR)
        self.annotation = ['']
        self.header = header or []
        self.headerHovers = headerHovers
        self.rows = rows or []
        self.attr = attr
        self.command = command  # used for commands
        self.justify = justify  # usually None, meaning default rules
        self.colourCells = False
        self.forceBGColour = forceBGColour
        self.forcedMinMax = {}    # Used to force a modified colour scale
        self.transpose = transpose
        self.groupHeader = groupHeader
        self.shortlinks = shortlinks
        self.repeatHeader = repeatHeader
        self.colHeadPadding = colHeadPadding
        self.colPadding = colPadding
        self.gridlines = gridlines  # text only. 1 for tight, 2 for spaced
        self.cellClasses = cellClasses
        self.cellClassFns = cellClassFns
        self.structuredHeader = structuredHeader
        self.oneLineHeader = onelineheader
        self.htmlrows = htmlrows  # Usually None, except for preformatted
        self.nColsAsRowHeaders = nColsAsRowHeaders  # number of cols to use as
                                                    # extra headers
        self.tddaMetadata = tddaMetadata or {}
        self.truncatedRecords = truncatedRecords
        self.colSeps = colSeps or {}
        self.colTypes = colTypes
        self.name = name
        self.emptyIfEmpty = emptyIfEmpty
        self.rawValues = rawValues  # used by Excel if present
        self.graphWidth = 200  # can be changed externally
        self.cellColourerOffsets = cellColourerOffsets
        self.footnote = footnote
        self.tt = tt

    def SortByRowHeader(self, reverse=False):
        """Sorts table by row header"""
        if len(self.rows) == 0:
            raise Exception('Table contains no sortable values')

        h = sorted(zip([c[0] for c in self.rows], self.rows, self.cellValues))
        h = list(reversed(h) if reverse else h)
        self.rows = [row[1] for row in h]
        self.cellValues = [row[2] for row in h]

    def DeleteLastRow(self):
        self.rows = self.rows[:-1]
        self.cellValues = self.cellValues[:-1]

    def Invert(self):
        self.rows = list(reversed(self.rows))
        self.cellValues = list(reversed(self.cellValues))

    def AddIndex(self, colName='Index', first=1):
        self.header = [colName] + self.header
        self.rows = [[f'{i + first:,}'] + row
                                for i, row in enumerate(self.rows)]

        self.cellValues = [[i + first] + vals
                                for i, vals in enumerate(self.cellValues)]

    def Annotate(self, annotation):
        if type(annotation) == str:
            self.annotation.append(annotation)
        elif type(annotation) == list:
            self.annotation.extend(annotation)
        else:
            raise Exception('Unexpected annotation')

    def toString(self, format=True, transpose=False):
        # What would be required to make this stuff handle newlines
        # properly? And what would that mean?
        #   1. First (simplest) thing would be just to make newlines cause
        #      a wrap to the right place (without shrinking the col width).
        #      A necessary part of this (I think) is to know that this is
        #      happening so that the next column starts on the right line,
        #      and all the continuations line up etc.
        #   2. Second thing would be to shrink the column width
        #   3. Third thing might be to do wrapping to specified widths.
        #   4. A slightly separate issue is that once lines can be split,
        #      row (and column?) separators potentially become more important.
        # Let's tackle these one at a time.
        #   Done: 1, 2, 4.

        if self.isEmpty(self.emptyIfEmpty):
            return ''
        s = []
        nCols = self.NCols()

        transpose = self.transpose or transpose
        u2Drows, colWidths = self.ProcessMultilineStrings(transpose)
        header = self.header
        if self.structuredHeader and self.oneLineHeader:
            header = self.oneLineHeader
        uHeader = header if not transpose else []
        if uHeader:
            headerWidths = [len(h) for h in uHeader]
            fullColWidths = [max(h, c) for h, c in zip(headerWidths,
                                                       colWidths)]
        else:
            fullColWidths = colWidths

        if format:
            sep = ' '
            if self.gridlines:
                sep = '|' if self.gridlines == 1 else ' | '
                pad = 2 if self.gridlines == 2 else 0
                interline = '+%s+' % '+'.join('-' * (c + pad)
                                                for c in fullColWidths)
                pre = '|' if self.gridlines == 1 else '| '
                post = '|' if self.gridlines == 1 else ' |'
            if self.groupHeader is not None and not transpose:
                tableWidth = sum(colWidths) + nCols - 1
                ghw = len(self.groupHeader)
                if tableWidth > ghw:
                    fmt = str(ColWithinColFormat(tableWidth,
                                                             ghw, 'c'))
                else:
                    fmt = '%s'
                s.append(fmt % self.groupHeader)

            if uHeader:
                headerFormat = ['%%%ds' % w for w in colWidths]
                just = [self.justify or 'r'] * len(colWidths)
                colFormat = [str(ColWithinColFormat(h, c, j))
                             for h, c, j in zip(headerWidths, colWidths, just)]
                if self.gridlines:
                    s.append(interline)
                line = sep.join(f % h for f, h in zip(headerFormat, uHeader))
                if self.gridlines:
                    s.append(pre + line + post)
                else:
                    s.append(line)
            else:
                sign = '-' if self.justify == 'l' else ''
                sign = [sign] * len(colWidths)
                colFormat = ['%%%s%ds' % (sf, w) for sf, w in zip(sign,
                                                                   colWidths)]
            for row2D in u2Drows:
                if self.gridlines:
                    s.append(interline)
                nOutRows = ((max(len(rows) for rows in row2D) if row2D else 1)
                             or 1)
                z = list(zip(colFormat, row2D))
                for i in range(nOutRows):
                    line = sep.join(f % (c[i] if len(c) > i else '')
                                    for f, c in z)
                    if self.gridlines:
                        s.append(pre + line + post)
                    else:
                        s.append(line)
            if self.gridlines:
                s.append(interline)
        else:
            sep = ' '
            if transpose:  # *** SEE ABOVE (HACK)
                raise Exception('No unformatted transpose Table.toString')
            else:
                if self.groupHeader is not None:
                    s.append(self.groupHeader)
                if uHeader:
                    s.append(sep.join(uHeader))
                for row in self.rows:
                    s.append(sep.join(row))

        if len(self.annotation) > 1:
            s.extend([str(a) for a in self.annotation])

        if self.footnote:
            s.append('')
            s.append(self.footnote)
        try:
            return str('\n'.join(s))
        except:  # pragma: no cover
            print(s)
            print([type(S) for S in s])
            raise

    def toMarkdown(self, format=True, transpose=False,
                   flavour='github', pretty=True):
        """
        Creates a markdown version of the table
        """
        assert flavour in ('github', 'mmd')
        if self.isEmpty(self.emptyIfEmpty):
            return ''
        s = []
        nCols = self.NCols()
        if pretty:
            pre, sep, post = ('| ', ' | ', ' |')
        else:
            pre = sep =  post = '|'
        justify = self.justify or 'r'  # for now

        transpose = self.transpose or transpose

        u2Drows, colWidths = self.ProcessMultilineStrings(transpose)
        header = self.header
        if self.structuredHeader and self.oneLineHeader:
            header = self.oneLineHeader
        uHeader = header if not transpose else []
        if uHeader:
            headerWidths = [len(h) for h in uHeader]
            fullColWidths = [max(h, c) for h, c in zip(headerWidths,
                                                       colWidths)]
            fullColWidths = [max(3, f) for f in fullColWidths]
        else:
            fullColWidths = colWidths

        if flavour == 'mmd':
            inner = sep.join(mmd_justify_marker(c, justify)
                             for c in fullColWidths)
        else:  # currently flavour == 'github':
            inner = sep.join('-' * c for c in fullColWidths)
        interline = pre + inner + post
        if format:
            if self.groupHeader is not None and not transpose:
                tableWidth = sum(colWidths) + nCols - 1
                ghw = len(self.groupHeader)
                if tableWidth > ghw:
                    fmt = ColWithinColFormat(tableWidth, ghw, 'c')
                else:
                    fmt = '%s'
                fmt = '|%s%s' % (fmt, '|' * nCols)
                s.append(fmt % self.groupHeader)

            if uHeader:
                headerFormat = ['%%%ds' % w for w in colWidths]
                just = [justify] * len(colWidths)
                colFormat = [ColWithinColFormat(h, c, j)
                             for h, c, j in zip(headerWidths, colWidths, just)]
                line = sep.join(f % h for f, h in zip(headerFormat, uHeader))
                s.append(pre + line + post)
                s.append(interline)
            else:
                s.append(interline)
                sign = '-' if self.justify == 'l' else ''
                sign = [sign] * len(colWidths)
                colFormat = ['%%%s%ds' % (sf, w) for sf, w in zip(sign,
                                                                  colWidths)]
            for row2D in u2Drows:
                nOutRows = ((max(len(rows) for rows in row2D) if row2D else 1)
                             or 1)
                z = list(zip(colFormat, row2D))
                for i in range(nOutRows):
                    line = sep.join(f % (c[i] if len(c) > i else '')
                                    for f, c in z)
                    s.append(pre + line + post)
        else:
            sep = ' '
            if transpose:  # *** SEE ABOVE (HACK)
                raise Exception('No unformatted transpose Table.toString')
            else:
                if self.groupHeader is not None:
                    s.append(self.groupHeader)
                if uHeader:
                    s.append(sep.join(uHeader))
                for row in self.rows:
                    s.append(sep.row)

        if len(self.annotation) > 1:
            s.extend([a for a in self.annotation])

        if self.footnote:
            s.append('')
            s.append(self.footnote)
        return '\n'.join(s)


    def GetFullColWidths(self, transpose=False):
        """
        Returns column widths in characters.
        Is the width of the relevant header or widest element.
        """
        transpose = self.transpose or transpose
        u2Drows, colWidths = self.ProcessMultilineStrings(transpose)
        header = self.header
        if self.structuredHeader and self.oneLineHeader:
            header = self.oneLineHeader
        uHeader = header if not transpose else []
        if uHeader:
            headerWidths = [len(h) for h in uHeader]
            fullColWidths = [max(h, c) for h, c in zip(headerWidths,
                                                       colWidths)]
        else:
            fullColWidths = colWidths
        return fullColWidths


    def toJSONLog(self, format=True):
        return 'table', {'rows': self.rows, 'header': self.header,
                         'align': ['right'] * self.NCols()}

    def NCols(self):
        if self.rows:
            return len(self.rows[0])
        elif self.header:
            return len(self.header)
        else:
            return 0

    def ProcessMultilineStrings(self, transpose=False, scale=None):
        """
        Computes unicode 2D rows and column widths.
        If scale is None, the column width are in characters
        If scale is supplied, this is the EstimatedStringWidth
        at the scale specified
        """
        f = len
        if transpose:
            return self.ProcessMultilineStringsTransposed()
        nCols = self.NCols()
        colWidths = [0] * nCols
        u2Drows = []
        for row in self.rows:
            uRow = list([u.splitlines() for u in row]) # list of lists
            for i, cell in enumerate(uRow):
                colWidths[i] = max(max(f(c) for c in cell) if cell else 0,
                                   colWidths[i])
            u2Drows.append(uRow)
        return u2Drows, colWidths

    def ProcessMultilineStringsTransposed(self, scale=None):
        """
        Computes unicode 2D rows and column widths for transformed data.
        If scale is None, the column width are in characters
        If scale is supplied, this is the EstimatedStringWidth
        at the scale specified
        """
        f = len
        nHeaders = 1 if self.header else 0
        nColsOut = nHeaders + len(self.rows)
        outColWidths = [0] * nColsOut
        u2DrowsOut = []
        if self.header:
            for u in self.header:
                u2DrowsOut.append([[u + ':']])
                outColWidths[0] = max(len(u) + 1, outColWidths[0])
        else:
            u2DrowsOut = [[] for i in range(nColsOut)]
        for c, inRow in enumerate(self.rows):
            for r, u in enumerate(inRow):
                cellLines = u.splitlines()
                u2DrowsOut[r].append(cellLines)
                w = max(f(line) for line in cellLines) if cellLines else 0
                if outColWidths[c + nHeaders] < w:
                    outColWidths[c + nHeaders] = w
        return u2DrowsOut, outColWidths

    def ColumnValues(self, n=0, formatted=False):
        """
        Returns the column values for the nominated column (or None, if
        n is out of range.

        NOTE: this function returns the RAW NUMERIC value by default,
        even for strings and dates.    This is hard to avoid,
        as the table doesn't know which value is the 'real' one.
        Could add metadata to fix this in the future.
        """
        cv = self.rows if formatted else self.cellValues
        if cv and len(cv[0]) > n:
            return [c[n] for c in cv]

    def RowValues(self, n=0, formatted=False):
        """
        Returns the raw values for the nominated row (or None, if
        n is out of range.

        NOTE: this function returns the RAW NUMERIC value by default,
        even for strings and dates.   This is hard to avoid,
        as the table doesn't know which value is the 'real' one.
        Could add metadata to fix this in the future.
        """
        cv = self.rows if formatted else self.cellValues
        if cv and len(cv) > n:
            return cv[n]

    __str__ = toString

    def isEmpty(self, onlyIf=False):
        return onlyIf and (not self.rows or all(not r for r in self.rows))

    def toHTML(self, format=True, xml=None):
        """
        Returns an HTML representation of the table, unless xml
        if provided, in which case it is just written to that.
        """
        if self.isEmpty(self.emptyIfEmpty):
            return None if xml else ''
        h = xml if xml else XML(omitHeader=1, tabSize=4)

        attr = self.attr or {'class': 'solid'}
        if HTML_REPEAT_HEADERS and self.repeatHeader and self.header:
            attr['repeat'] = self.repeatHeader
        h.OpenElement('table', attributes=attr)

        self.DoHTMLHeader(h)
        useBGColour = False
        if self.transpose:
            self.DoTransposedHTMLTable(h, useBGColour)
        else:
            self.DoHTMLTable(h, useBGColour)

        h.CloseElement('table')
        if len(self.annotation) > 1:
            for a in self.annotation:
                h.WriteElement('div', a)

        h.OpenElement('div', attributes={'class': 'separator'})
        # Wow.   Firefox really doesn't like it if this self-closes. <div/>
        # Safari DOM inspector complains and say it will leave it open
        # Once you hit enough of these, Firefox just gives up (presumably
        # because it's leaving them all open.   Doncha just love Postel.
        # I thought the number might be 256, but it actually looks like
        # it's 200 --- I think I get a fail at 201.
        # What kind of power of 2 is that???
        if self.footnote:
            h.WriteElement('pre', self.footnote)
        h.CloseElement('div')
        if xml:
            return None
        else:
            h.CloseXML()
            return h.xml()

    def DoHTMLHeader(self, h, row=None):
        """
        Writes the header for for the table in the non-transposed case.

        If row (a row number) is given, the row is shown only if
        self.repeat header is non-null and a repeat is due.
        """
        if self.transpose:
            return

        if row is not None:
            if (not self.repeatHeader or row == 0
                    or (row % self.repeatHeader != 0)):
                return

        if self.groupHeader is not None:
            h.OpenElement('tr')
            nCols = len(self.header) + len(self.colSeps)
            h.WriteElement('th', self.groupHeader,
                           attributes=(('colspan', str(nCols)),
                                       self.colHeadAttr))
            h.CloseElement('tr')
        if self.structuredHeader is not None:
            h.OpenElement('tr')
            for (nCols, nRows, head) in self.structuredHeader:
                attr = [('colspan', str(nCols)), self.colHeadAttr]
                if nRows > 1:
                    attr += [('rowspan', str(nRows))]
                h.WriteElement('th', head, attributes=attr)
            h.CloseElement('tr')
        if self.header:
            gh = self.groupHeader is not None
            h.OpenElement('tr')
            for i, f in enumerate(self.header):
                if gh:
                    attr = [self.rowHeadAttr if i == 0 else self.colHeadAttr,]
                else:
                    attr = [self.colHeadAttr,]
                if self.colHeadPadding and self.colHeadPadding[i]:
                    AddAttribute(attr, 'class', self.colHeadPadding[i])
                self.AddHeaderHover(attr, i)
                self.AddOptionalColSep('th', h, i)
                h.WriteElement('th', f, attributes=attr)
            self.AddOptionalColSep('th', h, len(self.header))
            h.CloseElement('tr')

    def AddOptionalColSep(self, tag, h, i):
        if self.colSeps.get(i):
            h.WriteElement(tag, '', attributes={'class': 'colsep'})

    def AddOptionalColSepTransposed(self, tag, h, i):
        if self.colSeps.get(i):
            h.OpenElement('tr')
            for i in range(len(self.rows) + 1):
                h.WriteElement(tag, '', attributes={'class': 'rowsep'})
            h.CloseElement('tr')

    def AddHeaderHover(self, a, i):
        if (self.headerHovers and len(self.headerHovers) > i
                and self.headerHovers[i]):
            a.append(('title', self.headerHovers[i]))

    def DoHTMLTable(self, h, useBGColour=True):
        (cc, cs, cf, nHeaders, _) = self.GetCellFormattingParameters()
        for i, row in enumerate(self.rows):
            if HTML_REPEAT_HEADERS:
                self.DoHTMLHeader(h, i)
            h.OpenElement('tr')
            for j, v in enumerate(row):
                self.WriteCell(h, v, i, j, cc, cs, cf, nHeaders,
                               useBGColour=useBGColour)
            self.AddOptionalColSep('td', h, len(self.header))
            h.CloseElement('tr')

    def DoTransposedHTMLTable(self, h, useBGColour=True):
        (cc, cs, cf, nHeaders, nColumns) = self.GetCellFormattingParameters()
        for j in range(nColumns):
            self.AddOptionalColSepTransposed('td', h, j)
            h.OpenElement('tr')
            if self.header:
                attr = [self.colHeadAttr, ('align', 'right')]
                self.AddHeaderHover(attr, j)
                h.WriteElement('th', self.header[j], attributes=attr)
            for i, row in enumerate(self.rows):
                v = row[j]
                self.WriteCell(h, v, i, j, cc, cs, cf, nHeaders,
                               transposed=True, useBGColour=useBGColour)
            h.CloseElement('tr')
        self.AddOptionalColSepTransposed('td', h, nColumns)

    def WriteHeaderCell(self, h, v, i, j, transposed):
        attr = [self.rowHeadAttr] if self.groupHeader else ()
        self.MDFormatElement(h, 'th', v, i, j, attributes=attr)

    def IsHeader(self, j, cc, nHeaders, useBGColour):
        isNonHead = (j >= nHeaders and j >= self.nColsAsRowHeaders)
        if useBGColour:
            isNonHead = isNonHead and cc[j - nHeaders]
        return not isNonHead

    def HandleURLs(self, h, v, attr):
        m = re.match(MARKDOWN_URL_RE, v)
        if m:
            self.WriteLink(h, m.group(1), m.group(2), elt='td', attr=attr)
        elif re.match(URL_RE, v):
            self.WriteLink(h, v, elt='td', attr=attr)
        elif re.match(GRAPH_RE, v):
            self.WriteImg(h, v, elt='td', attr=attr)
        else:
            return False
        return True

    def AnyExplicitClassAttributes(self, i, j, cs, cf):
        attr = []
        if cs:
            AddAttribute(attr, 'class', cs[i][j])
        elif cf and cf[j] is not None:
            f = colour_class(cf[j])
            if f:
                AddAttribute(attr, 'class', f(self.cellValues[i][j],
                                              **self.tddaMetadata))
        if self.tt:
           AddAttribute(attr, 'class', 'tt')

        return attr, bool(attr)

    def WriteCell(self, h, v, i, j, cc, cs, cf, nHeaders, transposed=False,
                  useBGColour=False):
        """Helper method for DoHTMLTable and DoTransposedHTMLTable"""
        # j is a column-number, i is a row-number
        if not transposed:
            self.AddOptionalColSep('td', h, j)
        if self.IsHeader(j, cc, nHeaders, useBGColour):
            return self.WriteHeaderCell(h, v, i, j, transposed)
        attr, classSet = self.AnyExplicitClassAttributes(i, j, cs, cf)
        if self.HandleURLs(h, v, attr):
            return
        if useBGColour and ((not cf[j]) if self.forceBGColour and cf
                            else not cf):
            # i.e. if any coloured text function, no coloured backgrounds
            # anywhere in table, unless forced, in which case columns without
            # colour-text will be background-coloured.
            AddBackgroundColour(attr, cc[j - nHeaders][i])
        if self.colPadding and self.colPadding[j - nHeaders]:
            AddAttribute(attr, 'class', self.colPadding[j - nHeaders])

        fmt = (getattr(self.htmlrows[i][j], 'html', None)
               if self.htmlrows else None)
        if fmt is not None:
            h.OpenElement('td', attributes=attr)
            h.AddBalancedXML(fmt)
            h.CloseElement('td')
        elif self.command:   # command provided
            h.OpenElement('code', self.command)
            h.CloseElement('td')
        else:
            attr = self.ModifyForNull(attr, i, j, classSet)
            self.MDFormatElement(h, 'td', str(v), i, j, attributes=attr)

    def MDFormatElement(self, x, elt, v, i, j, attributes=None,
                        entitize=2, convertNL=2):
        x.WriteElement(elt, v, attributes=attributes,
                       entitize=entitize, convertNL=convertNL)

    def ModifyForNull(self, attr, i, j, ignore=False):
        return attr

    def GetCellFormattingParameters(self):
        """Helper method for DoColourHTML and DoTransposedColourHTML"""
        nColumns = len(self.rows[0] if len(self.rows) > 0 else self.header)
        return (None, None, None, 0, nColumns)

    def WriteLink(self, x, val, link=None, elt='td', attr=None):
        x.OpenElement(elt)
        if not link:
            n = val.find('://.')
            link = val[n+3:] if n >= 0 else val
        attr = attr or []
        attr.append(('href', link))
        x.WriteElement('a', self.LinkText(val), attributes=attr)
        x.CloseElement(elt)

    def WriteImg(self, x, val, link=None, elt='td', attr=None):
        x.OpenElement(elt)
        if not link:
            n = val.find('://')
            link = val[n+3:] if n >= 0 else val
        attr = attr or []
        attr = attr + [('width', self.graphWidth)]
        attr.append(('src', link))
        x.WriteElement('img', '', attributes=attr)
        x.CloseElement(elt)

    def LinkText(self, v):
        if self.shortlinks:
            _, path = os.path.split(v)
            if path:
                return path
            if v.endswith('/'):
                _, path = os.path.split(v[:-1])
            return path if path else v
        else:
            return v


Table._acceptsFormat = True


def Transpose2D(a):
    out = []
    for inCol in range(len(a[0])):
        outRow = []
        for inRow in a:
            outRow.append(inRow[inCol])
        out.append(outRow)
    return out


def ColWithinColFormat(h, c, pos='l'):
    if pos == 'l':
        F = '%%-%ds' % c
    else:
        F = '%%%ds' % c
    if h <= c:
        return F
    else:
        n = h - c
        R = n // 2
        L = n - R
        return (' ' * L) + F + (' ' * R)


def RemoveEmptyRows(data, empty=None):
    """
    Returns a copy of data with rows consisting of all empty entries
    (as defined by the parameter), together with a list of booleans
    in which the ith entry is True iff the row was kept.
    """
    return ([d for d in data if not d == [empty] * len(d)],
            [d != [empty] * len(d) for d in data])


def PairRemoveNulls(data, labels):
    """
    Data and labels are lists of lists having the same shape.
    This removes entries from both where the data entry is null (None).
    """
    outD, outL = ([], [])
    for (D, L) in zip(data, labels):
        (dRow, lRow) = ([], [])
        for (d, l) in zip(D, L):
            if d is not None:
                dRow.append(d)
                lRow.append(l)
        outD.append(dRow)
        outL.append(lRow)
    return (outD, outL)


def TripleRemoveNulls(data, labels, yLabels, toZero):
    """
    Data and labels are lists of lists having the same shape.
    This removes entries from both where the data entry is null (None).

    yLabels is a list of the "outer" dimension; it gets items removed if
    whole rows go.
    """
    outD, outL, outY = ([], [], [])
    for (D, L, Y) in zip(data, labels, yLabels):
        (dRow, lRow) = ([], [])
        for (d, l) in zip(D, L):
            if d is not None:
                dRow.append(d)
                lRow.append(l)
            elif toZero:
                dRow.append(0)
                lRow.append(l)
        if dRow:
            outD.append(dRow)
            outL.append(lRow)
            outY.append(Y)
    return (outD, outL, outY)


def TableFromList(list_, command, nCols=4):
    N = len(list_)
    values = list_ + [''] * ((nCols - (N % nCols)) if (N % nCols) else 0)
    nRows = len(values) // nCols
    rows = [[values[row * nCols + col] for col in range(nCols)]
            for row in range(nRows)]
    return Table(None, rows, attr={'class': 'clicklist'},
                 command=command, justify='l')


def EmptyTable():
    return Table([], [])


def BackgroundColourAttributes(c):
    attr = []
    AddBackgroundColour(attr, c)
    return attr


def AddBackgroundColour(attr, c):
    if c not in ('#FFFFFF', 'white'):
        AddAttribute(attr, 'bgcolor', c)


def CreateAttribute(k, v):
    attr = []
    AddAttribute(attr, k, v)
    return attr


def AddAttribute(attr, k, v):
    """
    Add attribute k, with value v, to attr, if v is truthy.

    If k is already in attr, appends v to existing value.
    """
    if v:  # is not None:
        for i, (K, V) in enumerate(attr):
            if K == k:
                attr[i] = (k, V + ' ' + v)
                return
        attr.append((k, v))

def mmd_justify_marker(n, justify):
    dashes = '-' * (max(n, 3) - 2)
    if justify == 'r':
        return '%s-:' % dashes
    elif justify == 'c':
        return ':%s:' % dashes
    else:
        return ':-%s:' % dashes



def rgb_bool(satisfied, **params):
    """truthy: Green  nil: black:  other falsy: Green"""
    return 'tdgreen' if satisfied else None if satisfied is None else 'tdred'


def z_red(satisfied, **params):
    """nil or truthy: Red   other falsy: grey"""
    return 'nullgrey' if (satisfied or satisfied is None) else 'tdred'


def nz_red(v, **params):
    """nil: black  otherwise: Red"""
    return 'tdred' if v else None


def nz_green(v, **params):
    """truthy: Green  falsy: black"""
    return 'tdgreen' if v else None

def n1_red(v, **params):
    """< 1: Red; otherwise: black"""
    return 'tdred' if v is not None and v < 1.0 else None

def nns_red(v, **md):
    """< (n-selected): Red  otherwise: black"""
    N = md.get('n_selected')
    return 'tdred' if v is not None and N is not None and v < N else None


def ranking_red(v, **params):
    """<= 8: red  otherwise: grey"""
    return 'tdred' if v is not None and v < 9 else 'nullgrey'


def tt(v, **params):
    """Forces monospace (typewriter type)"""
    return 'tt'



PassthroughCellColourer = Dummy()
PassthroughCellColourer.GetHTML = lambda x: (
    None if x is None or type(x) is not str else x
)
