"""
Rexpy: Automatic Regular Expression Extraction
-----------------------------------------------

Given a set of example strings, rexpy infers one or more regular
expressions that collectively match them all. When a single pattern
would require a large alternation to cover structurally different
inputs, rexpy produces multiple patterns instead — one per distinct
structure — so each remains readable and precise.

Algorithm
~~~~~~~~~

Extraction proceeds in the following stages:

1. **Coarse classification.** Each character is assigned to a broad
   category: lowercase letter, uppercase letter, digit, punctuation,
   whitespace, or a catch-all. The result is a sequence of category
   codes for each string.

2. **Run-length encoding (RLE).** Consecutive characters in the same
   category are collapsed into ``(category, count)`` pairs. For
   example, ``"hello123"`` becomes ``[(letter, 5), (digit, 3)]``.

3. **Variable run-length encoding (VRLE).** RLEs that share the same
   sequence of categories but differ only in their counts are merged
   into a single variable pattern. For example, ``[(letter, 3)]``
   and ``[(letter, 5)]`` both have the shape ``[letter]`` and merge
   into ``[(letter, 3, 5)]``.

4. **Fragment refinement.** Within each fragment position of a VRLE,
   the actual characters seen across all matching examples are
   examined to find the narrowest character class that fits — for
   instance, hex digits rather than all alphanumeric characters.

5. **Pattern merging.** The refined VRLEs are aligned and merged.
   Fixed literal sub-sequences that appear at a consistent position
   (relative to the start or end) across all patterns in a group are
   used as anchors: patterns are split at those anchors and the
   pieces are recursively merged. Patterns too different to reconcile
   remain as separate entries in the output.

6. **Regex generation.** Each merged pattern is converted to a
   regular expression string in the requested output dialect
   (``'portable'``, ``'grep'``, ``'java'``, ``'perl'``, or
   ``'posix'``).

For large inputs, rexpy works on a sample first and then checks
which examples the resulting patterns fail to match. Any failures
are folded back into the working set and extraction is repeated,
ensuring that even sampled runs achieve complete coverage.

Python API
~~~~~~~~~~

The simplest entry point is the :func:`extract` function; the
:class:`Extractor` class gives full control over the process and
provides access to coverage statistics.
"""

import random
import re
import sys

from array import array
from collections import Counter, defaultdict, namedtuple, OrderedDict
from pprint import pprint

from tdda import __version__
from tdda.abstractdf import is_polars_series
from tdda.utils import nvl, TDDAError


INT_ARRAY = 'i'
UNESCAPES = """!"%',/:;<=>@_` """

VERBOSITY_LEVEL_RE = r'^-v(-?[0-9]+)$'


class VERBOSITY:
    PASSES = 0b1  # 1; old verbose
    ALL = 0b01  # 2; same as MAX
    INPUTS = 0b100
    SORTED = 0b1000
    RLE = 0b10000
    VRLE = 0b100000
    MERGED = 0b1000000
    SPECIALIZED = 0b10000000
    MERGED_REX = 0b100000000
    MERGED_FRAGS = 0b1000000000
    ALIGNED = 0b10000000000
    PREPROCESSING = 0b1000000000000
    DETAIL = 0b10000000000000
    MAX = -1


########################################
#
# KEEP IN SYNC WITH rexpy.txt in doc dir
#
########################################

USAGE = r"""Usage:

    rexpy [FLAGS] [INPUTFILE [OUTPUTFILE]]

If INPUTFILE is provided, it should contain one string per line;
otherwise lines will be read from standard input.

If OUTPUTFILE is provided, regular expressions found will be written
to that (one per line); otherwise they will be printed.

Optional FLAGS may be used to modify Rexpy's behaviour:

  -h, --header      Discard first line, as a header.

  -?, --help        Print this usage information and exit (without error)

  -g, --group       Generate capture groups for each variable fragment
                    of each regular expression generated, i.e. surround
                    variable components with parentheses
                        e.g.     ^[A-Z]+\-[0-9]+$
                        becomes  ^([A-Z]+)\-([0-9]+)$

  -q, --quote       Display the resulting regular expressions as
                    double-quoted, escaped strings, in a form broadly
                    suitable for use in Unix shells, JSON, and string
                    literals in many programming languages.
                        e.g.     ^[A-Z]+\-[0-9]+$
                        becomes  "^[A-Z]+\-[0-9]+$"

  --portable        Produce maximally portable regular expressions
                    (e.g. [0-9] rather than \d). (This is the default.)

  --grep            Same as --portable

  --java            Produce Java-style regular expressions (e.g. \p{Digit})

  --posix           Produce POSIX-compilant regular expressions
                    (e.g. [[:digit:]] rather than \d).

  --perl            Produce Perl-style regular expressions (e.g. \d)

  -u, --underscore  Allow underscore to be treated as a letter.
                    Mostly useful for matching identifiers
                    Also allow -_.

  -d, --dot         Allow dot to be treated as a letter.
                    Mostly useful for matching identifiers.
                    Also -. --period.

  -m, --minus       Allow minus to be treated as a letter.
                    Mostly useful for matching identifiers.
                    Also --hyphen or --dash.

  -1, --single      Combine multiple regular expressions found into a
                    single regular expression, using alternation.
                        e.g.     ^[A-Z]{2}$
                                 ^[0-9]{3}$
                        becomes  ^([A-Z]{2}|[0-9]{3})$

  -v, --version     Print the version number.

  -V, --verbose     Set verbosity level to 1

  -VV, --Verbose    Set verbosity level to 2

  -vlf, --variable  Use variable length fragments

  -flf, --fixed     Use fixed length fragments
"""
########################################
#
# KEEP IN SYNC WITH rexpy.txt in doc dir
#
########################################

MIN_MERGE_SIMILARITY = 0.5
TERMINATE = True  # False

N_ALIGNMENT_LEVELS = 1

MAX_GROUPS = 99  # re library fails with AssertionError:
# sorry, but this version only supports 100 named groups
# if you have too many groups.
# Looks like actual limit might be 99, not 100...

MAX_VRLE_RANGE = 2  # Meaning that it will only produce patterns like
# x{m,n} when n - m ≤ 2

VARIABLE_LENGTH_FRAGS = False
DEFAULT_VERBOSITY = 0

MAX_PATTERNS = None
MIN_DIFF_STRINGS_PER_PATTERN = 1
MIN_STRINGS_PER_PATTERN = 1

USE_SAMPLING = True

RE_FLAGS = re.UNICODE | re.DOTALL

DIALECTS = ['perl']

DO_ALL_SIZE = 100000000


class Size(object):
    def __init__(self, **kwargs):
        self.use_sampling = nvl(
            kwargs.get('use_sampling', USE_SAMPLING), USE_SAMPLING
        )
        do_all = kwargs.get('do_all')
        if do_all is None:
            if self.use_sampling:
                do_all = 100  # Use all examples up to this many
            else:
                do_all = DO_ALL_SIZE  # Use all examples up to this many
        self.do_all = do_all
        self.do_all_exceptions = 4000  # Add in all failures up to this many
        self.n_per_length = 64  # When sampling, use this many
        # of each length
        self.max_sampled_attempts = 2  # Give up and use all after this many
        # sampled attempts

        self.max_punc_in_group = 5
        self.max_strings_in_group = 10
        for k, v in kwargs.items():
            if k in self.__dict__:
                if v is None and k not in ('use_sampling', 'do_all'):
                    raise TDDAError(
                        'Bad null value for parameter %s to Size.' % k
                    )
                else:
                    self.__dict__[k] = v
            else:
                raise TDDAError('Unknown parameter to Size: "%s" % k')


nCalls = 0
memo = {}


def cre(rex):
    """
    Compiled regular expression
    Memoized implementation.
    """
    global nCalls, memo
    nCalls += 1
    c = memo.get(rex)
    if c:
        return c
    else:
        memo[rex] = c = re.compile(rex, RE_FLAGS)
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

    def set(self, rex):
        self.re_string = rex


UNICHRS = True  # controls whether to include a unicode letter class
UNIC = 'Ḉ'  # K
COARSEST_ALPHANUMERIC_CODE = UNIC if UNICHRS else 'C'

DIALECTS = [
    'grep',
    'java',
    'perl',
    'portable',
    'posix',
]

DEFAULT_DIALECT = 'portable'


