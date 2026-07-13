#
# xerpy.py: Create example strings matching (simple) unix-style
#           regular expressions.
#
# Copyright (c) Stochastic Solutions Limited, 2018-2026
#
# Copied from Miro (Stochastic Solutions) and now
# MIT licensed like the rest of TDDA.


import argparse
import random
import sys
import time

from tdda.man.utils import print_help
from tdda.rexpy.rexutils import Repeat, range_weight, repeat_cardinality


VERBOSE = False
DEFAULT_MAX_PLUS = 5

def crange(chars):
    assert len(chars) == 2
    return tuple(chr(i) for i in range(ord(chars[0]), ord(chars[1]) + 1))


def nvl(x, v):
    return v if x is None else x


DOT_CHARS = crange(' ~')
AFTER_z = '{|}~'  # characters after z in ASCII, before backspace
BEFORE_BANG = ' '
DIGITS = crange('09')
HEX_DIGITS = crange('09') + crange('af') + crange('AF')
LC_LETTERS = crange('az')
UC_LETTERS = crange('AZ')
LETTERS = LC_LETTERS + UC_LETTERS
WHITESPACE_CHARS = (' ', '\t', '\r', '\n', '\f', '\v')
BLANK_CHARS = (' ', '\t')
WORD_CHARS = DIGITS + UC_LETTERS + ('_',) + LC_LETTERS
ALNUM_CHARS = DIGITS + UC_LETTERS + LC_LETTERS
NON_WORD_CHARS = tuple(sorted(set(DOT_CHARS) - set(WORD_CHARS)))
PUNCTUATION_CHARS = [chr(c) for c in range(32, 127) if not chr(c).isalnum()]
VISIBLE_CHARS = crange('!~')
CONTROL_CHARS = crange('\x00\x1F') + ('\x7E',)

PROPERTY = 'p'            # Dummy
INVERSE_PROPERTY = 'P'    # Dummy

ESCAPES = {
    'd': DIGITS,
    'w': WORD_CHARS,
    'W': NON_WORD_CHARS,
    's': WHITESPACE_CHARS,
    't': '\t',
    'r': '\r',
    'n': '\n',
    'f': '\f',
    'v': '\v',
    'p': PROPERTY,
    'P': INVERSE_PROPERTY,
}


PROPERTIES = {
    'digit': DIGITS,
    'number': DIGITS,
    'n': DIGITS,
    'nd': DIGITS,
    'decimal_digit_number': DIGITS,
    'xdigit': HEX_DIGITS,
    'hex_digit': HEX_DIGITS,
    'alphabetic': LETTERS,
    'alpha': LETTERS,
    'letter': LETTERS,
    'l': LETTERS,
    'lower': LC_LETTERS,
    'lowercase': LC_LETTERS,
    'lowercase_letter': LC_LETTERS,
    'll': LC_LETTERS,
    'upper': UC_LETTERS,
    'uppercase': UC_LETTERS,
    'uppercase_letter': UC_LETTERS,
    'lu': UC_LETTERS,
    'alnum': ALNUM_CHARS,
    'word': WORD_CHARS,
    'punctuation': PUNCTUATION_CHARS,
    'p': PUNCTUATION_CHARS,
    'separator': WHITESPACE_CHARS,
    'space': WHITESPACE_CHARS,
    'blank': BLANK_CHARS,
    'z': WHITESPACE_CHARS,
    'control': CONTROL_CHARS,
    'cc': CONTROL_CHARS,
    'any': DOT_CHARS,
}


CHARACTER_CLASSES = {
    ':digit:': DIGITS,
    ':alpha:': LETTERS,
    ':lower:': LETTERS,
    ':upper:': UC_LETTERS,
    ':punct:': PUNCTUATION_CHARS,
    ':space:': WHITESPACE_CHARS,
    ':blank:': BLANK_CHARS,
    ':xdigit:': HEX_DIGITS,
    ':graph:': VISIBLE_CHARS,
    ':cntrl:': CONTROL_CHARS,
}


