# -*- coding: utf-8 -*-

"""
rexpy.py: Regular expression extraction (induction) from examples
"""

from __future__ import division
from __future__ import print_function
from __future__ import absolute_import
from __future__ import unicode_literals

import random
import re
import string
import sys

from collections import Counter, defaultdict, namedtuple

str_type = unicode if sys.version_info.major < 3 else str
bytes_type = str if sys.version_info.major < 3 else bytes

USAGE = """USAGE:

    python rexpy.py [FLAGS] [input file [output file]]

If input file is provided, it should contain one string per line;
otherwise lines will be read from standard input.

If output file is provided, regular expressions found will be written
to that (one per line); otherwise they will be printed.

FLAGS are optional flags. Currently:

  -h, --header      Discard first line, as a header.

  -?, --help        Print this usage information and exit (without error)

  -g, --group       Generate capture groups for each variable fragment
                    of each regular expression generated, i.e. surround
                    variable components with parentheses
                        e.g.     '^([A-Z]+)\-([0-9]+)$'
                        becomes  '^[A-Z]+\-[0-9]+$'

  -u, --underscore  Allow underscore to be treated as a letter.
                    Mostly useful for matching identifiers
                    Also allow -_.

  -d, --dot         Allow dot to be treated as a letter.
                    Mostly useful for matching identifiers.
                    Also -. --period.

  -m, --minus       Allow minus to be treated as a letter.
                    Mostly useful for matching identifiers.
                    Also --hyphen or --dash.

"""

MIN_MERGE_SIMILARITY = 0.5
TERMINATE = True  # False

N_ALIGNMENT_LEVELS = 1

MAX_GROUPS = 99   # re library fails with AssertionError:
                  # sorry, but this version only supports 100 named groups
                  # if you have too many groups.
                  # Looks like actual limit might be 99, not 100...

MAX_VRLE_RANGE = 2  # Meaning that it will only produce patterns like
                    # x{m,n} when n - m ≤ 2


class SIZE(object):
    DO_ALL = 1024               # Use all examples up to this many
    DO_ALL = 100000000          # Use all examples up to this many
    DO_ALL_EXCEPTIONS = 4096    # Add in all failyres up to this many
    N_PER_LENGTH = 64           # When sampling, use this many
                                # of each length
    MAX_SAMPLED_ATTEMPTS = 2    # Give up and use all after this many
                                # sampled attempts

    MAX_PUNC_IN_GROUP = 5
    MAX_STRINGS_IN_GROUP = 10


nCalls = 0
memo = {}
def cre(rex):
    global nCalls, memo
    nCalls += 1
    c = memo.get(rex)
    if c:
        return c
    else:
        memo[rex] = c = re.compile(rex)
        return c


def terminated_cre(expr):
    return cre('^%s$' % expr)


def terminated_re(expr):
    return '^%s$' % expr


if TERMINATE:
    poss_term_cre = terminated_cre
    poss_term_re = terminated_re
else:
    def poss_term_re(expr):
        return expr

    def poss_term_cre(expr):
        return cre(expr)


class CODE(object):
    ANY = '?'
    PUNC = '.'


class Category(object):
    def __init__(self, name, code, re_string):
        self.name = name
        self.code = code
        self.re_string = re_string
        self.re_single = poss_term_cre(re_string)
        self.re_multiple = poss_term_cre(re_string + '+')