class Categories(object):
    escapableCodes = '.*?'

    def __init__(self, extra_letters=None, full_escape=False, dialect=None):
        if extra_letters:
            assert all(L in '_.-' for L in extra_letters)  # For now
            extra_letters = ''.join(
                e for e in '_.-' if e in extra_letters
            )  # Force '-' to end
            el_re = extra_letters
            el_re_exc = '' if '_' in extra_letters else '_'
        else:
            el_re = ''
            el_re_exc = '_'
        el_re_inc = (extra_letters or '').replace('_', '')
        punctuation = self.PunctuationChars(el_re)
        self.dialect = dialect
        self.extra_letters = extra_letters or ''
        self.full_escape = full_escape
        self.LETTER = Category('LETTER', 'A', '[A-Z]')
        self.letter = Category('letter', 'a', '[a-z]')
        self.Letter = Category('Letter', 'L', '[A-Za-z]')
        self.ULetter = Category('ULetter', 'Ḹ', r'[^\W0-9_]')
        if extra_letters:
            self.LETTER_ = Category('LETTER_', 'B', '[A-Z%s]' % el_re)
            self.letter_ = Category('letter_', 'b', '[a-z%s]' % el_re)
            self.Letter_ = Category('Letter_', 'M', '[A-Za-z%s]' % el_re)
            if extra_letters == '_':
                self.ULetter_ = Category('ULetter_', 'Ṃ', r'[^\W0-9]')
            else:
                p = u_alpha_numeric_re(
                    el_re_inc, el_re_exc, digits=False, dialect=dialect
                )
                self.ULetter_ = Category('ULetter_', 'Ṃ', p)

            ExtraLetterGroups = ['LETTER_', 'letter_', 'Letter_'] + (
                ['ULetter_'] if UNICHRS else []
            )
        else:
            self.ULetter_ = Category('ULetter_', 'Ṃ', r'[^\W0-9_]')
            ExtraLetterGroups = []
        self.Digit = Category('Digit', 'D', r'\d')
        self.hex = Category('hex', 'h', '[0-9a-f]')
        self.HEX = Category('HEX', 'H', '[0-9A-F]')
        self.Hex = Category('Hex', 'X', '[0-9a-fA-F]')
        self.ALPHANUMERIC = Category('ALPHANUMERIC', 'N', '[A-Z0-9%s]' % el_re)
        self.alphanumeric = Category('alphanumeric', 'n', '[a-z0-9%s]' % el_re)
        self.AlphaNumeric = Category(
            'AlphaNumeric', 'C', '[A-Za-z0-9%s]' % el_re
        )
        self.UAlphaNumeric = Category(
            'UAlphaNumeric',
            'Ḉ',
            u_alpha_numeric_re(el_re_inc, el_re_exc, dialect=dialect),
        )
        self.Whitespace = Category('Whitespace', ' ', r'\s')
        self.Punctuation = Category(
            'Punctuation',
            CODE.PUNC,
            escaped_bracket(punctuation, dialect=dialect),
        )

        self.Other = Category('Other', '*', r'[^!-~\s]')
        self.Any = Category('Any', CODE.ANY, '.')

        self.SpecificCoarseCats = [
            self.UAlphaNumeric if UNICHRS else self.AlphaNumeric,
            self.Whitespace,
            self.Punctuation,
        ]
        self.AllCoarseCats = self.SpecificCoarseCats + [self.Other]
        self.IncreasinglyGeneralAlphanumerics = (
            [
                'Digit',
                'LETTER',
                'letter',
                'Letter',
            ]
            + (['ULetter'] if UNICHRS else [])
            + ExtraLetterGroups
            + [
                'HEX',
                'hex',
                'Hex',
                'ALPHANUMERIC',
                'alphanumeric',
                'AlphaNumeric',
            ]
            + (['UAlphaNumeric'] if UNICHRS else [])
        )
        if dialect and dialect != 'perl':
            self.adapt_for_output(dialect, el_re)

    def PunctuationChars(self, el_re):
        specials = re.compile(r'[A-Za-z0-9\s%s]' % el_re, RE_FLAGS)
        return [
            chr(c) for c in range(32, 127) if not re.match(specials, chr(c))
        ]

    def build_cat_map(self):
        """
        Lazily builds (on first use) mapping from single-character category
        codes to Category Objects, stores in self.code2cat, which is used
        by __getitem__. e.g.

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

    @classmethod
    def escape_code(cls, code):
        return escape(code, full=False) if code in cls.escapableCodes else code

    def escape(self, s, full=None):
        return escape(s, full=self.full_escape if full is None else full)

    def adapt_for_output(self, dialect, el_re):
        """
        This converts the output regular expressions for each kind of
        fragment identified to one of the supported, dialects, as listed
        below.

        This is called at the very end of regular-expression generation,
        since not all dialects can be used internally for determining
        what patterns to generate.
        """
        if dialect in ('portable', 'grep'):
            self.Digit.set(r'[0-9]')
        elif dialect == 'posix':
            self.Digit.set(r'[[:digit:]]')

            self.letter.set(r'[[:lower:]]')
            self.LETTER.set(r'[[:upper:]]')
            self.Letter.set(r'[[:alpha:]]')
            self.ULetter.set(r'[[:alpha:]]')
            self.Hex.set(r'[[:xdigit:]]')
            self.Whitespace.set(r'[[:space:]]')
            if el_re:
                self.ALPHANUMERIC.set('[[:upper:][:digit:]%s]' % el_re)
                self.alphanumeric.set('[[:lower:][:digit:]%s]' % el_re)
                self.AlphaNumeric.set('[[:alnum:]%s]' % el_re)
                self.UAlphaNumeric.set('[[:alnum:]%s]' % el_re)
            else:
                self.Punctuation.set(r'[[:punct:]]')

        elif dialect == 'java':
            self.Digit.set(r'\p{Digit}')
            self.letter.set(r'\p{Lower}')
            self.LETTER.set(r'\p{Upper}')
            self.Letter.set(r'\p{Alpha}')
            self.ULetter.set(r'\p{Alpha}')
            self.Hex.set(r'\p{XDigit}')
            self.Whitespace.set(r'\p{Space}')
            if el_re:
                self.ALPHANUMERIC.set(r'[\p{Upper}\p{Digit}%s]' % el_re)
                self.alphanumeric.set(r'[\p{Lower}\p{Digit}%s]' % el_re)
                self.AlphaNumeric.set(r'[\p{Alnum}%s]' % el_re)
                self.UAlphaNumeric.set(r'[\p{Alnum}%s]' % el_re)
            else:
                self.Punctuation.set(r'\p{Punct}')
        else:
            raise TDDAError('Unknown dialect: %s' % dialect)


class Fragment(namedtuple('Fragment', 're group')):
    """
    Container for a fragment.

    Attributes:
        re: The regular expression for the fragment.
        group: True if it forms a capture group (i.e. is not constant).
    """


class Coverage(namedtuple('Coverage', 'n n_uniq incr incr_uniq index')):
    """
    Container for coverage information.

    Attributes:
        n: Number of matches.
        n_uniq: Number of matches, deduplicating strings.
        incr: Number of new (unique) matches for this regex.
        incr_uniq: Number of new (unique) deduplicated matches for this regex.
        index: Index of this regex in the original list returned.
    """


def Tree():
    return defaultdict(list)


class Examples(object):
    def __init__(self, strings, freqs=None):
        self.strings = strings
        self.freqs = freqs if freqs is not None else [1] * len(strings)
        assert len(self.strings) == len(set(self.strings))
        self.update()

    def update(self):
        self.n_uniqs = len(self.strings)
        self.n_strings = sum(self.freqs)


class Extractor(object):
    """
    Regular expression extractor.

    Given a set of examples, constructs a regular expression that
    characterizes them; or, if no single pattern suffices, a list of
    regular expressions that collectively cover the cases.

    Results are stored in ``self.results`` once extraction has occurred,
    which happens by default on initialization but can be triggered
    manually by calling ``extract()``.

    Args:
        examples: The input strings to analyse. May be:

            - a list of strings, one per example
            - an integer-valued, string-keyed dictionary (or
              ``Counter``), where the values are taken as string
              frequencies (must be non-negative)
            - a callable conforming to the
              ``example_check_function`` protocol

        extract (bool): If ``True`` (the default), run extraction
            immediately on initialization. Set to ``False`` to
            defer extraction and call ``extract()`` manually.
        tag (bool): If ``True``, return tagged (capturing-group)
            regular expressions instead of plain ones.
        extra_letters (str): Additional characters to treat as
            word letters when building character classes. By
            default only standard alphanumeric characters qualify.
        full_escape (bool): If ``True``, escape all special regex
            characters, not just those strictly necessary.
        remove_empties (bool): If ``True``, discard empty strings
            from the examples before extraction.
        strip (bool): If ``True``, strip leading and trailing
            whitespace from each example before extraction.
        variableLengthFrags (bool): If ``True``, allow fragments
            of variable length within patterns. Off by default,
            which produces simpler patterns.
        specialize (bool): If ``True``, produce more specialized
            (narrower) patterns that match fewer strings outside
            the examples.
        max_patterns (int): Maximum number of patterns to produce.
            ``None`` (the default) means no limit.
        min_diff_strings_per_pattern (int): Minimum number of
            distinct strings a pattern must account for. Currently
            ignored.
        min_strings_per_pattern (int): Minimum total number of
            strings (counting duplicates) a pattern must account
            for to be retained. Default is ``1``.
        size: Controls sampling behaviour. Pass a ``Size``
            instance to tune the sampling parameters, ``None``
            (the default) to use rexpy's built-in defaults, or
            ``False``/``0`` to disable sampling entirely.
        seed (int): Random seed for reproducibility when sampling.
            ``None`` (the default) means non-deterministic.
        dialect (str): The kind of regular expression to emit.
            One of ``'portable'`` (the default), ``'grep'``,
            ``'java'``, ``'perl'``, or ``'posix'``.
        verbose (int): Verbosity level. ``0`` (the default) is
            silent. ``1`` prints some progress information.
            ``2`` prints maximum detail.
    """

    def __init__(
        self,
        examples,
        extract=True,
        tag=False,
        extra_letters=None,
        full_escape=False,
        remove_empties=False,
        strip=False,
        variableLengthFrags=VARIABLE_LENGTH_FRAGS,
        specialize=False,
        max_patterns=MAX_PATTERNS,
        min_diff_strings_per_pattern=MIN_DIFF_STRINGS_PER_PATTERN,
        min_strings_per_pattern=MIN_STRINGS_PER_PATTERN,
        size=None,
        seed=None,
        dialect=DEFAULT_DIALECT,
        verbose=DEFAULT_VERBOSITY,
        single=None,
    ):
        """Initialize and, unless extract=False, run extraction."""
        self.verbose = self._set_verbosity(verbose)
        self.size = size or Size(use_sampling=False if size == 0 else None)
        if self.size.use_sampling:
            self.by_length = Tree()  # Also store examples by length
        self.n_stripped = 0  # Number that required stripping
        self.n_empties = 0  # Number of empty string found
        self.n_nulls = 0  # Number of nulls found
        self.remove_empties = remove_empties
        self.strip = strip
        self.variableLengthFrags = variableLengthFrags
        self.specialize = specialize
        self.tag = tag  # Returned tagged (grouped) RE
        # self.examples = self._clean(examples)  !!!
        if callable(examples):
            self.check_fn = examples
        else:
            self.check_fn = self._check_for_failures
            self.all_examples = self._clean(examples)
        strings, _ = self.check_fn([], self.size.do_all)
        self.examples = self._clean(strings)

        self.results = None
        self.warnings = []
        self.n_too_many_groups = 0
        self.Cats = Categories(
            self._thin_extras(extra_letters), full_escape=full_escape
        )  # no dialect
        if dialect == 'perl':
            dialect = None
        self.dialect = dialect
        if dialect is not None:
            self.OutCats = Categories(
                self._thin_extras(extra_letters),
                full_escape=full_escape,
                dialect=dialect,
            )  # output dialect
        self.full_escape = full_escape
        self.max_patterns = max_patterns
        self.min_diff_strings_per_pattern = min_diff_strings_per_pattern
        self.min_strings_per_pattern = min_strings_per_pattern
        self.max_patterns = nvl(max_patterns, MAX_PATTERNS)
        self.seed = seed
        self.single = single

        if extract:
            self.extract()  # Stores results

    def _set_verbosity(self, verbosity):
        if type(verbosity) != int:
            verbosity = int(bool(verbosity))
        if verbosity == 2:  # old max
            verbosity = VERBOSITY.MAX
        return verbosity

    def extract(self):
        """
        Run the regular expression extraction.

        Analyses the examples supplied at initialization and populates
        ``self.results`` with the extracted patterns. The regular
        expressions are then available as ``self.results.rex``.

        Called automatically on initialization unless ``extract=False``
        was passed.
        """
        self.prng_state = PRNGState(self.seed)
        try:
            size = self.size
            if self.examples.n_uniqs == 0:
                self.results = None
                return

            attempt = 1
            failures = []
            self._show_inputs()
            while attempt <= size.max_sampled_attempts + 1:
                if self._show(VERBOSITY.PASSES):
                    strings = self.examples.strings
                    print(
                        '\n*** Pass %d (%s strings)' % (attempt, len(strings))
                    )
                    if self._show(VERBOSITY.DETAIL):
                        print(
                            'Examples: %s ... %s' % (strings[:5], strings[-5:])
                        )
                self.results = self._batch_extract()
                maxN = (
                    None
                    if attempt > size.max_sampled_attempts
                    else size.do_all_exceptions
                )
                failex, re_freqs = self.check_fn(self.results.rex, maxN)
                failex = self._clean(failex)
                if self._show(VERBOSITY.PASSES):
                    print('%s REs:' % len(self.results.rex))
                    for r in self.results.rex:
                        print('    %s' % r)
                    print(
                        '\nFailures (%d): %s'
                        % (len(failex.strings), failex.strings[:5])
                    )
                if len(failex.strings) == 0:
                    break
                elif (
                    len(failex.strings) <= size.do_all_exceptions
                    or attempt > size.max_sampled_attempts
                ):
                    if self._show(VERBOSITY.PASSES):
                        print('\n\n\n*** Now doing all failures...')
                    self.examples.strings.extend(failex.strings)
                    self.examples.freqs.extend(failex.freqs)
                    self.examples.update()
                    if self._show(VERBOSITY.PASSES):
                        print(
                            '\n\n\n*** Total strings = %s'
                            % len(failex.strings)
                        )
                else:
                    z = list(zip(failex.strings, failex.freqs))
                    if len(z) > size.do_all_exceptions:
                        sampled = random.sample(z, size.do_all_exceptions)
                    else:
                        sampled = z
                    self.examples.strings.extend(s[0] for s in sampled)
                    self.examples.freqs.extend(s[1] for s in sampled)
                    self.examples.update()
                attempt += 1

            self._add_warnings()
            self.results.remove(self._find_bad_patterns(re_freqs))
            self._convert_rex_to_dialect()
        finally:
            self.prng_state.restore()
        if self.single is True and self.results is not None:
            self.results.rex = combine_patterns(self.results.rex)

    def _show(self, verbosity):
        """
        Returns whether to show something at the verbosity level provided.
        Usually verbosity is a value from (or a combined value from)
        the levels in VERBOSITY
        """
        return self.verbose & verbosity

    def _show_inputs(self):
        if self._show(VERBOSITY.INPUTS):
            print('INPUTS:')
            for s in self.examples.strings:
                print(s)
            print()

    def _check_for_failures(self, rexes, maxExamples):
        """
        This method is the default check_fn
        (See the definition of example_check_function below.)
        """
        failures, freqs, re_freqs = self._sample_non_matches(rexes, maxExamples)
        return Examples(failures, freqs), re_freqs

    def _find_bad_patterns(self, freqs):
        """
        Given freqs, a list of frequencies (for the corresponding indexed RE)
        identify indexes to patterns that:

          - have too few strings
          - cause too many patterns to be returned

        NOTE: min_diff_strings_per_pattern is currently ignored.

        Returns set of indices for deletion
        """
        M = self.max_patterns
        deletions = set()
        if M is not None and len(freqs) > self.max_patterns:
            deletions = set(
                list(sorted(range(len(freqs)), key=lambda k: -freqs[k]))[M:]
            )

        m = self.min_strings_per_pattern
        if m > 1:
            deletions = deletions.union(
                {i for (i, v) in enumerate(freqs) if v < m}
            )
        return deletions

    def _add_warnings(self):
        if self.n_too_many_groups:
            self.warnings.append(
                '%d string%s assigned to .{m,n} for needing '
                '"too many" groups.'
                % (
                    self.n_too_many_groups,
                    's' if self.n_too_many_groups > 1 else '',
                )
            )

    def _thin_extras(self, extra_letters):
        if not extra_letters or len(extra_letters) == 1:
            return extra_letters
        keep = []
        for L in extra_letters:
            if any(L in example for example in self.examples.strings):
                keep.append(L)
        return ''.join(keep) if keep else None

    def _clean(self, examples):
        """
        Normalize examples into an ``Examples`` object.

        Handles null removal, stripping, empty removal, and
        deduplication with frequency counting.
        """
        isdict = isinstance(examples, dict)
        isExamples = isinstance(examples, Examples)
        counter = Counter()
        items = examples.strings if isExamples else examples
        for i, s in enumerate(items):
            n = (
                examples[s]
                if isdict
                else examples.freqs[i]
                if isExamples
                else 1
            )
            if s is None:
                self.n_nulls += n
            elif n == 0:
                continue  # dictionary entry with count 0
            else:
                stripped = s.strip() if self.strip else s
                L = len(stripped)
                if self.remove_empties and L == 0:
                    self.n_empties += n
                else:
                    counter[stripped] += n
                    if len(stripped) != len(s):
                        self.n_stripped += n

        if self._show(VERBOSITY.INPUTS):
            print('Examples:')
            pprint([(k, v) for (k, v) in counter.items()])
            print()

        return Examples(list(counter.keys()), ilist(counter.values()))

    def _batch_extract(self):
        """
        Run a single extraction pass over the current working examples.

        This is the non-iterative core called by ``extract()``, which
        may invoke it several times, each time folding unmatched
        examples back in before retrying.

        The pipeline: coarse-classify and run-length encode each
        string; group by category sequence into variable run-length
        encodings (VRLEs); refine each fragment to the narrowest
        character class that fits; merge and align patterns on shared
        fixed anchors; convert to regex strings.

        Returns a ``ResultsSummary`` containing the intermediate
        structures (RLEs, VRLEs, refined patterns) as well as the
        final regular expressions.
        """
        examples = self.examples.strings
        freqs = self.examples.freqs
        # First, run-length encode each (distinct) example
        rles = [self._run_length_encode_coarse_classes(s) for s in examples]
        self._poss_show_items(VERBOSITY.RLE, rles, 'RLEs')
        rle_freqs = IDCounter()
        example2r_id = ilist([1]) * len(examples)  # same length as rles
        r_id2v_id = {}
        for i, rle in enumerate(rles):
            r_id = rle_freqs.add(rle, freqs[i])
            example2r_id[i] = r_id  # r_ids are the ids of rles

        # Then convert these RLEs to VRLEs (variable-run-length-encoded seqs)
        example2v_id = ilist([1]) * len(examples)  # same length as rles
        vrles, sig2rle, sig2vrle = to_vrles(rle_freqs.keys())
        vrle_freqs = IDCounter()
        refined = []
        for vrle in vrles:
            v_id = vrle_freqs.add(vrle)  # v_ids are the ids of vles
            sig = signature(vrle)
            for rle in sig2rle[sig]:
                r_id = rle_freqs.ids[rle]
                r_id2v_id[r_id] = v_id
                vrle_freqs.counter[v_id] += rle_freqs.counter[r_id]
                # This adds in the freq for each rle in the vrle
            vrle_freqs.counter[v_id] -= 1  # Take off the "extra" one we
            # initially added
            # Note, these totals include repeats.

        self._poss_show_items(VERBOSITY.VRLE, vrles, 'VRLEs')

        # For each example, record the id of the VRLE to which it belongs
        # and stash that away inside the Examples object.
        for i, r_id in enumerate(example2r_id):
            example2v_id[i] = r_id2v_id[r_id]
        self.examples.example2v_id = example2v_id

        # Refine the fragments in the VRLEs
        for vrle in vrles:
            grouped = self._refine_fragments(vrle, vrle_freqs.ids[vrle])
            refined.append(grouped)

        self.examples.vrle_freqs = vrle_freqs

        merged = self._merge_patterns(refined)
        self._poss_show_items(VERBOSITY.MERGED, merged, 'Merged VRLEs')
        if self.specialize:
            merged = self._specialize(merged)
            self._poss_show_items(
                VERBOSITY.SPECIALIZED, merged, 'Specializsed, merged VRLEs'
            )
        mergedrex = [self._vrle2re(m, tagged=self.tag) for m in merged]
        self._poss_show_items(VERBOSITY.MERGED_REX, mergedrex, 'Merged Rexes')
        mergedfrags = [self._vrle2refrags(m) for m in merged]
        self._poss_show_items(
            VERBOSITY.MERGED_FRAGS, mergedfrags, 'Merged Frags'
        )
        return ResultsSummary(
            rles,
            rle_freqs,
            vrles,
            vrle_freqs,
            merged,
            mergedrex,
            mergedfrags,
            extractor=self,
        )

    def _poss_show_items(self, mask, items, header):
        if self._show(mask):
            print(f'{header}:')
            for items in items:
                print(items)
            print()

    def _convert_rex_to_dialect(self):
        self.results.convert_to_dialect(self)

    def _specialize(self, patterns):
        """
        Check all the catpure groups in each patterns and simplify any
        that are sufficiently low frequency.
        """
        return patterns

    def _coarse_classify(self, s):
        """
        Classify each character in a string into one of the coarse categories
        """
        return ''.join(self._coarse_classify_char(c) for c in s)

    def _coarse_classify_char(self, c):
        """
        Classify character into one of the coarse categories
        """
        Cats = self.Cats
        for cat in Cats.SpecificCoarseCats:
            if re.match(cat.re_single, c):
                return cat.code
        assert re.match(Cats.Other.re_single, c)
        return Cats.Other.code

    def _run_length_encode_coarse_classes(self, s):
        """
        Return the run-length encoding of the coarse classification of s.

        If the result would exceed ``MAX_GROUPS`` fragments — which
        would produce an unwieldy regex — the whole string is treated
        as a single catch-all fragment instead.
        """
        rle = run_length_encode(self._coarse_classify(s))
        if len(rle) <= MAX_GROUPS:
            return rle
        else:
            self.n_too_many_groups += 1
            return run_length_encode(CODE.ANY * len(s))

    def _merge_patterns(self, patterns):
        """
        Merge refined VRLE patterns by aligning on shared fixed anchors.

        Applies alignment passes until no further merging is possible,
        then reassembles the pieces into a flat list of patterns.
        """
        if len(patterns) == 1:
            return patterns
        patterns = self._sort_by_length(patterns)
        level = 0
        parts = [patterns]  # Start off with each whole pattern
        # as a single part
        n_parts = len(parts)
        DO_ALIGNMENT = True
        while level < N_ALIGNMENT_LEVELS and DO_ALIGNMENT:
            parts = self._alignment_step(parts, level)
            if len(parts) == n_parts:  # no change this time; next level
                level += 1
            else:
                n_parts = len(parts)
        patterns = self._join_parts(parts)
        return patterns

    def _alignment_step(self, parts, level):
        new_parts = []
        n_parts = len(parts)
        for part in parts:
            if level == 0:
                new_parts.extend(self._merge_fixed_omnipresent_at_pos(part))
            elif level == 1:
                new_parts.extend(self._merge_fixed_only_present_at_pos(part))
            else:
                raise ValueError('Level out of range (%d)' % level)
        if self._show(VERBOSITY.ALIGNED):
            print('\nOUT:')
            print(self._aligned_parts(new_parts))
        return new_parts

    def _merge_fixed_omnipresent_at_pos(self, patterns):
        """
        Split patterns at fixed fragments that appear at the same
        position in every pattern.

        Checks positions relative to both the left and right ends.
        When a shared anchor is found the patterns are split there
        and returned as separate groups for recursive merging. If no
        such anchor exists, the patterns are returned as a single
        unmodified group.
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

        leftPos = {frag: Counter() for frag in frags}  # pos of frag from left
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
        rightFixed = get_omnipresent_at_pos(
            rightPos, nPatterns, verbose=self.verbose
        )
        if rightFixed:
            return right_parts(patterns, rightFixed)
        return [patterns]

    def _merge_fixed_only_present_at_pos(self, patterns):
        """
        Split patterns at fixed fragments that always appear at the
        same position when present, but need not appear in every pattern.

        Like ``_merge_fixed_omnipresent_at_pos``, but the anchor need
        not be universal — it just must never appear at more than one
        position across the patterns. Checks both left and
        right-relative positions.
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

        leftPos = {frag: Counter() for frag in frags}  # pos of frag from left
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
            if self.verbose:
                print('LEFT FOUND!', leftFixed)
            return left_parts(patterns, leftFixed)
        rightFixed = get_only_present_at_pos(rightPos, verbose=self.verbose)
        if rightFixed:
            if self.verbose:
                print('RIGHT FOUND!', rightFixed)
            return right_parts(patterns, rightFixed)
        return [patterns]

    def _join_parts(self, parts):
        if not parts:
            return []
        out = [[] for i in range(len(parts[0]))]
        for part in parts:
            for i, row in enumerate(part):
                if row:
                    out[i].extend(row)
        return out

    def _sort_by_length(self, patterns):
        if patterns:
            M = max(len(p) for p in patterns if p is not None) + 1
            f = lambda p: len(p) if p is not None else M
            return list(sorted(patterns, key=f))
        else:
            return []

    def _pad(self, p, q):
        if self.verbose:
            print(self._vrle2re(self._despecify(p), True))
            print(self._vrle2re(self._despecify(q), True))
            print()
        return p  # padded

    def _despecify(self, pattern):
        return list(self._despecify_frag(frag) for frag in pattern)

    def _despecify_frag(self, frag):
        r, m, M = frag[:3]
        if m == M == 1:
            return frag
        else:
            return (r, 1, None) if len(frag) == 3 else (r, 1, None, 'fixed')

    def _similarity(self, p, q):
        return 1

    def _sample(self, n):
        """
        Sample self.all_examples for potentially faster induction.
        """
        return self._sample_examples(self.all_examples, n)

    def _sample_examples(self, examples, n):
        """
        Sample examples provided for potentially faster induction.
        """
        indices = list(range(len(examples.strings)))
        sample_indices = random.sample(indices, n)
        return (
            [examples.strings[i] for i in sample_indices],
            [examples.freqs[i] for i in sample_indices],
        )

    def _sample_non_matches(self, rexes, maxN=None):
        """
        Like ``_find_non_matches``, but caps the failures returned at
        ``maxN``, sampling randomly if there are more.
        """
        failures, freqs, re_freqs = self._find_non_matches(rexes)
        if maxN is not None:
            if len(failures) > maxN:
                z = list(zip(failures, freqs))
                n = len(z)
                if n > maxN and n > self.size.do_all_exceptions:
                    sampled = random.sample(z, self.size.do_all_exceptions)
                else:
                    sampled = z
                failures = [s[0] for s in sampled]
                freqs = [s[1] for s in sampled]
        return failures, freqs, re_freqs

    def _find_non_matches(self, rexes):
        """
        Return all examples not matched by any regex in rexes.

        Returns a tuple ``(strings, freqs, re_freqs)`` where
        ``strings`` is the list of unmatched examples, ``freqs`` their
        frequencies, and ``re_freqs`` the total frequency matched by
        each regex.
        """
        examples = self.all_examples
        if not rexes:
            return examples.strings, examples.freqs, []

        strings = examples.strings
        freqs = examples.freqs
        N = len(strings)
        matched = [False] * N
        nRemaining = N
        re_freqs = [0] * len(rexes)
        if self.results:
            for j, r in enumerate(rexes):
                cr = cre(r)
                for i in range(N):
                    if not matched[i]:
                        if re.match(cr, strings[i]):
                            matched[i] = True
                            nRemaining -= 1
                            re_freqs[j] += freqs[i]
                            if nRemaining == 0:
                                return [], [], re_freqs
        indices = [i for i in range(N) if not matched[i]]
        failures = [strings[i] for i in indices]
        out_freqs = [freqs[i] for i in indices]
        return failures, out_freqs, re_freqs

    def _pattern_matches(self):
        compiled = [cre(r) for r in self.results.rex]
        results = OrderedDict()
        for x in self.examples.strings:
            for i, r in enumerate(self.results.rex):
                cr = cre(r)
                if re.match(cr, x):
                    try:
                        results[i].append(x)
                    except:
                        results[i] = [x]
                    break
            else:
                # TODO: should never happen, so should raise an exception
                print('Example "%s" did not match any pattern' % x)
        return results

    def _analyse_fragments(self, vrle, v_id):
        """
        Collect per-fragment character data across all examples matching vrle.

        Returns a zip of five parallel sequences, one entry per
        fragment position:

        - the set of characters seen in that fragment
        - the set of substrings seen in that fragment
        - the run-length encoding of fine classes, or ``False``
          if inconsistent across examples
        - the run-length encoding of literal characters, or ``False``
          if inconsistent
        - the fragment descriptor from the VRLE
        """
        examples = self.examples
        regex = cre(self._vrle2re(vrle, tagged=True))
        n_frags = len(vrle)
        frag_chars = [set([]) for i in range(n_frags)]
        frag_strings = [set([]) for i in range(n_frags)]

        frag_rlefcs = [None] * n_frags  # Start as None; end as False or VRLE
        frag_rlecs = [None] * n_frags  # Start as None; end as False or VRLE

        n_strings = [0] * n_frags
        strings = examples.strings
        v_ids = examples.example2v_id
        size = self.size
        for i, example in enumerate(strings):
            if v_ids[i] == v_id:  # Only need to use examples for this VRLE
                m = re.match(regex, example)
                assert m is not None
                f = group_map_function(m, n_frags)
                for i, frag in enumerate(vrle):
                    try:
                        g = m.group(f(i + 1))
                    except:
                        print('>>>', regex.pattern)
                        print(n_frags, i)
                        raise

                    if n_strings[i] <= size.max_strings_in_group:
                        frag_strings[i].add(g)
                        n_strings[i] = len(frag_strings[i])
                    frag_chars[i] = frag_chars[i].union(set(list(g)))
                    (frag_rlefcs[i], frag_rlecs[i]) = self._rle_fc_c(
                        g, frag, frag_rlefcs[i], frag_rlecs[i]
                    )
        if self.verbose >= 2:
            print('Fine Class VRLE:', frag_rlefcs)
            print('      Char VRLE:', frag_rlecs)
        return zip(frag_chars, frag_strings, frag_rlefcs, frag_rlecs, vrle)

    def _refine_fragments(self, vrle, v_id):
        """
        Narrow the character class for each fragment in a VRLE.

        For each fragment position, examines all matching examples to
        find the most specific category that still covers every
        character seen: a fixed literal, a single repeated character,
        a fine alphanumeric subclass (e.g. hex digits), a specific
        punctuation set, or the original coarse class as a fallback.
        """
        examples = self.examples
        ga = self._analyse_fragments(vrle, v_id)
        out = []
        Cats = self.Cats
        size = self.size
        n_groups = len(vrle)

        for group, (chars, strings, rlefc, rlec, fragment) in enumerate(ga):
            (c, m, M) = fragment
            char_str = ''.join(sorted(chars))
            fixed = False
            refined = None
            if len(strings) == 1:  # Same string for whole group
                refined = self.Cats.escape(list(strings)[0])
                m = M = 1
                fixed = True
            elif len(chars) == 1:  # Same character, possibly repeated
                refined = self.Cats.escape(list(chars)[0])
                fixed = True
            elif c == COARSEST_ALPHANUMERIC_CODE:  # Alphanumeric
                if rlec:  # Always same sequence of chars
                    if self.verbose >= 2:
                        print('SAME CHARS: %s' % rlec)
                    out.extend(plusify_vrles(rlec))
                    continue
                elif rlefc:  # Always same sequence of fine classes
                    if self.verbose >= 2:
                        print('SAME FINE CLASSES: %s' % rlefc)
                    if n_groups + len(rlefc) - 1 <= MAX_GROUPS:
                        out.extend(plusify_vrles(rlefc))
                        n_groups += len(rlefc) - 1
                        continue
                for k in Cats.IncreasinglyGeneralAlphanumerics:
                    cat = getattr(Cats, k)
                    if type(cat) == tuple:
                        print('>>>', cat)  # This cannot happen
                    code = cat.code
                    if re.match(cat.re_multiple, char_str):
                        refined = Cats.escape_code(code)
                        break  # <-- continue?
                else:
                    refined = c
            elif (
                c == CODE.PUNC and len(chars) <= size.max_punc_in_group
            ):  # Punctuation
                refined = escaped_bracket(char_str, dialect=self.Cats.dialect)
                fixed = True
            else:
                refined = c
            if fixed:
                out.append((refined, m, M, 'fixed'))
            else:
                out.append((refined, m, M))
        return out

    def _rle_fc_c(self, s, pattern, rlefc_in, rlec_in):
        """
        Update the accumulated run-length encodings of fine classes and
        literal characters for the substring s matching a coarse fragment.

        Only applies to alphanumeric (``'C'``) fragments; returns
        ``(False, False)`` for any other coarse class, or when a
        previous call has already found inconsistency.

        Args:
            s: The substring of an example that matched this fragment.
            pattern: The VRLE fragment descriptor (coarse class, min, max).
            rlefc_in: Accumulated fine-class VRLE so far, ``None`` if
                this is the first example, or ``False`` if already
                inconsistent.
            rlec_in: Accumulated character VRLE, with the same
                sentinel values as ``rlefc_in``.

        Returns:
            A pair ``(rlefc, rlec)``, each a (possibly widened) VRLE
            if s is consistent with prior examples, or ``False`` if s
            breaks consistency.
        """
        if pattern[0] != COARSEST_ALPHANUMERIC_CODE or (
            rlefc_in == False and rlec_in == False
        ):
            return (False, False)  # Indicates, neither applies
            # Either 'cos not coarse class C
            # Or because previously found wanting...

        rlefc = []  # run-length encoded list of fine classes
        rlec = []  # run-length encoded list of characters
        last_fc = None  # last fine class
        last_c = None  # last character
        nfc = 0
        nc = 0

        for c in s:
            fc = self._fine_class(c)
            if fc == last_fc:
                nfc += 1
            else:
                if last_fc:
                    rlefc.append((last_fc, nfc))
                last_fc = fc
                nfc = 1
            if c == last_c:
                nc += 1
            else:
                if last_c:
                    rlec.append((last_c, nc))
                last_c = c
                nc = 1
        if last_c:  # i.e. there were any; probably always the case
            rlefc.append((last_fc, nfc))
            rlec.append((last_c, nc))

        v = self.variableLengthFrags
        return (
            expand_or_falsify_vrle(rlefc, rlefc_in, variableLength=v),
            expand_or_falsify_vrle(
                rlec, rlec_in, fixed=True, variableLength=v
            ),
        )

    def _fine_class(self, c):
        """
        Map a character in coarse class 'C' (AlphaNumeric) to a fine class.
        """
        cats = self.Cats
        if c.isdigit():
            return cats.Digit.code
        elif 'a' <= c <= 'z':
            return cats.letter.code
        elif 'A' <= c <= 'Z':
            return cats.LETTER.code
        elif c in cats.extra_letters or not UNICHRS:
            return cats.LETTER_.code
        else:
            return cats.ULetter_.code

    def _fragment2re(self, fragment, tagged=False, as_re=True, output=False):
        """
        Convert a single VRLE fragment to a regex string.

        Args:
            fragment: A tuple ``(code, min, max)`` or
                ``(code, min, max, 'fixed')`` for a fixed literal.
            tagged (bool): If ``True``, wrap variable fragments in
                a capturing group.
            as_re (bool): If ``False``, return the raw category code
                rather than its regex equivalent.
            output (bool): If ``True``, use the output-dialect
                character classes rather than the internal ones.
        """
        (c, m, M) = fragment[:3]
        fixed = len(fragment) > 3
        Cats = self.OutCats if (output and self.dialect) else self.Cats
        regex = c if (fixed or not as_re) else Cats[c].re_string
        if (m is None or m == 0) and M is None:
            part = regex + '*'
        elif M is None:
            part = regex + '+'
        elif m == M == 1:
            part = regex
        elif m == M == 2 and len(regex) == 1:
            part = regex + regex
        elif m == M:
            part = regex + ('{%d}' % m)
        else:
            part = regex + ('?' if m == 0 and M == 1 else ('{%d,%s}' % (m, M)))
        return capture_group(part) if (tagged and not fixed) else part

    def _vrle2re(self, vrles, tagged=False, as_re=True, output=False):
        """
        Convert a VRLE pattern to a regular expression string.

        Concatenates the regex for each fragment, adds start/end
        anchors, and if any examples were stripped, wraps the result
        in optional-whitespace anchors.

        Args:
            vrles: A sequence of VRLE fragment tuples.
            tagged (bool): If ``True``, wrap variable fragments in
                capturing groups.
            as_re (bool): If ``False``, return raw category codes
                rather than their regex equivalents.
            output (bool): If ``True``, use the output-dialect
                character classes rather than the internal ones.
        """
        parts = [
            self._fragment2re(frag, tagged=tagged, as_re=as_re, output=output)
            for frag in vrles
        ]
        if self.n_stripped > 0:
            Cats = self.OutCats if output and self.dialect else self.Cats
            ws = [r'%s*' % Cats.Whitespace.re_string]
            parts = ws + parts + ws
        return poss_term_re(''.join(parts))

    def _vrle2refrags(self, vrles, output=False):
        """
        Convert variable run-length-encoded code string to regular expression
        and list of fragments
        """
        if self.n_stripped > 0:
            ws = r'\s*'
            return (
                [Fragment(ws, True)]
                + [
                    Fragment(
                        self._fragment2re(
                            frag, tagged=False, as_re=True, output=output
                        ),
                        len(frag) < 4,
                    )
                    for frag in vrles
                ]
                + [Fragment(ws, True)]
            )

        else:
            return [
                Fragment(
                    self._fragment2re(
                        frag, tagged=False, as_re=True, output=output
                    ),
                    len(frag) < 4,
                )
                for frag in vrles
            ]

    def _rle2re(self, rles, tagged=False, as_re=True):
        """
        Convert run-length-encoded code string to regular expression
        """
        Cats = self.Cats
        parts = []
        for c, freq in rles:
            desc = Cats[c].re_string if as_re else c
            part = desc + ('{%d}' % freq if freq > 1 else '')
            parts.append(('(%s)' % part) if tagged else part)
        return poss_term_re(''.join(parts))

    def _humanish_frag(self, frag):
        as_re = self._fragment2re(frag)
        return as_re.replace('\\', '').replace(' ', '_')

    def _aligned_parts(self, parts):
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
                        frag = self._humanish_frag(row[c])
                        lines[r].append(frag)
                        w = max(w, len(frag))
                    else:
                        lines[r].append('')
                seps.append(' ')
                widths.append(w)
            if stats.max_length:
                seps[-1] = '|'
        header = '|' + ''.join(
            (ndigits(w, i) + seps[i - 1]) for i, w in enumerate(widths, 1)
        )
        fmts = ['%%%ds' % w for w in widths]
        body = '\n '.join(
            ' '.join(fmt % frag for (fmt, frag) in zip(fmts, line))
            for line in lines
        )
        return '\n'.join([header, ' ' + body])

    def coverage(self, dedup=False):
        """
        Return match counts for each extracted regular expression.

        Returns a list of counts in the same order as
        ``self.results.rex``. Each count is the number of input
        strings matched by that pattern.

        Args:
            dedup (bool): If ``True``, count only distinct strings,
                ignoring duplicate frequencies.

        Returns:
            A list of match counts, one per regular expression in
            ``self.results.rex``, in the same order.
        """
        return rex_coverage(self.results.rex, self.examples, dedup)

    def incremental_coverage(self, dedup=False, debug=False):
        """
        Return regular expressions sorted by incremental coverage.

        Returns an ordered dictionary mapping each regular expression
        to the number of new (previously unmatched) examples it
        accounts for, sorted from most to fewest, with ties broken by
        pattern sort order.

        Args:
            dedup (bool): If ``True``, ignore string frequencies when
                counting and sorting.
            debug (bool): If ``True``, print debugging information
                during computation.

        Returns:
            An ``OrderedDict`` mapping each regular expression to its
            new-match count, in decreasing order of incremental
            coverage.
        """
        return rex_incremental_coverage(
            self.results.rex, self.examples, dedup, debug=debug
        )

    def full_incremental_coverage(self, dedup=False, debug=False):
        """
        Return regular expressions sorted by incremental coverage,
        with full per-pattern statistics.

        Like ``incremental_coverage()``, but the dictionary values are
        ``Coverage`` objects rather than plain counts, giving both
        cumulative and incremental match statistics for each pattern.

        Args:
            dedup (bool): If ``True``, use deduplicated incremental
                coverage as the sort key rather than raw coverage.
            debug (bool): If ``True``, print debugging information
                during computation.

        Returns:
            An ``OrderedDict`` mapping each regular expression to a
            ``Coverage`` object, in decreasing order of incremental
            coverage. See ``Coverage`` for the available attributes.
        """
        return rex_full_incremental_coverage(
            self.results.rex, self.examples, sort_on_deduped=dedup, debug=debug
        )

    def n_examples(self, dedup=False):
        """
        Return the total number of examples used for extraction.

        Args:
            dedup (bool): If ``True``, return the number of distinct
                examples; otherwise return the total count including
                duplicates. In both cases examples are post-strip.

        Returns:
            The number of examples as an integer.
        """
        if dedup:
            return self.examples.n_uniqs
        else:
            return self.examples.n_strings

    def __str__(self):
        return str(self.results or 'No results (yet)')

    def _build_tree(self, vrles):
        fulls = vrles[:]
        tree = self._build_tree_inner(vrles, fulls)
        self._add_freqs_to_tree(tree)
        return tree

    def _add_freqs_to_tree(self, tree):
        freqs = self.examples.vrle_freqs
        for key, values in tree.items():
            for i, v in enumerate(values):
                if type(v) is tuple:
                    values[i] = (v[1], freqs[v[1]])
                else:
                    self._add_freqs_to_tree(v)

    def _build_tree_inner(self, vrles, fulls=None):
        """
        Turn the VRLEs into a tree based on the different initial fragments.
        """
        tree = Tree()
        for partial, full in zip(vrles, fulls):
            if partial:
                key, entry = self._vrle_entry(partial, full)
                tree[key].append(entry)
        for key, entries in tree.items():
            v = self._build_tree_inner(
                [e[0] for e in entries if e[0]],
                [e[1] for e in entries if e[0]],
            )
            if v is not None:
                tree[key] = [v]
                for e in entries:
                    if e[0] is None:
                        tree[key] = [e] + [v]
            else:
                tree[key] = entries
        return tree if len(tree) > 0 else None

    def _vrle_entry(self, partial, full):
        return (
            self._vrle_key(partial[0]),
            (partial[1:] if len(partial) > 1 else None, full),
        )

    def _vrle_key(self, vrle):
        (c, m, M) = vrle[:3]
        fixed = len(vrle) == 4
        if fixed:
            return vrle
        else:
            return c

    def _find_frag_sep_frag_repeated(self, tree, existing=None, results=None):
        r"""
        This specifically looks for patterns in the tree constructed
        by self._build_tree of the general form

            A
            ABA
            ABABA

        etc., where A and B are both fragments.
        A common example is that A is recognizably a pattern and B is
        recognizably a separator. So, for example:

        HM
        MH-RT
        QY-TR-BF
        QK-YT-IU-QP

        all fit

        [A-Z]{2}(\-[A-Z])*

        which, as fragments, would be A = (C, 2, 2) and B = ('.', 1, 1).

        The tree is currently not recording or taking account of
        frequency in the fragments. We might want to do that.
        Or we might leave that as a job for whatever is going to
        consolidate the different branches of the tree that match
        the repeating patterns returned.
        """
        results = results or []
        existing = existing or []
        for k, v in tree.items():
            for j, item in enumerate(v):
                if item is None:  # leaf
                    L = len(existing)
                    if L >= 3 and L % 2 == 1:
                        if all(
                            existing[i] == existing[i % 2] for i in range(3, L)
                        ):
                            results.append(
                                [existing[0], existing[1], existing[0]]
                            )
                            v[j] = results
                else:
                    newpat = existing + [k]
                    results, _ = self._find_frag_sep_frag_repeated(
                        item, newpat, results
                    )
        return results, tree


def example_check_function(rexes, strings, maxN=None):
    """
    **CHECK FUNCTIONS**
    This is an example check function

    A check function takes a list of regular expressions (as strings)
    and optionally, a maximum number of (different) strings to return.

    It should return two things:

      - An Examples object (importing that class from rexpy.py)
        containing strings that don't match any of the regular expressions
        in the list provided. (If the list is empty, all strings are candidates
        to be returned.)

      - a list of how many strings matched each regular expression
        provided (in the same order).

    If maxN is None, it should return all strings that fail to match;
    if it is a number, that is the maximum number of (distinct) failures
    to return. The function *is* expected to return all failures, however,
    if there are fewer than maxN failures (i.e., it's not OK if maxN
    is 20 to return just 1 failiing string if actually 5 different
    strings fail.)

    Examples: The examples object is initialized with a list of (distinct)
    failing strings, and optionally a corresponding list of their frequencies.
    If no frequencies are provided, all frequencies will be set to 1
    when the Examples object is initialized.

    The regular expression match frequencies are used to eliminate
    low-frequency or low-ranked regular expressions. It is not essential
    that the values cover all candidate strings; it is enough to give
    frequencies for those strings tested before maxN failures are generated.

    (Normally, the regular expressions provided will be exclusive, i.e.
    at most one will match, so it's also fine only to test a string
    against regular expressions until a match is found...you don't
    need to test against other patterns in case the string also matches
    more than one.)
    """
    # In this example function, we are assuming each string in strings
    # is distinct.
    failures = []
    re_freqs = [0] * len(rexes)
    if rexes:
        patterns = [re.compile(r) for r in rexes]  # compile for efficiency
        for u in strings:
            for i, r in enumerate(patterns):
                if re.match(r, u):
                    re_freqs[i] += 1  # record the fact that this rex matched
                    break  # don't try later patterns
            else:  # Record strings that don't match any rex
                failures.append(u)
    else:
        failures = strings  # If there are no rexes, all strings fail
    if maxN is not None and len(failures) > maxN:
        failures = random.sample(failures, maxN)
    return Examples(failures), re_freqs


def rex_coverage(patterns, examples, dedup=False):
    """
    Given a list of regular expressions and a dictionary of examples
    and their frequencies, this counts the number of times each pattern
    matches a an example.

    If ``dedup`` is set to ``True``, the frequencies are ignored, so that only
    the number of keys is returned.
    """
    results = []
    for p in patterns:
        p = '%s%s%s' % (
            '' if p.startswith('^') else '^',
            p,
            '' if p.endswith('$') else '$',
        )
        r = re.compile(p, RE_FLAGS)
        if dedup:
            strings = examples.strings
            results.append(sum(1 if re.match(r, k) else 0 for k in strings))
        else:
            strings = examples.strings
            freqs = examples.freqs
            results.append(
                sum(
                    n if re.match(r, k) else 0
                    for (k, n) in zip(strings, freqs)
                )
            )
    return results


def rex_full_incremental_coverage(
    patterns, examples, sort_on_deduped=False, debug=False
):
    """
    Returns an ordered dictionary containing, keyed on terminated
    regular expressions, from patterns, sorted in decreasing order
    of incremental coverage, i.e. with the pattern matching
    the most first, followed by the one matching the most remaining
    examples etc.

    If ``dedup`` is set to ``True``, the ordering ignores duplicate examples;
    otherise, duplicates help determine the sort order.

    Each entry in the dictionary returned is a ``Coverage`` object
    with the following attributes:

        ``n``:
            number of examples matched including duplicatesb

        ``n_uniq``:
            number of examples matched, excluding duplicates

        ``incr``:
            number of previously unmatched examples matched,
            including duplicates

        ``incr_uniq``:
            number of previously unmatched examples matched,
            excluding duplicates
    """
    patterns, indexes = terminate_patterns_and_sort(patterns)
    matrix, deduped = coverage_matrices(patterns, examples)
    return matrices2incremental_coverage(
        patterns,
        matrix,
        deduped,
        indexes,
        examples,
        sort_on_deduped=sort_on_deduped,
    )


def terminate_patterns_and_sort(patterns):
    """
    Given a list of regular expressions, this terminates any that are
    not and returns them in sorted order.
    Also returns a list of the original indexes of the results.
    """
    results = [
        '%s%s%s'
        % ('' if p.startswith('^') else '^', p, '' if p.endswith('$') else '$')
        for p in patterns
    ]
    z = list(zip(results, range(len(results))))
    z.sort()  # Sort to fix the order of tiebreaks
    return [r[0] for r in z], [r[1] for r in z]


def rex_incremental_coverage(
    patterns, examples, sort_on_deduped=False, debug=False
):
    """
    Given a list of regular expressions and a dictionary of examples
    and their frequencies, this computes their incremental coverage,
    i.e. it produces an ordered dictionary, sorted from the "most useful"
    patterns (the one that matches the most examples) to the least useful.
    Usefulness is defined as "matching the most previously unmatched patterns".
    The dictionary entries are the number of (new) matches for the pattern.

    If ``dedup`` is set to ``True``, the frequencies are ignored when computing
    match rate; if set to false, patterns get credit for the nmultiplicity
    of examples they match.

    Ties are broken by lexical order of the (terminated) patterns.

    For example, given patterns p1, p2, and p3, and examples e1, e2 and e3,
    with a match profile as follows (where the numbers are multiplicities)

    ======= ====    ====    ====
    example p1      p2      p3
    ======= ====    ====    ====
    e1       2       2       0
    e2       0       3       3
    e3       1       0       0
    e4       0       0       4
    e5       1       0       1
    TOTAL    4       4       8
    ======= ====    ====    ====

    If ``dedup`` is ``False`` this would produce::

        OrderedDict(
            (p3, 8),
            (p1, 3),
            (p2, 0)
        )

    because:

     - p3 matches the most, with 8
     - Of the strings unmatched by p3, p1 accounts for 3 (e1 x 2 and e3 x 1)
       whereas p2 accounts for no new strings.

    With ``dedup`` set to ``True``, the matrix transforms to

    ======= ====    ====    ====
    example p1      p2      p3
    ======= ====    ====    ====
    e1       1       1       0
    e2       0       1       1
    e3       1       0       0
    e4       0       0       1
    e5       1       0       1
    TOTAL    3       2       3
    ======= ====    ====    ====

    So p1 and p3 are tied.

    If we assume the p1 sorts before p3, the result would then be::

        OrderedDict(
            (p1, 3),
            (p3, 2),
            (p2, 0)
        )

    """
    results = rex_full_incremental_coverage(
        patterns, examples, sort_on_deduped=sort_on_deduped, debug=False
    )
    if sort_on_deduped:
        return OrderedDict((k, v.incr_uniq) for (k, v) in results.items())
    else:
        return OrderedDict((k, v.incr) for (k, v) in results.items())


def coverage_matrices(patterns, examples):
    # Compute the 2 coverage matrices:
    #   matrix:  1 row per example, with a count of number of matches
    #   deduped: 1 row per example, with a boolean where it matches

    matrix = []
    deduped = []  # deduped version of same
    rexes = [re.compile(p, RE_FLAGS) for p in patterns]
    strings = examples.strings
    freqs = examples.freqs
    for x, n in zip(strings, freqs):
        row = [n if re.match(r, x) else 0 for r in rexes]
        matrix.append(row)
        deduped.append([1 if r else 0 for r in row])
    return matrix, deduped


def matrices2incremental_coverage(
    patterns, matrix, deduped, indexes, examples, sort_on_deduped=False
):
    """
    Find patterns, in (descending) order of # of matches, and pull out freqs.

    Then set overlapping matches to zero and repeat.

    Returns ordered dict, sorted by incremental match rate,
    with number of (previously unaccounted for) strings matched.
    """
    results = OrderedDict()
    sort_matrix = deduped if sort_on_deduped else matrix
    np = len(patterns)
    zeros = [0] * np
    strings = examples.strings
    pattern_freqs = [
        sum(matrix[i][r] for i, x in enumerate(strings)) for r in range(np)
    ]
    pattern_uniqs = [
        sum(deduped[i][r] for i, x in enumerate(strings)) for r in range(np)
    ]
    some_left = True
    while some_left and len(results) < np:
        totals = [sum(row[i] for row in matrix) for i in range(np)]
        uniq_totals = [sum(row[i] for row in deduped) for i in range(np)]
        M, uM = max(totals), max(uniq_totals)
        if sort_on_deduped:
            sort_totals = uniq_totals
            target = uM
        else:
            sort_totals = totals
            target = M

        if target > 0:
            # find pattern with frequency of target
            p = 0  # index of pattern
            while sort_totals[p] < target:
                p += 1
            rex = patterns[p]

            in_results = rex in results
            if not in_results:
                for i in range(examples.n_uniqs):
                    if matrix[i][p]:
                        matrix[i] = zeros
                        deduped[i] = zeros
                        zeroed = True
                results[rex] = Coverage(
                    n=pattern_freqs[p],
                    n_uniq=pattern_uniqs[p],
                    incr=totals[p],
                    incr_uniq=uniq_totals[p],
                    index=indexes[p],
                )
        else:
            some_left = False

    if some_left and len(results) < np:
        for p in range(np):
            rex = patterns[p]
            if rex not in results:
                results[rex] = Coverage(
                    n=pattern_freqs[p],
                    n_uniq=pattern_uniqs[p],
                    incr=0,
                    incr_uniq=0,
                    index=indexes[p],
                )
    return results


def run_length_encode(s):
    """
    Return run-length-encoding of string s, e.g.::

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

    For example, given inputs of::

            (('C', 2),)
            (('C', 3),)
        and (('C', 2), ('.', 1))

    this would return::

            (('C', 2, 3),)
        and (('C', 2, 2), ('.', 1, 1))

    """
    rle_by_sig = Tree()
    vrles = []
    for rle in rles:
        rle_by_sig[signature(rle)].append(rle)
    for sig, rles in rle_by_sig.items():
        nCats = len(sig)
        cats = list(sig)
        mins = [min(r[i][1] for r in rles) for i in range(nCats)]
        maxes = [max(r[i][1] for r in rles) for i in range(nCats)]
        vrles.append(
            tuple([(cat, m, M) for (cat, m, M) in zip(cats, mins, maxes)])
        )

    if MAX_VRLE_RANGE is not None:
        vrles2 = [
            tuple(
                ((cat, m, M) if (M - m) <= MAX_VRLE_RANGE else (cat, 1, None))
                for (cat, m, M) in pattern
            )
            for pattern in vrles
        ]
        vrles = list(set(vrles2))
        vrles.sort(key=none_to_m1)
    vrle_by_sig = {signature(vrle): vrle for vrle in vrles}
    return vrles, rle_by_sig, vrle_by_sig


def none_to_m1(vrle):
    return tuple(tuple((-1 if t is None else t) for t in tup) for tup in vrle)


def ndigits(n, d):
    digit = chr((d + ord('0')) if d < 10 else (ord('A') + d - 10))
    return digit * n


def plusify_vrle(vrle):
    cat, m, M = vrle[:3]
    if M is None:
        return vrle
    fixed = vrle[3] if len(vrle) > 3 else None
    if (M - m) <= MAX_VRLE_RANGE:
        return vrle
    elif fixed:
        return (cat, m, None, fixed)
    else:
        return (cat, m, None)


def plusify_vrles(vrles):
    return [plusify_vrle(v) for v in vrles]


class IDCounter(object):
    """
    Rather Like a counter, but also assigns a numeric ID (from 1) to each key
    and actually builds the counter on that.

    Use .add to increment an existing key's count, or to initialize it to
    (by default) 1.

    Get the key's ID with .ids[key] or .keys.get(key).
    """

    def __init__(self):
        self.counter = Counter()
        self.ids = OrderedDict()
        self.n = 0

    def __getitem__(self, key):
        """Gets the count for the key"""
        id_ = self.ids.get(key)
        return self.counter[id_] if id_ else 0

    getitem = __getitem__

    def add(self, key, freq=1):
        """
        Adds the given key, counting it and ensuring it has an id.

        Returns the id.
        """
        id_ = self.ids.get(key, 0)
        if id_ == 0:
            self.n += 1
            id_ = self.n
            self.ids[key] = id_
        self.counter[id_] += freq
        return id_

    def keys(self):
        return self.ids.keys()

    def items(self):
        return self.ids.items()

    def __iter__(self):
        return self.ids.__iter__()

    def __iterkeys__(self):
        return self.ids.__iterkeys__()

    def __len__(self):
        return self.ids.__len__()


class ResultsSummary(object):
    def __init__(
        self,
        rles,
        rle_freqs,
        vrles,
        vrle_freqs,
        refined_vrles,
        rex,
        refrags,
        extractor=None,
    ):
        self.rles = rles
        self.rle_freqs = rle_freqs
        self.vrles = vrles
        self.vrle_freqs = vrle_freqs
        self.refined_vrles = refined_vrles
        self.rex = rex
        self.refrags = refrags
        self.extractor = extractor

    def to_string(
        self,
        rles=False,
        rle_freqs=False,
        vrles=False,
        vrle_freqs=False,
        refined_vrles=False,
        rex=False,
        fmt='code',
    ):
        assert fmt in ('code', 're', 'raw')
        as_re = fmt == 're'
        short = fmt in ('re', 'code')
        allFalse = not any(
            (rles, rle_freqs, vrles, vrle_freqs, refined_vrles, rex)
        )
        out = []
        if rles or allFalse:
            out.append('Run-length encoded patterns (rles):')
            for i, rle in enumerate(self.rles, 1):
                out.append(
                    '%2d: %s'
                    % (i, self.to_re(rle, as_re=as_re) if short else str(rle))
                )
            out.append('')

        if rle_freqs or allFalse:
            out.append('Run-length encoded pattern freqencies (rle_freqs):')
            for i, (rle, freq) in enumerate(self.rle_freqs.items(), 1):
                out.append(
                    '%2d: %s: %d'
                    % (
                        i,
                        self.to_re(rle, as_re=as_re) if short else str(rle),
                        freq,
                    )
                )
            out.append('')

        if vrles or allFalse:
            out.append('Variable run-length encoded patterns (vrles):')
            for i, vrle in enumerate(self.vrle_freqs, 1):
                out.append(
                    '%2d: %s'
                    % (
                        i,
                        self.to_re(vrle, as_re=as_re) if short else str(vrle),
                    )
                )
            out.append('')

        if vrle_freqs or allFalse:
            out.append(
                'Variable run-length encoded pattern freqencies (vrle_freqs):'
            )
            for i, (vrle, freq) in enumerate(self.vrle_freqs.items(), 1):
                out.append(
                    '%2d: %s: %d'
                    % (
                        i,
                        self.to_re(vrle, as_re=as_re) if short else str(vrle),
                        freq,
                    )
                )
            out.append('')

        if refined_vrles or allFalse:
            out.append(
                'Refined variable run-length encoded patterns (refined_vrles):'
            )
            for i, p in enumerate(self.refined_vrles, 1):
                out.append(
                    '%2d: %s'
                    % (i, self.to_re(p, as_re=as_re) if short else str(p))
                )
            out.append('')

        if rex or allFalse:
            out.append('Refined variable run-length encoded patterns (rex):')
            for i, r in enumerate(self.rex, 1):
                out.append('%2d: %s' % (i, r))
            out.append('')
        return '\n'.join(out)

    def to_re(self, patterns, grouped=False, as_re=True):
        f = (
            self.extractor.rle2re
            if not patterns or len(patterns[0]) == 2
            else self.extractor.vrle2re
        )
        return f(patterns, tagged=grouped, as_re=as_re)

    def remove(self, indexes, add_dot_star=False):
        """
        Given a set of indexes, remove patterns with those indexes.

        If add_dot_star is set to True, a '.*' wildcard pattern will
        also be added. This is off, by default, since adding '.*'
        is unhelpful when discovering constraints.
        """
        if not indexes:
            return

        x = self.extractor
        remaining = [i for i in range(len(self.rex)) if not i in indexes]
        for name in ('refined_vrles', 'rex', 'refrags'):
            d = self.__dict__[name]
            self.__dict__[name] = [d[i] for i in remaining]
        if add_dot_star:
            dot_star = ((x.Cats.Any.code, None, None),)
            self.refrags.append([Fragment('.*', True)])
            self.rex.append(x._vrle2re(dot_star, tagged=x.tag))

    def convert_to_dialect(self, x):
        if not x.dialect:
            return  # No dialect set, so nothing to do
        self.rex = [
            x._vrle2re(m, tagged=x.tag, output=True) for m in self.refined_vrles
        ]

        self.refrags = [
            x._vrle2refrags(m, output=True) for m in self.refined_vrles
        ]

    def __str__(self):
        return self.to_string()


class PRNGState:
    """
    Seeds the Python PRNG and after captures its state.

    restore() cam be used to set them back to the captured state.
    """

    def __init__(self, n):
        if n is not None:
            self.saved = random.getstate()
            random.seed(n)

    def restore(self):
        if hasattr(self, 'saved'):
            random.setstate(self.saved)


def combine_patterns(patterns):
    """
    Combine a list of anchored regex patterns into a single alternation.

    Converts ``['^R1$', '^R2$', ...]`` to ``['^(R1|R2|...)$']``.
    Returns the list unchanged if it has zero or one element.
    """
    if len(patterns) <= 1:
        return patterns
    stripped = [
        p[1:-1] if p.startswith('^') and p.endswith('$') else p
        for p in patterns
    ]
    return ['^(' + '|'.join(stripped) + ')$']


def extract(
    examples,
    tag=False,
    encoding=None,
    as_object=False,
    extra_letters=None,
    full_escape=False,
    remove_empties=False,
    strip=False,
    variableLengthFrags=VARIABLE_LENGTH_FRAGS,
    max_patterns=MAX_PATTERNS,
    min_diff_strings_per_pattern=MIN_DIFF_STRINGS_PER_PATTERN,
    min_strings_per_pattern=MIN_STRINGS_PER_PATTERN,
    size=None,
    seed=None,
    dialect=DEFAULT_DIALECT,
    verbose=DEFAULT_VERBOSITY,
    single=None,
):
    """
    Extract regular expression(s) from examples and return them.

    Normally examples should be unicode (i.e. ``str`` in Python 3).
    Byte strings can be passed provided ``encoding`` is specified;
    results are always unicode strings.

    Args:
        examples: The input strings to analyse. May be a list of
            strings, an integer-valued string-keyed dictionary (or
            ``Counter``) where values are string frequencies, or a
            callable conforming to the ``example_check_function``
            protocol.
        tag (bool): If ``True``, return tagged (capturing-group)
            regular expressions.
        encoding (str): Encoding to use when decoding byte-string
            examples. ``None`` (the default) means examples are
            already unicode.
        as_object (bool): If ``True``, return the ``Extractor``
            object rather than the list of regular expressions.
            The expressions are then available as
            ``result.results.rex``.
        extra_letters (str): Additional characters to treat as word
            letters when building character classes.
        full_escape (bool): If ``True``, escape all special regex
            characters, not just those strictly necessary.
        remove_empties (bool): If ``True``, discard empty strings
            from the examples before extraction.
        strip (bool): If ``True``, strip leading and trailing
            whitespace from each example before extraction.
        variableLengthFrags (bool): If ``True``, allow fragments of
            variable length within patterns.
        max_patterns (int): Maximum number of patterns to produce.
            ``None`` means no limit.
        min_diff_strings_per_pattern (int): Minimum distinct strings
            per pattern. Currently ignored.
        min_strings_per_pattern (int): Minimum total strings
            (counting duplicates) for a pattern to be retained.
        size: Controls sampling. Pass a ``Size`` instance, ``None``
            (the default) to use built-in defaults, or ``False``/``0``
            to disable sampling.
        seed (int): Random seed for reproducibility. ``None`` means
            non-deterministic.
        dialect (str): The kind of regular expression to emit.
            One of ``'portable'`` (the default), ``'grep'``,
            ``'java'``, ``'perl'``, or ``'posix'``.
        verbose (int): Verbosity level. ``0`` is silent, ``1`` prints
            progress information, ``2`` prints maximum detail.
        single (bool): If ``True``, combine all extracted patterns into
            a single regex using alternation: ``^(R1|R2|...)$``.
            ``None`` (the default) leaves the list unchanged.

    Returns:
        A list of regular expressions as unicode strings, or the
        ``Extractor`` object if ``as_object=True``.
    """
    if encoding and not callable(examples):
        if isinstance(examples, dict):
            examples = {x.decode(encoding): n for (x, n) in examples.items()}
        else:
            examples = [x.decode(encoding) for x in examples]
    r = Extractor(
        examples,
        tag=tag,
        extra_letters=extra_letters,
        full_escape=full_escape,
        remove_empties=remove_empties,
        strip=strip,
        variableLengthFrags=variableLengthFrags,
        max_patterns=max_patterns,
        min_diff_strings_per_pattern=min_diff_strings_per_pattern,
        min_strings_per_pattern=min_strings_per_pattern,
        size=size,
        seed=seed,
        dialect=dialect,
        verbose=verbose,
        single=single,
    )
    return r if as_object else r.results.rex if r.results else []


def dfextract(cols, seed=None, single=None):
    """
    Extract regular expression(s) from one or more DataFrame columns.

    All columns provided should be string columns, possibly containing
    null values, which are ignored. Works with both Pandas and Polars
    Series.

    Example::

        import numpy as np
        import pandas as pd
        from tdda.rexpy import dfextract

        df = pd.DataFrame({'a3': ["one", "two", np.nan],
                           'a45': ['three', 'four', 'five']})

        re3 = dfextract(df['a3'])
        re45 = dfextract(df['a45'])
        re345 = dfextract([df['a3'], df['a45']])

    This should result in::

        re3   = ['^[a-z]{3}$']
        re45  = ['^[a-z]{4,5}$']
        re345 = ['^[a-z]{3,5}$']

    Args:
        cols: A Pandas or Polars ``Series``, or list of ``Series`` objects.
        seed (int): Random seed for reproducibility. ``None`` (the
            default) means non-deterministic.
        single (bool): If ``True``, combine all extracted patterns into
            a single regex using alternation: ``^(R1|R2|...)$``.
            ``None`` (the default) leaves the list unchanged.

    Returns:
        A list of regular expressions as unicode strings.
    """
    if type(cols) not in (list, tuple):
        cols = [cols]
    strings = []
    for c in cols:
        if is_polars_series(c):
            strings.extend(c.drop_nulls().unique().to_list())
        else:
            strings.extend(list(c.dropna().unique()))
    try:
        return extract(strings, seed=seed, single=single)
    except:
        if not all(type(s) == str for s in strings):
            raise ValueError('Non-null, non-string values found in input.')
        else:
            raise


# TODO: add alias once refactoring complete
# pdextract = dfextract


def get_omnipresent_at_pos(fragFreqCounters, n, **kwargs):
    """
    Find patterns in ``fragFreqCounters`` for which the frequency is ``n``.

    fragFreqCounters is a dictionary (usually keyed on 'fragments')
    of whose values are dictionaries mapping positions to frequencies.

    For example::

        {
            ('a', 1, 1, 'fixed'): {1: 7, -1: 7, 3: 4},
            ('b', 1, 1, 'fixed'): {2: 6, 3: 4},
        }

    This indicates that the pattern ``('a', 1, 1, 'fixed')`` has frequency
    7 at positions 1 and -1, and frequency 4 at position 3, while
    pattern ``('b', 1, 1, 'fixed')`` has frequency 6 at position 2 and
    4 at position 3.

    With n set to 7, this returns::

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

    ``fragFreqCounters`` is a dictionary (usually keyed on ``fragments``)
    of whose values are dictionaries mapping positions to frequencies.

    For example::

        {
            ('a', 1, 1, 'fixed'): {1: 7, -1: 7, 3: 4},
            ('b', 1, 1, 'fixed'): {2: 6},
        }

    This indicates that the
      - pattern ``('a', 1, 1, 'fixed')`` has frequency 7 at positions 1 and -1,
        and frequency 4 at position 3;
      - pattern ``('b', 1, 1, 'fixed')`` has frequency 6 at position 2 (only)

    So this would return::

        [
            (('b', 1, 1, 'fixed'), 2)
        ]

    (sorted on ``pos``; each ``pos`` really should occur at most once.)
    """
    out = []
    for frag, fragFreqs in fragFreqCounters.items():
        if len(fragFreqs) == 1:
            pos = fragFreqs.keys()[0]  # the only position
            out.append((frag, pos))
    out.sort(key=lambda x: x[1])
    return out


def left_parts(patterns, fixed):
    """
    patterns is a list of patterns each consisting of a list of frags.

    fixed is a list of ``(fragment, position)`` pairs, sorted on position,
    specifying points at which to split the patterns.

    This function returns a list of lists of pattern fragments,
    split at each fixed position.
    """
    if not fixed:
        return [patterns]
    lastPos = -1
    out = []
    lstats = length_stats(patterns)
    for frag, pos in fixed:
        if pos > 0:  # Nothing to the left if it's position 0
            out.append([p[lastPos + 1 : pos] for p in patterns])
        #        out.append([p[pos:pos + 1] for p in patterns])  # the fixed bit
        out.append([[p[pos]] for p in patterns])  # the fixed bit
        lastPos = pos
    if lastPos < lstats.max_length - 1:  # the end, if there's anything left
        out.append([p[lastPos + 1 :] for p in patterns])
    return out


def right_parts(patterns, fixed):
    """
    patterns is a list of patterns each consisting of a list of frags.

    fixed is a list of ``(fragment, pos)`` pairs where position specifies
    the position from the right, i.e a position that can be indexed as
    ``-position``.

    Fixed should be sorted, increasing on position, i.e.
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
    for frag, pos in fixed:
        if pos > 1:  # Nothing the right if it's position -1
            out.append([p[-pos + 1 : -lastPos] for p in patterns])
        out.append([[p[-pos]] for p in patterns])  # the fixed bit
        lastPos = pos
    if lastPos < lstats.max_length:  # the start, if there's anything left
        out.append([p[:-lastPos] for p in patterns])
    out.reverse()  # We built it up from the right; so we must reverse it
    return out