class Xerpy:
    """
    Class for constructing example instances of a regular expression.
    """
    def __init__(self, rex, weighted=False):
        self.original_rex = rex
        self.rex, self.wrap_start, self.wrap_close = self.maybe_wrap(rex)
        self.weighted = weighted

    def maybe_wrap(self, rex):
        """
        If the pattern contains a '|', wrap the anchor-stripped body in
        a synthetic group so alternation across the whole pattern is
        handled by the same machinery as any other group's alternation.

        This is the only sensible generative reading of an unwrapped
        top-level '|': xerpy always generates a complete string for the
        whole pattern rather than searching for a match within a larger
        one, so there is no meaningful generative distinction between
        "^A|B$" and "^(A|B)$" -- unlike for re.search/re.match, where
        the unwrapped form means "^A" or "B$", each with only one of
        the two anchors.

        Returns (new_rex, wrap_start, wrap_close): the positions (in
        new_rex) of the synthetic '(' and ')', used by error() to map
        positions in new_rex back to the user's original string. If no
        wrapping was needed, wrap_start and wrap_close are both None.
        """
        if '|' not in rex:
            return rex, None, None
        had_start = rex[:1] == '^'
        had_end = rex[-1:] == '$' and real_trailing_dollar(rex)
        start_idx = 1 if had_start else 0
        end_idx = len(rex) - (1 if had_end else 0)
        body = rex[start_idx:end_idx]
        wrap_start = start_idx
        wrap_close = start_idx + 1 + len(body)
        new_rex = rex[:start_idx] + '(' + body + ')' + rex[end_idx:]
        return new_rex, wrap_start, wrap_close

    def map_position(self, p):
        """
        Maps a position in self.rex (which may be wrapped in a
        synthetic group -- see maybe_wrap) back to the corresponding
        position in self.original_rex, for error reporting.
        """
        if self.wrap_start is None:
            return p
        if p <= self.wrap_start:
            return p
        elif p <= self.wrap_close:
            return p - 1
        else:
            return p - 2

    def compile(self):
        p = 0
        self.generators = RootGroup()
        while p < len(self.rex):
            p = self.process(p)
        if not self.generators.current.is_root():
            self.error('Unbalanced group parentheses', p)
        self.generators.reset()

    def generate(
        self, min_len=None, max_len=None, verbose=VERBOSE, weighted=None,
    ):
        """Generate one example string matching the pattern.

        `weighted` controls whether alternation branches are chosen
        with uniform probability (`False`, the long-standing
        default) or weighted by each branch's estimated cardinality
        (`True`) -- a branch admitting a billion strings is picked
        far more often than one admitting two, rather than equally
        often. Falls back to `self.weighted` (set in `__init__`,
        itself defaulting to `False`) when not given explicitly.
        """
        if weighted is None:
            weighted = self.weighted
        if not hasattr(self, 'generators'):
            self.compile()
        out = []
        for f, q in self.generators:
            out.append(self.generate_frag(f, q(), weighted))
        s = ''.join(out)
        if min_len is not None or max_len is not None:
            s = self.improve_length(len(s), out, min_len, max_len, weighted)
        if verbose:
            print("'%s': '%s'" % (self.original_rex, s))
        return s

    def generate_frag(self, f, n, weighted=False):
        frag = []
        for i in range(n):
            if getattr(f, 'kind', None) == 'Group':
                frag.append(f.generate(weighted))
            else:
                frag.append(f())
        return ''.join(frag)


    def improve_length(self, L, out, min_len, max_len, weighted=False):
        m = nvl(min_len, L)
        M = nvl(max_len, L)
        if not (m <= L <= M):
            indexes = list(range(len(list(self.generators))))
            random.shuffle(indexes)
            for i in indexes:
                if L < m:
                    L += self.lengthen(i, out, m - L, M - L, weighted)
                elif L > M:
                    L -= self.shorten(i, out, L - M, L - m, weighted)
                if (m <= L <= M):
                    break
        return ''.join(out)

    def lengthen(self, i, out, target_extra, max_extra, weighted=False):
        (f, q) = self.generators[i]
        frag = out[i]
        L = len(frag)
        if q.M is None: # Can do it all
            n = random.randint(L + target_extra, L + max_extra)
        elif q.M > L:   # Can do something, at least
            if L + target_extra > q.M:  # Can't do it all
                n = q.M
            else:   # Can do it all
                n = random.randint(L + target_extra, min(q.M, L + max_extra))
        else:  # Can't do anything
            n = None
            xtra = 0
        if n is not None:
            s = self.generate_frag(f, n, weighted)
            if len(s) > L:
                out[i] = s
            xtra = len(s) - L
        return xtra

    def shorten(self, i, out, target_reduction, max_reduction, weighted=False):
        (f, q) = self.generators[i]
        frag = out[i]
        L = len(frag)
        if (q.M is None and q.m is None):
            m = M = 1
        else:
            m, M = q.m, q.M
            assert m is not None
        if m < L:   # Can do something, at least
            if L - m < target_reduction:  # Can't do it all
                n = m
            else:   # Can do it all
                n = random.randint(max(m, L - max_reduction),
                                   L - target_reduction)
        else:  # Can't do anything
            n = None
            reduction = 0
        if n is not None:
            s = self.generate_frag(f, n, weighted)
            if len(s) < L:
                out[i] = s
            reduction = L - len(s)
        return reduction

    def process(self, p):
        c = self.rex[p]
        if c == '(':
            return self.begin_group(p)
        elif c == ')':
            return self.end_group(p)
        elif c == '|':
            return self.pipe(p)
        elif c == '[':
            return self.bracket(p)
        elif c == '.':
            return self.dot(p)
        elif c == '\\':
            return self.escape(p)
        elif c == '^':
            return self.start_anchor(p)
        elif c == '$':
            return self.end_anchor(p)
        else:
            return self.literal(p)

    def begin_group(self, p):
        self.generators.push()
        return p + 1

    def end_group(self, p):
        if self.generators.current.is_root():
            self.error('Close group ")" matches no open group "("', p)
        quantifier, p = self.get_any_quantifier(p + 1)
        self.generators.pop(quantifier)
        return p

    def pipe(self, p):
        if self.generators.current.is_root():
            self.error('Alternation marker "|" found outside group', p)
        self.generators.create_alternative()
        return p + 1

    def bracket(self, p):
        """
        Extract bracket and any quantifer, starting at position p.
        Return next position for processing
        """
        chars = set()
        done = False
        prev = None
        exclusion = False
        first = True
        p += 1
        if p < len(self.rex) and self.rex[p] == '^':
            exclusion = True
            p += 1
        while p < len(self.rex) and not done:
            c = self.rex[p]
            if c == ']' and not first:
                done = True
            elif c == '\\':
                echars, offset = self.escape_chars(p)
                if isinstance(echars, tuple):
                    chars = chars.union(set(echars))
                else:
                    chars.add(echars)  # single escaped char
                p += offset
            elif c == '-' and (first or self.rex[p + 1:p + 2] == ']'):
                # '-' at the start or end of a class is a literal, not
                # a range operator.
                chars.add('-')
                prev = '-'
            elif c == '-':
                if prev is None:
                    self.error('Bad range specifier', p)
                p += 1
                if p >= len(self.rex):
                    self.error('Pattern ended during range specification', p)
                c = self.rex[p]
                start_chr = ord(prev)
                end_chr = ord(c)
                if end_chr < start_chr:
                    self.error("Bad range specifer ('%s' precedes '%s'"
                               % (c, prev), p)
                for c in range(start_chr + 1, end_chr + 1):
                    chars.add(chr(c))
                prev = None
            elif c == '[':  # possible [:digit:] or similar
                close_pos = self.rex[p+2:].find(']')
                if close_pos == -1:
                    self.error('Unclosed character class', p + 1)
                code = self.rex[p + 1:p + 2 + close_pos]
                v = CHARACTER_CLASSES.get(code)
                if not v:
                    if CHARACTER_CLASSES.get(':%s:' % code):
                        self.error('Character class [%s] not known'
                                   ' (but [:%s:] is).' % (code, code), p)
                    else:
                        self.error('Character class [%s] not known' % code, p)
                chars = chars.union(set(v))
                p += len(code) + 1
            else:
                chars.add(c)
                prev = c
            first = False
            p += 1
        if not done:
            self.error('Pattern ended during alternation group [...]', p)
        elif not chars:
            self.error('Empty brackets', p)

        quantifier, p = self.get_any_quantifier(p)
        if exclusion:
            chars = set(DOT_CHARS) - chars
            if not chars:
                self.error('Bracket excludes everything xerpy uses.', p)
        self.generators.append((brackets(tuple(sorted(chars))), quantifier))
        return p

    def dot(self, p):
        """
        Handle a dot and any quantifier.
        """
        quantifier, p = self.get_any_quantifier(p + 1)
        self.generators.append((any_character, quantifier))
        return p

    def escape(self, p):
        """
        Handle an escaped character at position p,
        together with any quantifier.
        """
        chars, offset = self.escape_chars(p)
        if isinstance(chars, tuple):
            part = brackets(chars)
        else:
            part = fixed(chars)
        quantifier, p = self.get_any_quantifier(p + offset + 1)
        self.generators.append((part, quantifier))
        return p

    def escape_chars(self, p):
        """
        Expand a recognized escape sequence at position p into either
            - a tuple of characters, for things like \\d
            - a literal for escapes that are single characters
              or which have no effect
        Returns the character or tuple of characters represented
        by the escape sequence, and the number of characters in the
        escape sequence after the backslash (1 for \\d; 9 for \\p{Letter}).
        """
        assert self.rex[p] == '\\'
        p += 1
        if p >= len(self.rex):
            self.error('Expression terminated during escape sequence', p)
        c = self.rex[p]
        v = ESCAPES.get(c, c)
        if v not in (PROPERTY, INVERSE_PROPERTY):
            return v, 1
        # Found a property, such as \p{letter}
        rest = self.rex[p+1:]
        close_brace_pos = rest.find('}')
        if close_brace_pos < 0 or rest[0] != '{':
            self.error(r'Properties \p must have form \p{Name}.', p)
        offset = close_brace_pos + 1  # need to skip over these
        rest = rest[1:offset - 1].lower()
        if rest and rest[0] == '^':
            v = INVERSE_PROPERTY if v == PROPERTY else PROPERTY
            rest = rest[1:]
        chars = PROPERTIES.get(rest)
        if v == INVERSE_PROPERTY:
            if rest == 'any':
                self.error('Cannot invert Any', p)
            chars = tuple(sorted(set(DOT_CHARS) - set(chars)))
        if not chars:
            self.error('"%s" is not a Unicode property known to xerpy.'
                       % rest, p)
        return chars, offset + 1

    def literal(self, p):
        """
        Handle a non-special, non-escaped character at position p,
        together with any quantifier.
        """
        c = self.rex[p]
        quantifier, p = self.get_any_quantifier(p + 1)
        self.generators.append((fixed(c), quantifier))
        return p

    def start_anchor(self, p):
        """
        Handle ^.
        If at start of string, return 1.
        Otherwise, raise Exception
        """
        if p != 0:
            self.error('Unescaped ^ can only occur at the start of the '
                       'pattern (it is a literal inside a character '
                       'class)', p)
        return p + 1

    def end_anchor(self, p):
        """
        Handle $.
        If at end of string, return string length.
        Otherwise, raise Exception
        """
        if p + 1 != len(self.rex):
            self.error('Unescaped $ can only occur at the end of the '
                       'pattern (it is a literal inside a character '
                       'class)', p)
        return p + 1

    def get_any_quantifier(self, p):
        """
        Extract quantifier, if any, from position p.
        Return quantifier as quantifier(n, N) and next available position.

            *             --> quantifier(0, None)
            +             --> quantifier(1, None)
            ?             --> quantifier(0, 1)
            {n}           --> quantifier(n, n)
            {n, N}        --> quantifier(n, N)
            no quantifier --> quantifier(1, 1)
        """
        if p < len(self.rex):
            c = self.rex[p]
            if c == '+':
                return quantifier(1, None), p + 1
            elif c == '*':
                return quantifier(0, None), p + 1
            elif c == '?':
                return quantifier(0, 1), p + 1
            elif c == '{':
                n, p = self.get_number(p + 1)
                if p >= len(self.rex):
                    self.error('Regular expression terminated during range '
                               'specifier', p)
                c = self.rex[p]
                if c == '}':
                    return quantifier(n, n), p + 1
                elif c == ',':
                    p += 1
                    if p >= len(self.rex):
                        self.error('Regular expression terminated during range '
                                   'specifier', p)
                    N, p = self.get_number(p)
                    if p >= len(self.rex):
                        self.error('Regular expression terminated during range '
                                   'specifier', p)
                    if not self.rex[p] == '}':
                        self.error("Expected '}', found '%s'", p)
                    return quantifier(n, N), p + 1
        return quantifier(None), p

    def get_number(self, p):
        """
        Gets a (whole, non-negative) number from self.rex at position p.

        If there isn't one, raises an exception.

        Returns the number and the next unused position in self.rex.
        """
        if p >= len(self.rex):
            self.error('Expected digit, found end of string', p)
        if not self.rex[p].isdigit():
            raise ValueError('%s is not a digit' % self.rex[p])
        e = p + 1
        while e < len(self.rex) and self.rex[e].isdigit():
            e += 1
        n = int(self.rex[p:e])
        return n, e

    def error(self, msg, p):
        p = self.map_position(p)
        rex = self.original_rex
        left = str(rex[:p])[:-1]
        right = ' ' * len(left) + str(rex[p:])[1:]
        raise Exception('%s (position %d)\n%s\n%s'
                        % (msg, p, left, right))