class Categories(object):
    def __init__(self, extra_letters=None):
        if extra_letters:
            assert all(L in '_-.' for L in extra_letters)  # for now
            el_re = ''.join(r'\%s' % L for L in extra_letters)
        else:
            el_re = ''
        punctuation = self.Punctuation(el_re)
        self.LETTER = Category('LETTER', 'A', '[A-Z]')
        self.letter = Category('letter', 'a', '[a-z]')
        self.Letter = Category('Letter', 'L', '[A-Za-z]')
        if extra_letters:
            self.LETTER_ = Category('LETTER_', 'B', '[A-Z%s]' % el_re)
            self.letter_ = Category('letter_', 'b', '[a-z%s]' % el_re)
            self.Letter_ = Category('Letter_', 'M', '[A-Za-z%s]' % el_re)
            ExtraLetterGroups = ['LETTER_', 'letter_', 'Letter_']
        else:
            ExtraLetterGroups = []
        self.Digit = Category('Digit', 'D', r'\d')
        self.hex = Category('hex', 'h', '[0-9a-f]')
        self.HEX = Category('HEX', 'H', '[0-9A-F]')
        self.Hex = Category('Hex', 'X', '[0-9a-fA-F]')
        self.ALPHANUMERIC = Category('ALPHANUMERIC', 'N', '[A-Z0-9%s]' % el_re)
        self.alphanumeric = Category('alphanumeric', 'n', '[a-z0-9%s]' % el_re)
        self.AlphaNumeric = Category('AlphaNumeric', 'C',
                                     '[A-Za-z0-9%s]' % el_re)
        self.Whitespace = Category('Whitespace', ' ', r'\s')
        self.Punctuation = Category('Punctuation', CODE.PUNC,
                                    '[%s]' % re.escape(''.join(punctuation)))
        self.Other = Category('Other', '*', r'[^!-~\s]')
        self.Any = Category('Any', CODE.ANY, '.')

        self.SpecificCoarseCats = [self.AlphaNumeric,
                                   self.Whitespace,
                                   self.Punctuation]
        self.AllCoarseCats = self.SpecificCoarseCats + [self.Other]
        self.IncreasinglyGeneralAlphanumerics = [
            'Digit',
            'LETTER', 'letter', 'Letter',
        ] + ExtraLetterGroups + [
            'HEX', 'hex', 'Hex',
            'ALPHANUMERIC', 'alphanumeric'
        ]

    def Punctuation(self, el_re):
        specials = re.compile(r'[A-Za-z0-9\s%s]' % el_re)
        return [chr(c) for c in range(32, 127) if not re.match(specials,
                                                               chr(c))]


    def build_cat_map(self):
        """
        Lazily builds (on first use) mapping from single-character category
        codes to Category Objects, stores in self.code2cat, which is used
        by __getitem__. E.g.

            'N' --> self.ALPHANUMERIC
            'X' --> self.Hex
        """
        self.code2cat = {}
        for k in self.__dict__:
            cat = self.__dict__[k]
            code = getattr(cat, 'code', None)
            if code:
                self.code2cat[code] = cat

    def __getitem__(self, k):
        if not hasattr(self, 'code2cat'):
            self.build_cat_map()
        return self.code2cat[k]


Fragment = namedtuple('Fragment', 're group')


class Extractor(object):
    """
    Regular expression 'extractor'.

    Given a set of examples, this tries to construct a useful
    regular expression that characterizes them; failing which,
    a list of regular expressions that collectively cover the cases.

    Results are stored in self.results once extraction has occurred,
    which happens by default on initialization, but can be invoked
    manually.
    """
    def __init__(self, examples, extract=True, tag=False, extra_letters=None,
                 verbose=False):
        """
        Set class attributes and clean input strings.
        Also performs exraction unless extract=False.
        """

        self.example_freqs = Counter()      # Each string stored only once;
                                            # but multiplicity stored
#        self.by_length = defaultdict(list)  # Examples also stored by length
        self.n_stripped = 0                 # Number that required stripping
        self.n_empties = 0                  # Number of empty string found
        self.n_nulls = 0                    # Number of nulls found
        self.clean(examples)                # Fill in previous attrubutes
        self.tag = tag                      # Returned tagged (grouped) RE
        self.verbose = verbose
        self.results = None
        self.warnings = []
        self.n_too_many_groups = 0
        self.Cats = Categories(self.thin_extras(extra_letters))
        if extract:
            self.extract()                  # Stores results


    def extract(self):
        """
        Actually perform the regular expression 'extraction'.
        """
        if len(self.example_freqs) == 0:
            self.results = None

        if len(self.example_freqs) <= SIZE.DO_ALL:
            self.results = self.batch_extract(self.example_freqs.keys())
        else:  # Future poss optimization; not really used for now.
            examples = self.sample(SIZE.N_PER_LENGTH)
            attempt = 1
            failures = []
            while attempt <= SIZE.MAX_SAMPLED_ATTEMPTS + 1:
                print('Attempt %d' % attempt)
                if self.verbose:
                    print('Examples: %s ... %s' % (examples[:5],
                                                   examples[-5:]))
                self.results = self.batch_extract(examples)
                failures = self.find_non_matches()
                if self.verbose:
                    print('REs:', self.results.rex)
                    print('Failures (%d): %s' % (len(failures),
                                                 failures[:5]))
                if len(failures) == 0:
                    break
                elif (len(failures) <= SIZE.DO_ALL_EXCEPTIONS
                      or attempt > SIZE.MAX_SAMPLED_ATTEMPTS):
                    examples.extend(failures)
                else:
                    examples.extend(random.sample(failures,
                                                  SIZE.DO_ALL_EXCEPTIONS))
                attempt += 1
        self.add_warnings()

    def add_warnings(self):
        if self.n_too_many_groups:
            self.warnings.append('%d string%s assigned to .{m,n} for needing '
                                 '"too many" groups.'
                                 % (self.n_too_many_groups,
                                    's' if self.n_too_many_groups > 1 else ''))

    def thin_extras(self, extra_letters):
        if not extra_letters or len(extra_letters) == 1:
            return extra_letters
        keep = []
        for L in extra_letters:
            if any(L in example for example in self.example_freqs):
                keep.append(L)
        return ''.join(keep) if keep else None

    def clean(self, examples):
        """
        Compute length of each string and count number of examples
        of each length.
        """
        for s in examples:
            if s is None:
                self.n_nulls += 1
            else:
                stripped = s.strip()
                L = len(stripped)
                if L == 0:
                    self.n_empties += 1
                else:
                    self.example_freqs[stripped] += 1
                    if len(stripped) != len(s):
                        self.n_stripped += 1
