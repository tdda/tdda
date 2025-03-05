from html import escape as htmlescape

from tdda.utils import Dummy, DQuote

COLOURS7 = [
    '#BF0F00', '#E57200', '#D8A200', '#007F15', '#008AA5', '#6C00D8', '#9700A5'
]
COLOURS = ['#303030'] + [COLOURS7[i] for i in (0, 4, 1, 3, 5)]
N_COLOURS = len(COLOURS)


def Rex2String(rexes, group=True, anchor=True, asList=False):
    """
    Convert list of regular expression objects from Rexpy to RE strings
    """
    if anchor:
        start = '^'
        end = '$'
    else:
        start = end = ''
    results = [(start + ''.join(add_group(frag, group)
                                for frag in result) + end)
               for result in rexes]
    return results if asList else '\n'.join(results)


def add_group(frag, group):
    if group and frag.group and not frag.re.startswith('('):
        return '(%s)' % str(frag.re)
    else:
        return str(frag.re)


def Rex2HTML(rexes, group=True, anchor=True, asList=False):
    """
    Convert list of regular expression objects from Rexpy to HTML,
    with colouring, anchoring and grouping controlled by flags.
    """
    if anchor:
        start = '<span class="anchor">^</span>'
        end = '<span class="anchor">$</span>'
    else:
        start = end = ''
    results = [(start
                + ''.join('<span style="color: %s;">%s</span>'
                          % (colour(i),
                             htmlescape(add_group(frag, group), quote=True))
                          for i, frag in enumerate(result))
                + end)
               for result in rexes]
    return results if asList else ('<pre class="emptycommand">%s</pre>'
                                   % '\n'.join(results))


def OnePerLineHTML(strings):
    return ('<pre class="emptycommand">%s</pre>'
            % '\n'.join(htmlescape(DQuote(s), quote=True)
                        for s in strings))


def colour(n):
    return COLOURS[n % N_COLOURS]


class Regex2Rex:
    """
    Convert any-old regular expression into a (colourable) list of Frags.
    """
    def __init__(self, regex):
        if regex.startswith('^'):
            regex = regex[1:]
        if regex.endswith('$'):
            regex = regex[:-1]
        self.regex = regex

        i = 0
        self.start_of_frag = i
        self.frags = []

        while i < len(regex):
            i, c = self.next_char(i)
            if c in '[(':
                self.add_unfinished_frag(i - 1)
                i = self.alternation(i, c)
                self.add_unfinished_frag(i, True)
            elif c in ('.', '\\d', '\\W', '\\w', '\\s'):
                self.add_unfinished_frag(i - len(c))
                i = self.skip_any_quantifier(i)
                self.add_unfinished_frag(i, True)
            else:      # ordinary
                pass   # just move on
        self.add_unfinished_frag(len(self.regex))

    def next_char(self, i):
        if i < len(self.regex):
            c = self.regex[i]
            i += 1
            if c == '\\':
                if i < len(self.regex):
                    c += self.regex[i]
                    i += 1
        else:
            c = None
        return i, c

    def add_unfinished_frag(self, i, group=False):
        if i > self.start_of_frag:
            self.frags.append(Frag(re=self.regex[self.start_of_frag:i],
                                   group=group))
        self.start_of_frag = i


    def skip_any_quantifier(self, i):
        if i < len(self.regex):
            nextc = self.regex[i]
            if nextc in '*+?{':
                i += 1
                if nextc == '{':
                    while i < len(self.regex):
                        i, c = self.next_char(i)
                        if c == '}' or c is None:
                            break
        return i

    def alternation(self, i, opening):
        assert opening in '(['
        closing = ']' if opening == '[' else ')'
        depth = 1
        c = None
        while True:
            i, c = self.next_char(i)
            if c == closing or c is None:
                depth -= 1
                if depth == 0:
                    break
            elif c == opening:
                depth += 1
        return self.skip_any_quantifier(i)


class Frag:
    def __init__(self, re, group=False):
        self.re = re
        self.group = group

    def __eq__(self, other):
        return self.re == other.re and self.group == other.group

    def __repr__(self):
        return 'Frag(re=%s, group=%s)' % (repr(self.re), repr(self.group))


def colour_regexes(regex_list):
    r = [Regex2Rex(r).frags for r in regex_list]
    return Dummy(html=Rex2HTML(r, group=True, anchor=True, asList=False))