def real_trailing_dollar(rex):
    """
    True if the final character of rex is a real (unescaped) '$'
    anchor rather than an escaped literal '$'.
    """
    n = 0
    i = len(rex) - 2
    while i >= 0 and rex[i] == '\\':
        n += 1
        i -= 1
    return n % 2 == 0


class Group:
    """
    Container for a capture group (possible the whole regex).
    """
    kind = 'Group'
    def __init__(self, parent=None, root=None):
        self.alternatives = [[]]    # list of alternatives in current group
        self.parent = parent        # parent of current group (None for root)
        self.root = self if root is None else root  # root Group for rex
        self.frags = self.alternatives[0]  # fragments for current alternative
        self.depth = 0 if self.is_root() else parent.depth + 1
        self.min_alt_len = None     # min length of alternatives, if any
        self.max_alt_len = None     # max length of alternatives, if any
        self._cardinality = None    # cache: cardinality() is invariant
        self._weights = None        # cache: weighted generate()'s weights

    def is_root(self):
        return self.root is self

    def generate(self, weighted=False, max_plus=DEFAULT_MAX_PLUS):
        n = len(self.alternatives)
        if n > 1:
            if weighted:
                if self._weights is None:
                    self._weights = [
                        range_weight(
                            self._alternative_cardinality(frags, max_plus)
                        )
                        for frags in self.alternatives
                    ]
                a = random.choices(range(n), weights=self._weights)[0]
            else:
                a = random.randint(0, n - 1)
        else:
            a = 0

        out = []
        frags = self.alternatives[a]
        for f, q in frags:
            for i in range(q()):
                if getattr(f, 'kind', None) == 'Group':
                    out.append(f.generate(weighted, max_plus))
                else:
                    out.append(f())
        s = ''.join(out)
        return s

    def _alternative_cardinality(self, frags, max_plus):
        """Estimated cardinality of one alternative: the product of
        each fragment's own cardinality (an atom's alphabet size, or
        a nested Group's own `cardinality()`) raised across its
        quantifier's repeat range.
        """
        product = 1
        for f, q in frags:
            atom_size = (
                f.cardinality(max_plus)
                if getattr(f, 'kind', None) == 'Group'
                else f.size
            )
            # q.m is None only for the "no quantifier" sentinel
            # (exactly one repetition) -- unlike an open-ended '*'/
            # '+', which has q.m set (0 or 1) with only q.M None.
            repeat = Repeat(1, 1) if q.m is None else Repeat(q.m, q.M)
            product *= repeat_cardinality(atom_size, repeat, max_plus)
        return product

    def cardinality(self, max_plus):
        """Estimated cardinality of this group: the sum of its
        alternatives' cardinalities (an over-estimate when
        alternatives overlap, since it doesn't attempt the
        disjointness reasoning `quality.py`'s `count_strings` does
        -- fine for use as a relative sampling weight, not intended
        as an exact count). Cached: the pattern tree is built once
        at parse time and never mutated afterward, so this is
        invariant across calls.
        """
        if self._cardinality is None:
            self._cardinality = sum(
                self._alternative_cardinality(frags, max_plus)
                for frags in self.alternatives
            )
        return self._cardinality