def length_stats(patterns):
    """
    Return length statistics for a list of patterns.

    Returns a named tuple with fields ``all_same_length`` (bool:
    whether all patterns have the same number of fragments) and
    ``max_length`` (int: the number of fragments in the longest
    pattern).
    """
    lengths = [len(p) for p in patterns]
    L0 = lengths[0] if lengths else 0
    LS = namedtuple('lengthstats', 'all_same_length max_length')
    return LS(all(L == L0 for L in lengths), max(lengths) if lengths else 0)


def get_nCalls():
    global nCalls
    return nCalls


def rexpy_streams(
    in_path=None, out_path=None, skip_header=False, quote=False, **kwargs
):
    """
    Run extraction from a stream or file and write results to a stream or file.

    Args:
        in_path: Source of input strings. ``None`` reads from stdin;
            a file path reads from that file; a list of strings uses
            them directly.
        out_path: Destination for results. ``None`` writes to stdout;
            a file path writes to that file; ``False`` returns the
            patterns as a list.
        skip_header (bool): If ``True``, skip the first line of input.
        quote (bool): If ``True``, wrap each pattern in double quotes.
        **kwargs: Additional keyword arguments passed to ``extract()``.

    Returns:
        A list of regular expression strings if ``out_path`` is
        ``False``, otherwise ``None``.
    """
    verbose = kwargs.get('verbose', 0)
    show_pp = show(verbose, VERBOSITY.PREPROCESSING)
    if type(in_path) in (list, tuple):
        strings = in_path
    elif in_path:
        if show_pp:
            print('Reading file %s.' % in_path)
        with open(in_path, encoding='utf-8') as f:
            strings = f.read().splitlines()
        if show(verbose, VERBOSITY.PREPROCESSING):
            print('Read file %s' % in_path)
    else:
        if show_pp:
            print('Ingesting strings')
        strings = [s.strip() for s in sys.stdin.readlines()]
        if strings and type(strings[0]) == bytes:
            strings = [s.decode('UTF-8') for s in strings]
        if show_pp:
            print('Ingested strings.')
    if skip_header:
        strings = strings[1:]
    if show_pp:
        print('Extracting strings')
    patterns = extract(strings, **kwargs)
    if show_pp:
        print('Extracted strings')
    if quote:
        patterns = [dquote(p) for p in patterns]
    if out_path is False:
        return patterns
    elif out_path:
        if show_pp:
            print('Writing results to %s.' % out_path)
        with open(out_path, 'w', encoding='utf-8') as f:
            for p in patterns:
                f.write(p + '\n')
        if show_pp:
            print('Written results to %s.' % out_path)
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
        'quote': False,
        'verbose': 0,
        'variableLengthFrags': False,
    }
    params['verbose'] = 0
    for a in args:
        if a.startswith('-'):
            if a == '-':
                params['in_path'] = None
            elif a in ('-h', '--header'):
                params['skip_header'] = True
            elif a in ('-g', '--group'):
                params['tag'] = True
            elif a in ('-q', '--quote'):
                params['quote'] = True
            elif a in ('-u', '-_', '--underscore'):
                params['extra_letters'] = (params['extra_letters'] or '') + '_'
            elif a in ('-d', '-.', '--dot', '--period'):
                params['extra_letters'] = (params['extra_letters'] or '') + '.'
            elif a in ('-m', '--minus', '--hyphen', '--dash'):
                params['extra_letters'] = (params['extra_letters'] or '') + '-'
            elif a in ('-v', '--version'):
                print(__version__)
                sys.exit(0)
            elif a in ('-V', '--verbose'):
                params['verbose'] = 1
            elif a in ('-VV', '--Verbose'):
                params['verbose'] = 2
            elif a in ('-1', '--single'):
                params['single'] = True
            elif a in ('-vlf', '--variable'):
                params['variableLengthFrags'] = True
            elif a in ('-flf', '--fixed'):
                params['variableLengthFrags'] = False
            elif a.startswith('--') and a[2:] in DIALECTS:
                params['dialect'] = a[2:]
            elif a in ('-?', '--help'):
                print(USAGE)
                sys.exit(0)
            else:
                m = re.match(VERBOSITY_LEVEL_RE, a)
                if m:
                    params['verbose'] |= int(str(m.group(1)))
                else:
                    raise TDDAError(USAGE)
        elif params['in_path'] == '':  # not previously set and not '-'
            params['in_path'] = a
        elif params['out_path'] is None:
            params['out_path'] = a
        else:
            raise TDDAError(USAGE)
    params['in_path'] = params['in_path'] or None  # replace '' with None
    extras = params['extra_letters']
    if extras:
        params['extra_letters'] = ''.join(sorted([c for c in extras]))
        # Order always, for consistency
    return params