#                    if self.example_freqs[stripped] == 1:
#                        self.by_length[L].append(stripped)

    def batch_extract(self, examples):
        """
        Find regular expressions for a batch of examples (as given).
        """
        rles = [self.run_length_encode_coarse_classes(s) for s in examples]
        rle_freqs = Counter()
        for r in rles:
            rle_freqs[r] += 1

        vrles = to_vrles(rle_freqs.keys())
        vrle_freqs = Counter()
        refined = []
        rex = []
        for r in vrles:
            vrle_freqs[r] += 1
            grouped = self.refine_groups(r, self.example_freqs)
            refined.append(grouped)
            rex.append(self.vrle2re(grouped))
        merged = self.merge_patterns(refined)
        mergedrex = [self.vrle2re(m, tagged=self.tag) for m in merged]
        mergedfrags = [self.vrle2refrags(m) for m in merged]
        return ResultsSummary(rles, rle_freqs, vrles, vrle_freqs,
                              merged, mergedrex, mergedfrags,
                              extractor=self)

    def coarse_classify(self, s):
        """
        Classify each character in a string into one of the coarse categories
        """
        return ''.join(self.coarse_classify_char(c) for c in s)


    def coarse_classify_char(self, c):
        """
        Classify character into one of the coarse categories
        """
        Cats = self.Cats
        for cat in Cats.SpecificCoarseCats:
            if re.match(cat.re_single, c):
                return cat.code
        assert re.match(Cats.Other.re_single, c)
        return Cats.Other.code


    def run_length_encode_coarse_classes(self, s):
        """
        Returns run-length encoded coarse classification
        """
        rle = run_length_encode(self.coarse_classify(s))
        if len(rle) <= MAX_GROUPS:
            return rle
        else:
            self.n_too_many_groups += 1
            return run_length_encode(CODE.ANY * len(s))


    def merge_patterns(self, patterns):
        if len(patterns) == 1:
            return patterns
        patterns = self.sort_by_length(patterns)
        level = 0
        parts = [patterns]  # Start off with each whole pattern
                            # as a single part
        n_parts = len(parts)
        DO_ALIGNMENT = True
        while level < N_ALIGNMENT_LEVELS and DO_ALIGNMENT:
            parts = self.alignment_step(parts, level)
            if len(parts) == n_parts:  # no change this time; next level
                level += 1
            else:
                n_parts = len(parts)
        patterns = self.join_parts(parts)
        return patterns

    def alignment_step(self, parts, level):
        new_parts = []
        n_parts = len(parts)
        for part in parts:
            if level == 0:
                new_parts.extend(self.merge_fixed_omnipresent_at_pos(part))
            elif level == 1:
                new_parts.extend(self.merge_fixed_only_present_at_pos(part))
            else:
                raise ValueError('Level out of range (%d)' % level)
        if self.verbose:
            print('\nOUT:')
            print(self.aligned_parts(new_parts))
        return new_parts

    def merge_fixed_omnipresent_at_pos(self, patterns):
        """
        Find unusual columns in fixed positions relative to ends.
        Align those
        Split and recurse
        """
        lstats = length_stats(patterns)
        if lstats.max_length <= 1:
            return [patterns]  # nothing to do
        frags = set()
        # First find fixed fragments that are present in the first pattern
        # for this part.
        for frag in patterns[0]:  # first pattern
            if len(frag) == 4:  # fixed
                frags.add(frag)
        frags = list(frags)

        # Now remove fragments that aren't in every pattern
        for pattern in patterns[1:]:
            i = 0
            while i < len(frags):
                if not frags[i] in pattern:
                    del frags[i]
                else:
                    i += 1

        if not frags:
            return [patterns]

        leftPos = {frag: Counter() for frag in frags}   # pos of frag from left
        rightPos = {frag: Counter() for frag in frags}  # ... and from right
        for pattern in patterns:
            n = len(pattern)
            for i, frag in enumerate(pattern):
                if frag in frags:
                    leftPos[frag][i] += 1
                    if not lstats.all_same_length:
                        rightPos[frag][n - i] += 1

        nPatterns = len(patterns)
        leftFixed = get_omnipresent_at_pos(leftPos, nPatterns)

        if leftFixed:
            return left_parts(patterns, leftFixed)
        rightFixed = get_omnipresent_at_pos(rightPos, nPatterns,
                                            verbose=self.verbose)
        if rightFixed:
            return right_parts(patterns, rightFixed)
        return [patterns]

    def merge_fixed_only_present_at_pos(self, patterns):
        """
        Find unusual columns in fixed positions relative to ends.
        Align those
        Split and recurse
        """
        lstats = length_stats(patterns)
        if lstats.max_length <= 1:
            return [patterns]  # nothing to do
        frags = set()
        # First find fixed fragments from all patterns
        for pattern in patterns:
            for frag in pattern:  # first pattern
                if len(frag) == 4:  # fixed
                    frags.add(frag)

        if not frags:
            return [patterns]

        leftPos = {frag: Counter() for frag in frags}   # pos of frag from left
        rightPos = {frag: Counter() for frag in frags}  # ... and from right
        for pattern in patterns:
            n = len(pattern)
            for i, frag in enumerate(pattern):
                if frag in frags:
                    leftPos[frag][i] += 1
                    if not lstats.all_same_length:
                        rightPos[frag][n - i] += 1

        nPatterns = len(patterns)
        leftFixed = get_only_present_at_pos(leftPos)

        if leftFixed:
            print('LEFT FOUND!', leftFixed)
            return left_parts(patterns, leftFixed)
        rightFixed = get_only_present_at_pos(rightPos, verbose=self.verbose)
        if rightFixed:
            print('RIGHT FOUND!', rightFixed)
            return right_parts(patterns, rightFixed)
        return [patterns]

    def join_parts(self, parts):
        if not parts:
            return []
        out = [[] for i in range(len(parts[0]))]
        for part in parts:
            for i, row in enumerate(part):
                if row:
                    out[i].extend(row)
        return out

    def sort_by_length(self, patterns):
        z = sorted(zip([len(p) for p in patterns], patterns))
        return [p for (L, p) in z]

    def pad(self, p, q):
        if self.verbose:
            print(self.vrle2re(self.despecify(p), True))
            print(self.vrle2re(self.despecify(q), True))
            print()
        return p  # padded

    def despecify(self, pattern):
        return list(self.despecify_frag(frag) for frag in pattern)

    def despecify_frag(self, frag):
        r, m, M = frag[:3]
        if m == M == 1:
            return frag
        else:
            return (r, 1, None) if len(frag) == 3 else (r, 1, None, 'fixed')

    def similarity(self, p, q):
        return 1

    def sample(self, nPerLength):
        """
        Sample strings for potentially faster induction.
        Only used if over a hundred million distinct strings are given.
        For now.
        """
        lengths = self.by_length.keys()
        lengths.sort()
        examples = []
        for L in lengths:
            x = self.by_length[L]
            if len(self.by_length[L]) <= nPerLength:
                examples.extend(x)
            else:
                examples.extend(random.sample(x, nPerLength))
        return examples

    def find_non_matches(self):
        """
        Returns all example strings that do not match any of the regular
        expressions in results.
        """
        failures = self.example_freqs.keys()
        if self.results:
            for r in self.results.rex:
                cr = cre(r)
                i = len(failures) - 1
                while i >= 0:
                    f = failures[i]
                    if re.match(cr, f):
                        del failures[i]
                    i -= 1
        return failures

    def refine_groups(self, pattern, examples):
        """
        Refine the categories for variable run-length-encoded patterns
        provided by narrowing the characters in the groups.
        """
        regex = cre(self.vrle2re(pattern, tagged=True))
        n_groups = len(pattern)
        group_chars = [set([]) for i in range(n_groups)]
        group_strings = [set([]) for i in range(n_groups)]
        n_strings = [0] * n_groups
        for example in examples:
            m = re.match(regex, example)
            if m:
                for i in range(n_groups):
                    g = m.group(i + 1)
                    if n_strings[i] <= SIZE.MAX_STRINGS_IN_GROUP:
                        group_strings[i].add(g)
                        n_strings[i] = len(group_strings[i])
                    group_chars[i] = group_chars[i].union(set(list(g)))
        out = []
        Cats = self.Cats
        for group, (chars, strings, fragment) in enumerate(zip(group_chars,
                                                               group_strings,
                                                               pattern)):
            (c, m, M) = fragment
            char_str = ''.join(sorted(chars))
            fixed = False
            refined = None
            if len(strings) == 1:
                refined = re.escape(list(strings)[0])
                m = M = 1
                fixed = True
            elif len(chars) == 1:
                refined = re.escape(list(chars)[0])
                fixed = True
            elif c == 'C':  # Alphanumeric
                for k in Cats.IncreasinglyGeneralAlphanumerics:
                    cat = getattr(Cats, k)
                    if type(cat) == tuple:
                        print('>>>', cat)
                    code = cat.code
                    if re.match(cat.re_multiple, char_str):
                        refined = re.escape(code)
                        break
                else:
                    refined = c
            elif (c == CODE.PUNC
                  and len(chars) <= SIZE.MAX_PUNC_IN_GROUP):  # Punctuation
                refined = '[%s]' % re.escape(char_str)
                fixed = True
            else:
                refined = c
            if fixed:
                out.append((refined, m, M, 'fixed'))
            else:
                out.append((refined, m, M))
        return out

    def fragment2re(self, fragment, tagged=False, as_re=True):
        (c, m, M) = fragment[:3]
        fixed = len(fragment) > 3
        Cats = self.Cats
        regex = c if (fixed or not as_re) else Cats[c].re_string
        if (m is None or m == 0) and M is None:
            part = regex + '*'
        elif M is None:
            part = regex + '+'
        elif m == M == 1:
            part = regex
        elif m == M:
            part = regex + ('{%d}' % m)
        else:
            part = regex + ('{%d,%s}' % (m, M))
        return ('(%s)' % part) if (tagged and not fixed) else part

    def vrle2re(self, vrles, tagged=False, as_re=True):
        """
        Convert variable run-length-encoded code string to regular expression
        """
        parts = [self.fragment2re(frag, tagged=tagged, as_re=as_re)
                 for frag in vrles]
        if self.n_stripped > 0:
            ws = [r'\s*']
            parts = ws + parts + ws
        return poss_term_re(''.join(parts))


    def vrle2refrags(self, vrles):
        """
        Convert variable run-length-encoded code string to regular expression
        and list of fragments
        """
        if self.n_stripped > 0:
            return ([Fragment(r'\s*', True)]
                    + [Fragment(self.fragment2re(frag, tagged=False,
                                                 as_re=True),
                              len(frag) < 4)
                       for frag in vrles]
                     + [Fragment(r'\s*', True)])

        else:
            return [Fragment(self.fragment2re(frag, tagged=False, as_re=True),
                             len(frag) < 4)
                    for frag in vrles]

    def rle2re(self, rles, tagged=False, as_re=True):
        """
        Convert run-length-encoded code string to regular expression
        """
        Cats = self.Cats
        parts = []
        for (c, freq) in rles:
            desc = Cats[c].re_string if as_re else c
            part = desc + ('{%d}' % freq if freq > 1 else '')
            parts.append(('(%s)' % part) if tagged else part)
        return poss_term_re(''.join(parts))


    def humanish_frag(self, frag):
        as_re = self.fragment2re(frag)
        return as_re.replace('\\', '').replace(' ', '_')

    def aligned_parts(self, parts):
        """
        Given a list of parts, each consisting of the fragments from a set
        of partially aligned patterns, show them aligned, and in a somewhat
        ambigous, numbered, fairly human-readable, compact form.
        """
        lines = [[] for i in range(len(parts[0]))]
        widths = []
        seps = []
        out = []
        for part in parts:
            stats = length_stats(part)
            for c in range(stats.max_length):  # col number in part
                w = 0
                for r, row in enumerate(part):
                    if len(row) > c:
                        frag = self.humanish_frag(row[c])
                        lines[r].append(frag)
                        w = max(w, len(frag))
                    else:
                        lines[r].append('')
                seps.append(' ')
                widths.append(w)
            if stats.max_length:
                seps[-1] = '|'
        header = '|' + ''.join((ndigits(w, i) + seps[i - 1])
                               for i, w in enumerate(widths, 1))
        fmts = ['%%%ds' % w for w in widths]
        body = '\n '.join(' '.join(fmt % frag
                                   for (fmt, frag) in zip(fmts, line))
                          for line in lines)
        return '\n'.join([header, ' ' + body])

    def __str__(self):
        return str(self.results or 'No results (yet)')