class RootGroup(Group):
    def __init__(self):
        Group.__init__(self)
        self.current = self         # current group being extended

    def __getitem__(self, k):
        return self.current.frags[k]

    def __setitem__(self, k, v):
        self.current.frags[k] = v

    def append(self, item):
        self.current.frags.append(item)

    def extend(self, L):
        self.current.frags.extend(L)

    def push(self):
        g = Group(parent=self.current, root=self.root)
        q = None  # placeholder quantifier
        self.current.frags.append((g, q))
        self.current = g

    def pop(self, quantifier):
        parent = self.current.parent
        f, _ = parent.frags[-1]
        parent.frags[-1] = (f, quantifier)   # set quantifier
        self.current = parent

    def create_alternative(self):
        L = []
        self.current.alternatives.append(L)
        self.current.frags = L

    def reset(self):
        self.current = self


def memoize(f):
    memo = {}
    def helper(*args):
        if args not in memo:
            memo[args] = f(*args)
        return memo[args]
    return helper



# Memoizing mainly to make the tests work
@memoize
def quantifier(m=None, M=None, p0=0.8, p1=0.8):
    if m is None:
        f = lambda: 1
    elif m == M:
        f = lambda: m
    elif M is not None:
        f = lambda: random.randint(m, M)
    elif m == 0:
        f = lambda: star()
    elif m == 1:
        f = lambda: plus()
    else:
        raise Exception('Unknown quantifier: quantifier(%s,%s)' % (m, M))
    f.m = m
    f.M = M
    return f