def expand_or_falsify_vrle(rle, vrle, fixed=False, variableLength=False):
    """
    Given a run-length encoded sequence
        (e.g. ``[('A', 3), ('B', 4)]``)
    and (usually) a variable run-length encoded sequence
        (e.g. ``[('A', 2, 3), ('B', 1, 2)]``)

    expand the VRLE to include the case of the RLE, if they can be consistent.

    If they cannot, return False.

    If vrle is None, this indicates it hasn't been found yet, so rle is
    simply expanded to a VRLE.

    If vrle is False, this indicates that a counterexample has already
    been found, so False is returned again.

    If variableLength is set to True, patterns will be merged even if it is
    a different length from the vrle, as long as the overlapping part is
    consistent.
    """
    suf = ['fixed'] if fixed else []
    if vrle == False:
        return False
    elif vrle is None:
        return [
            ((r[0], r[1], r[1], 'fixed') if fixed else (r[0], r[1], r[1]))
            for r in rle
        ]  # Just accept the new one

    out = []
    lr, lv = len(rle), len(vrle)
    lc = min(lr, lv)  # length of overlapping block
    if lr == lv:
        for r, v in zip(rle, vrle):
            c, m, M = v[:3]
            n = r[1]
            if r[0] == c:
                if n >= m and n <= M:
                    out.append(v)
                elif n < m:
                    out.append((c, n, M, 'fixed') if fixed else (c, n, M))
                else:  # n > M
                    out.append((c, m, n, 'fixed') if fixed else (c, m, n))
            else:
                return False
        # All consistent
        return out
    elif not variableLength:
        return False

    for r, v in zip(rle[:lc], vrle[:lc]):
        c, m, M = v[:3]
        n = r[1]
        if r[0] == c:
            if n >= m and n <= M:
                out.append(v)
            elif n < m:
                out.append((c, n, M, 'fixed') if fixed else (c, n, M))
            else:  # n > M
                out.append((c, m, n, 'fixed') if fixed else (c, m, n))
        else:
            return False
    if lv == lc:  # variable one is shorter
        for r in rle[lc:]:
            c, f = r[:2]
            out.append((c, 0, f, 'fixed') if fixed else (c, 0, f))
    else:
        for v in vrle[lc:]:
            c, m, M = v[:3]
            out.append((c, 0, M, 'fixed') if fixed else (c, 0, M))
    return out