def run_length_encode(s):
    """
    Return run-length-encoding of string s, e.g.

    'CCC-BB-A' --> (('C', 3), ('-', 1), ('B', 2), ('-', 1), ('A', 1))
    """
    out = []
    last = None
    n = 0
    for c in s:
        if c == last:
            n += 1
        else:
            if last is not None:
                out.append((last, n))
            last = c
            n = 1
    if last is not None:
        out.append((last, n))
    return tuple(out)


def signature(rle):
    """
    Return the sequence of characters in a run-length encoding
    (i.e. the signature).

    Also works with variable run-length encodings
    """
    return ''.join(r[0] for r in rle)


def to_vrles(rles):
    """
    Convert a list of run-length encodings to a list of variable run-length
    encodings, one for each common signature.

    For example, given inputs of:

            (('C', 2),)
            (('C', 3),)
        and (('C', 2), ('.', 1))

    this would return

            (('C', 2, 3),)
        and (('C', 2, 2), ('.', 1, 1))
    """
    by_sig = defaultdict(list)
    outs = []
    for rle in rles:
        by_sig[signature(rle)].append(rle)
    for sig, rles in by_sig.items():
        nCats = len(sig)
        cats = list(sig)
        mins = [min(r[i][1] for r in rles) for i in range(nCats)]
        maxes = [max(r[i][1] for r in rles) for i in range(nCats)]
        outs.append(tuple([(cat, m, M)
                           for (cat, m, M) in zip(cats, mins, maxes)]))

    if MAX_VRLE_RANGE is not None:
        outs2 = [tuple(((cat, m, M) if (M - m) <= MAX_VRLE_RANGE
                                    else (cat, 1, None))
                       for (cat, m, M) in pattern)
                 for pattern in outs]
        outs = list(set(outs2))
        outs.sort()
    return outs


