# -*- coding: utf-8 -*-

"""
equlity.py: comparison mechanism for arbitrary comparables

Source repository: http://github.com/tdda/tdda

License: MIT

Copyright (c) Stochastic Solutions Limited 2016-2020
"""

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division

from tdda.referencetest.basecomparison import BaseComparison, Diffs

def UNSPECIFIED():
    pass


class EqualityComparison(BaseComparison):

    def assertEqual(self, name, actual, expected,
                    preprocess=None, msgs=None):
        """
        Compare two lists of strings (actual and expected), one-by-one.

            *name*
                                a name or identifier for the case,
                                usually the inputs to a function being
                                tested or something that lets someone
                                figure out which case caused a failure
            *actual*
                                is a list of strings.
            *expected*
                                is the expected list of strings.
            *preprocess*
                                is an optional function that takes an input
                                of the same kind as actual and expected
                                and preprocesses it in some way;
                                this function will be applied to both
                                the actual and expected.
            *msgs*
                                is an optional Diffs object, where information
                                about differences will be appended; if not
                                specified, a new object will be created and
                                returned.

        Returns a tuple (failures, msgs), where failures is 1 if the lists
        differ and 0 if they are the same. The returned msgs is a list
        containing information about how they differed.
        """

        if msgs is None:
            msgs = Diffs()

        process = preprocess or (lambda x: x)
        processed_expected = process(expected)
        processed_actual = process(actual)

        same = processed_actual == processed_expected
        if not same:
            prefix = 'Raw ' if preprocess else ''
            self.info(msgs, '\n\nCase %s: failure.\n'
                            '    %sActual: %s\n'
                            '  %sExpected: %s'
                             % (name, prefix, actual, prefix, expected))
            if preprocess:
                self.info(msgs, '    Processed Actual: %s\n'
                                '  Processed Expected: %s'
                                % (actual, expected))
        return (0 if same else 1, msgs)

    def multipleAssertEqual(self, cases, preprocess=None, msgs=None):
        if msgs is None:
            msgs = Diffs()

        nFailures = 0
        if isinstance(cases, dict):
            for name, (actual, expected) in cases.items():
                r, _ = self.assertEqual(name, actual, expected, preprocess,
                                        msgs)
                nFailures += r
        else:
            for (name, actual, expected) in cases:
                r, _ = self.assertEqual(name, actual, expected, preprocess,
                                        msgs)
                nFailures += r
        return (nFailures, msgs)

    def checkFunctionByArg(self, f, cases, preprocess=None, msgs=None,
                            fixedresult=UNSPECIFIED):
        if fixedresult is UNSPECIFIED:
            caselist = (((arg,), {}, expected) for (arg, expected) in cases)
        else:
            caselist = (((arg,), {}) for args in cases)
        return self.checkFunctionByArgsKWArgs(f, caselist, preprocess, msgs,
                                              fixedresult)

    def checkFunctionByArgs(self, f, cases, preprocess=None, msgs=None,
                            fixedresult=UNSPECIFIED):
        if fixedresult is UNSPECIFIED:
            caselist = ((args, {}, expected) for (args, expected) in cases)
        else:
            caselist = ((args, {}) for args in cases)
        return self.checkFunctionByArgsKWArgs(f, caselist, preprocess, msgs,
                                              fixedresult)

    def checkFunctionByKWArgs(self, f, cases, preprocess=None, msgs=None,
                              fixedresult=UNSPECIFIED):
        if fixedresult is UNSPECIFIED:
            caselist = (((), kw, expected) for (kw, expected) in cases)
        else:
            caselist = (((), kw) for kw in cases)
        return self.checkFunctionByArgsKWArgs(f, caselist, preprocess, msgs,
                                              fixedresult)

    def checkFunctionByArgsKWArgs(self, f, cases, preprocess=None, msgs=None,
                                  fixedresult=UNSPECIFIED):
        if msgs is None:
            msgs = Diffs()

        nFailures = 0
        if fixedresult is not UNSPECIFIED:
            cases = ((args, kw, fixedresult) for (args, kw) in cases)
        for args, kw, expected in cases:
            argv = tuple(args)
            sarg = repr(argv)[1:-1]
            skw = repr(kw)[1:-1]
            strargs = '%s%s%s' % (sarg, ', ' if sarg and skw else '', skw)
            case = '%s(%s)' % (f.__name__, strargs)
            r, _ = self.assertEqual(case, f(*argv, **kw), expected,
                                    preprocess=preprocess, msgs=msgs)
            nFailures += r
        return (nFailures, msgs)