def escape(s, full=False):
    if full:
        return re.escape(s)
    else:
        return ''.join((c if c in UNESCAPES else re.escape(c)) for c in s)


def escaped_bracket(chars, dialect=None, inner=False):
    r"""
    Construct a regular expression Bracket (character class),
    obeying the special regex rules for escaping these:

      - Characters do not, in general need to be escaped
      - If there is a close bracket ("]") it mst be the first character
      - If there is a hyphen ("-") it must be the last character
      - If there is a carat ("^"), it must not be the first character
      - If there is a backslash, it's probably best to escape it.
        Some implementations don't require this, but it will rarely
        do any harm, and most implementation understand at least some
        escape sequences ("\w", "\W", "\d", "\s" etc.), so escaping
        seems prudent.

    However, javascript and ruby do not follow the unescaped "]" as the
    first character rule, so if either of these dialects is specified,
    the "]" will be escaped (but still placed in the first position.

    If inner is set to True, the result is returned without brackets.
    """
    opener, closer = ('', '') if inner else ('[', ']')
    if dialect in ('javascript', 'ruby'):
        prefix = r'\]' if ']' in chars else ''
    else:
        prefix = ']' if ']' in chars else ''
    suffix = (
        (r'\\' if '\\' in chars else '')
        + ('^' if '^' in chars else '')
        + ('-' if '-' in chars else '')
    )
    specials = r']\-^'
    mains = ''.join(c for c in chars if c not in specials)
    return '%s%s%s%s%s' % (opener, prefix, mains, suffix, closer)