def ndigits(n, d):
    digit = chr((d + ord('0')) if d < 10 else (ord('A') + d - 10))
    return digit * n




class ResultsSummary(object):
    def __init__(self, rles, rle_freqs, vrles,
                 vrle_freqs, refined_vrles, rex, refrags, extractor=None):
        self.rles = rles
        self.rle_freqs = rle_freqs
        self.vrles = vrles
        self.vrle_freqs = vrle_freqs
        self.refined_vrles = refined_vrles
        self.rex = rex
        self.refrags = refrags
        self.extractor = extractor

    def to_string(self, rles=False, rle_freqs=False, vrles=False,
                  vrle_freqs=False, refined_vrles=False, rex=False,
                  fmt='code'):
        assert fmt in ('code', 're', 'raw')
        as_re = fmt == 're'
        short = fmt in ('re', 'code')
        allFalse = not any((rles, rle_freqs, vrles,
                            vrle_freqs, refined_vrles, rex))
        out = []
        if rles or allFalse:
            out.append('Run-length encoded patterns (rles):')
            for i, rle in enumerate(self.rles, 1):
                out.append('%2d: %s'
                           % (i, self.to_re(rle, as_re=as_re) if short
                              else str(rle)))
            out.append('')

        if rle_freqs or allFalse:
            out.append('Run-length encoded pattern freqencies (rle_freqs):')
            for i, (rle, freq) in enumerate(self.rle_freqs.items(), 1):
                out.append('%2d: %s: %d'
                           % (i,
                              self.to_re(rle, as_re=as_re) if short
                                                           else str(rle),
                              freq))
            out.append('')

        if vrles or allFalse:
            out.append('Variable run-length encoded patterns (vrles):')
            for i, vrle in enumerate(self.vrle_freqs, 1):
                out.append('%2d: %s'
                           % (i, self.to_re(vrle, as_re=as_re) if short
                                                               else str(vrle)))
            out.append('')

        if vrle_freqs or allFalse:
            out.append('Variable run-length encoded pattern freqencies '
                       '(vrle_freqs):')
            for i, (vrle, freq) in enumerate(self.vrle_freqs.items(), 1):
                out.append('%2d: %s: %d'
                           % (i,
                              self.to_re(vrle, as_re=as_re) if short
                                                            else str(vrle),
                              freq))
            out.append('')

        if refined_vrles or allFalse:
            out.append('Refined variable run-length encoded patterns '
                       '(refined_vrles):')
            for i, p in enumerate(self.refined_vrles, 1):
                out.append('%2d: %s'
                           % (i, self.to_re(p, as_re=as_re) if short
                                                            else str(p)))
            out.append('')

        if rex or allFalse:
            out.append('Refined variable run-length encoded patterns (rex):')
            for i, r in enumerate(self.rex, 1):
                out.append('%2d: %s' % (i, r))
            out.append('')
        return '\n'.join(out)

    def to_re(self, patterns, grouped=False, as_re=True):
        f = (self.extractor.rle2re if len(patterns[0]) == 2
                                   else self.extractor.vrle2re)
        return f(patterns, tagged=grouped, as_re=as_re)

    def __str__(self):
        return self.to_string()