def star(p=0.8, p1=0.8):
    return plus(p1) if random.random() > p else 0


def plus(p=0.8):
    n = 1
    while random.random() < p:
        n += 1
    return n


def any_character():
    """
    Returns random character for '.',
    currently chosen between space (' ') and 'Z'.
    """
    return random.choice(DOT_CHARS)


any_character.size = len(DOT_CHARS)


@memoize
def brackets(charlist):
    """
    Returns function that randomly chooses one from charlist
    """
    f = lambda: random.choice(charlist)
    f.size = len(charlist)
    return f


@memoize
def fixed(c):
    f = lambda: c
    f.size = 1
    return f


def parse_args(args):
    parser = argparse.ArgumentParser(prog='xerpy', add_help=False)
    parser.add_argument('-h', '-?', '--help', dest='help',
                         action='store_true')
    parser.add_argument('rex', nargs='?', help='regular expression to '
                                                'generate strings matching')
    parser.add_argument('n', nargs='?', type=int, default=1,
                         help='number of strings to generate (default: 1)')
    parser.add_argument('seed', nargs='?', type=int, default=None,
                         help='random seed to use (default: current time)')
    weighting = parser.add_mutually_exclusive_group()
    weighting.add_argument('-w', '--weighted', action='store_true',
                            help='choose alternation branches weighted '
                                 'by their estimated cardinality')
    weighting.add_argument('-e', '--even', action='store_true',
                            help='choose alternation branches uniformly '
                                 '(default)')
    parser.add_argument('-s', '--seed', dest='show_seed',
                         action='store_true',
                         help='print the random seed used before the '
                              'generated strings')
    return parser.parse_args(args)


def main():
    params = parse_args(sys.argv[1:])
    if params.help or not params.rex:
        print_help('xerpy', sys.stdout)
        sys.exit(0 if params.help else 1)
    seed = params.seed if params.seed is not None else int(time.time())
    random.seed(seed)
    if params.show_seed:
        print('Seed: %s\n' % seed)
    x = Xerpy(params.rex, weighted=params.weighted)
    for i in range(params.n):
        print(x.generate())


if __name__ == '__main__':
    main()