def u_alpha_numeric_re(inc, exc, digits=True, dialect=None):
    r = r'[^\W%s%s]' % (
        '' if digits else '0-9',
        escaped_bracket(exc, dialect=dialect, inner=True),
    )
    i = escaped_bracket(inc, dialect=dialect) if len(inc) == 2 else escape(inc)
    return '(%s|%s)' % (r, i) if inc else r


def capture_group(s):
    """
    Places parentheses around s to form a capure group (a tagged piece of
    a regular expression), unless it is already a capture group.
    """
    return s if (s.startswith('(') and s.endswith(')')) else ('(%s)' % s)


def group_map_function(m, n_groups):
    N = len(m.groups())
    if N != n_groups:  # This means there are nested capture groups
        map = {}
        g = 1
        for i in range(1, N + 1):
            if is_outer_group(m, i):
                map[g] = i
                g += 1
        f = lambda n: map[n]
    else:
        f = lambda i: i
    return f


def is_outer_group(m, i):
    N = len(m.groups())
    return not any(
        m.start(g) <= m.start(i) and m.end(g) >= m.end(i) for g in range(1, i)
    )


def ilist(L=None):
    return array(INT_ARRAY, L or [])


def dquote(s):
    parts = [p.replace('\\', r'\\').replace('\n', r'\n') for p in s.split('"')]
    quoted = ('\\"').join(parts)
    return '"%s"' % quoted


def usage_error():
    print(USAGE, file=sys.stderr)
    sys.exit(1)


def show(verbosity, level):
    return verbosity & level


def main():
    params = get_params(sys.argv[1:])
    rexpy_streams(**params)


if __name__ == '__main__':
    main()