def extract(examples, tag=False, encoding=None, as_object=False,
            extra_letters=None, verbose=False):
    """
    Extract regular expression(s) from examples and return them.

    Normally, examples should be unicode (i.e. str in Python3,
    and unicode in Python2). However, encoded strings can be
    passed in provided the encoding is specified.

    Results will always be unicode.

    If as_object is set, the extractor object is returned,
    with results in .results.rex; otherwise, a list of regular
    expressions, as unicode strings is returned.
    """
    if encoding:
        examples = [x.decode(encoding) for x in examples]
    r = Extractor(examples, tag=tag, extra_letters=extra_letters,
                  verbose=verbose)
    return r if as_object else r.results.rex


def pdextract(cols):
    """
    Extract regular expression(s) from the pandas column (Series) object
    or list of pandas columns given.

    All columns provided should be string columns (i.e. of type np.dtype('O'),
    possibly including null values, which will be ignored.

    Example use:
        import pandas as pd
        from tdda.rexpy import pdextract

        df = pd.DataFrame({'a3': ["one", "two", pd.np.NaN],
                           'a45': ['three', 'four', 'five']})

        re3 = pdextract(df['a3'])
        re45 = pdextract(df['a45'])
        re345 = pdextract([df['a3'], df['a45']])

    This should result in
        re3   = '^[a-z]{3}$'
        re5   = '^[a-z]{3}$'
        re345 = '^[a-z]{3}$'
    """
    if not type(cols) in (list, tuple):
        cols = [cols]
    strings = []
    for c in cols:
        strings.extend(list(c.dropna().unique()))
    try:
        return extract(strings)
    except:
        if not all(type(s) == str_type for s in strings):
            raise ValueError('Non-null, non-string values found in input.')
        else:
            raise


def get_omnipresent_at_pos(fragFreqCounters, n, **kwargs):
    """
    Find patterns in fragFreqCounters for which the frequency is n.

    fragFreqCounters is a dictionary (usually keyed on 'fragments')
    of whose values are dictionaries mapping positions to frequencies.
    For example:
        {
            ('a', 1, 1, 'fixed'): {1: 7, -1: 7, 3: 4},
            ('b', 1, 1, 'fixed'): {2: 6, 3: 4},
        }

    This indicates that the pattern ('a', 1, 1, 'fixed'} has frequency
    7 at positions 1 and -1, and frequency 4 at position 3, while
    pattern ('b', 1, 1, 'fixed') has frequency 6 at position 2 and
    4 at position 3.

    With n set to 7, this returns

        [
            (('a', 1, 1, 'fixed'), -1)
            (('a', 1, 1, 'fixed'), 1),
        ]

    (sorted on pos; each pos really should occur at most once.)
    """
    out = []
    for frag, fragFreqs in fragFreqCounters.items():
        for pos, freq in fragFreqs.items():
            if freq == n:
                out.append((frag, pos))
    out.sort(key=lambda x: x[1])
    return out


def get_only_present_at_pos(fragFreqCounters, *args, **kwargs):
    """
    Find patterns in fragFreqCounters that, when present, are always
    at the same position.

    fragFreqCounters is a dictionary (usually keyed on 'fragments')
    of whose values are dictionaries mapping positions to frequencies.
    For example:
        {
            ('a', 1, 1, 'fixed'): {1: 7, -1: 7, 3: 4},
            ('b', 1, 1, 'fixed'): {2: 6},
        }

    This indicates that the
      - pattern ('a', 1, 1, 'fixed'} has frequency 7 at positions 1 and -1,
        and frequency 4 at position 3;
      - pattern ('b', 1, 1, 'fixed') has frequency 6 at position 2 (only)

    So this would return

        [
            (('b', 1, 1, 'fixed'), 2)
        ]

    (sorted on pos; each pos really should occur at most once.)
    """
    out = []
    print(fragFreqCounters)
    for frag, fragFreqs in fragFreqCounters.items():
        if len(fragFreqs) == 1:
            pos = fragFreqs.keys()[0]  # the only position
            out.append((frag, pos))
    out.sort(key=lambda x: x[1])
    return out


def left_parts(patterns, fixed):
    """
    patterns is a list of patterns each consisting of a list of frags.

    fixed is a list of (fragment, position) pairs, sorted on position,
    specifying points at which to split the patterns.

    This function returns a list of lists of pattern fragments,
    split at each fixed position.
    """
    if not fixed:
        return [patterns]
    lastPos = -1
    out = []
    lstats = length_stats(patterns)
    for (frag, pos) in fixed:
        if pos > 0:  # Nothing to the left if it's position 0
            out.append([p[lastPos + 1:pos] for p in patterns])
#        out.append([p[pos:pos + 1] for p in patterns])  # the fixed bit
        out.append([[p[pos]] for p in patterns])  # the fixed bit
        lastPos = pos
    if lastPos < lstats.max_length - 1:  # the end, if there's anything left
        out.append([p[lastPos + 1:] for p in patterns])
    return out


def right_parts(patterns, fixed):
    """
    patterns is a list of patterns each consisting of a list of frags.

    fixed is a list of (fragment, pos) pairs where position specifies
    the position from the right, i.e a position that can be indexed as
    -position. Fixed should be sorted, increasing on position, i.e.
    sorted from the right-most pattern.
    The positions specify points at which to split the patterns.

    This function returns a list of lists of pattern fragments,
    split at each fixed position.
    """
    if not fixed:
        return [patterns]
    out = []
    lstats = length_stats(patterns)
    lastPos = -lstats.max_length  # will be reversed in use
    for (frag, pos) in fixed:
        if pos > 1:  # Nothing the right if it's position -1
            out.append([p[-pos + 1:-lastPos] for p in patterns])
        out.append([[p[-pos]] for p in patterns])  # the fixed bit
        lastPos = pos
    if lastPos < lstats.max_length:  # the start, if there's anything left
        out.append([p[:-lastPos] for p in patterns])
    out.reverse()  # We built it up from the right; so we must reverse it
    return out


def length_stats(patterns):
    """
    Given a list of patterns, returns named tuple containing

        all_same_length: boolean, True if all patterns are the same length
        max_length:      length of the longest pattern in patterns
    """
    lengths = [len(p) for p in patterns]
    L0 = lengths[0] if lengths else 0
    LS = namedtuple('lengthstats', 'all_same_length max_length')
    return LS(all(L == L0 for L in lengths), max(lengths) if lengths else 0)


def get_nCalls():
    global nCalls
    return nCalls


def main(in_path=None, out_path=None, skip_header=False, **kwargs):
    if in_path:
        with open(in_path) as f:
            strings = f.read().splitlines()
    else:
        strings = sys.stdin.readlines()
    if skip_header:
        strings = strings[1:]
    patterns = extract(strings, **kwargs)
    if out_path:
        with open(out_path, 'w') as f:
            for p in patterns:
                f.write(p + '\n')
    else:
        for p in patterns:
            print(p)


def get_params(args):
    params = {
        'in_path': '',
        'out_path': None,
        'skip_header': False,
        'extra_letters': None,
        'tag': None,
    }
    for a in args:
        if a.startswith('-'):
            if a == '-':
                params['in_path'] = None
            elif a in ('-h', '--header'):
                params['skip_header'] = True
            elif a in ('-g', '--group'):
                params['tag'] = True
            elif a in ('-u', '-_', '--underscore'):
                params['extra_letters'] = (params['extra_letters'] or '') + '_'
            elif a in ('-d', '-.', '--dot', '--period'):
                params['extra_letters'] = (params['extra_letters'] or '') + '.'
            elif a in ('-m', '--minus', '--hyphen', '--dash'):
                params['extra_letters'] = (params['extra_letters'] or '') + '-'
            elif a in ('-?', '--help'):
                print(USAGE)
                sys.exit(0)
            else:
                raise Exception(USAGE)
        elif params['in_path'] == '':  # not previously set and not '-'
            params['in_path'] = a
        elif params['out_path'] is None:
            params['out_path'] = a
        else:
            raise Exception(USAGE)
    params['in_path'] = params['in_path']  or None  # replace '' with None
    extras = params['extra_letters']
    if extras:
        params['extra_letters'] =  ''.join(sorted([c for c in extras]))
        # Order always, for consistency
    return params


def usage_error():
    print(USAGE, file=sys.stderr)
    sys.exit(1)


if __name__ == '__main__':
    params = get_params(sys.argv[1:])
    main(**params)
