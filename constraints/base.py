# -*- coding: utf-8 -*-

"""
tdda.base.constraints.py:
Base Constraint Functionality for Test-Driven Data Analysis (TDDA)
"""
from __future__ import division
from __future__ import print_function

import datetime
import json
import re
import sys

from collections import OrderedDict

PRECISIONS = ('open', 'closed', 'fuzzy')
STANDARD_FIELD_CONSTRAINTS = ('type', 'min', 'min_length', 'max', 'max_length',
                              'sign', 'max_nulls', 'no_duplicates',
                              'allowed_values')
STANDARD_FIELD_GROUP_CONSTRAINTS = ('lt', 'lte', 'eq', 'gt', 'gte')
SIGNS = ('positive', 'non-negative', 'zero', 'non-positive', 'negative',
         'zero', 'null')
TYPES = ('bool', 'int', 'real', 'date', 'string')
DATE_VALUED_CONSTRAINTS = ('min', 'max')
UTF8 = 'UTF-8'


RD = re.compile(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})')
RDT = re.compile(r'(\d{4})[-/](\d{1,2})[-/](\d{1,2})[ T]'
                 r'(\d{1,2}):(\d{2}):(\d{2})')


class Marks:
    tick = '✓'     # This is a tick mark; whether or not it displays in editors
    cross = '✗'    # This is a cross; again, it may not display
    nothing = '-'  # This is an en-dash; again, it may not display in editors


class SafeMarks:
    tick = 'OK'
    cross = ' X'
    nothing = ' -'


class TDDAObject(OrderedDict):
    """
    Ordered Dictionary
    """
    def __init__(self, *args, **kwargs):
        OrderedDict.__init__(self, *args, **kwargs)

    def set_key_order(self, keys):
        keys = keys + [k for k in self.keys() if k not in keys]
        for k in keys:
            try:
                v = self[k]
                del self[k]
                self[k] = v
            except KeyError:
                pass


class DatasetConstraints(object):
    def __init__(self, per_field_constraints=None, loadpath=None):
        if loadpath:
            self.fields = Fields()
            self.load(loadpath)
        else:
            self.fields = Fields(per_field_constraints)

    def __getitem__(self, k):
        if type(k) == int:
            k = self.fields.keys()[k]
        return self.fields[k]

    def add_field(self, fc):
        self.fields[fc.name] = fc

    def __str__(self):
        return 'FIELDS:\n\n%s' % str(self.fields)

    def load(self, path):
        """
        Builds a DatasetConstraints object from a json file
        """
        with open(path) as f:
            text = f.read()
        self.initialize_from_dict(sanitize(json.loads(text)))

    def initialize_from_dict(self, in_constraints):
        fields = in_constraints['fields'] or []
        for fieldname, c in fields.items():
            fc = []
            is_date = 'type' in c and c['type'] == 'date'
            for kind, value in c.items():
                constraint_constructor = FIELD_CONSTRAINTS_MAP.get(kind)
                if constraint_constructor:
                    if isinstance(value, dict):
                        constraint = constraint_constructor(**value)
                    else:
                        constraint = constraint_constructor(value)
                    if is_date and kind in DATE_VALUED_CONSTRAINTS:
                        constraint.value = get_date(constraint.value)
                    fc.append(constraint)
                else:
                    warn('Constraint kind %s for field %s unknown: ignored.'
                         % (kind, fieldname))
            if fc:
                self.add_field(FieldConstraints(fieldname, fc))

    def to_json(self):
        return json.dumps({'fields': {f: v.to_dict_value()
                                         for f, v in self.fields.items()}},
                                         indent=4)


class Fields(TDDAObject):
    def __init__(self, constraints=None):
        TDDAObject.__init__(self)
        for c in constraints or []:
            self[c.name] = c

    def to_dict_value(self):
        return OrderedDict((name, c.to_dict_value())
                             for (name, c) in self.items())

    def __str__(self):
        return str('\n\n'.join(str(v) for v in self.values()))


class FieldConstraints(object):
    """
    Container for constraints on a field.
    """
    def __init__(self, name=None, constraints=None):
        """
        The name of the field can be supplied, or left as null (None).
        Leaving it null can be appropriate if the same constraint is
        to be used for multiple fields.

        Constraints can be supplied as a list; if so, these will be copied
        into the dictionary using the constraint kind as a key.
        """
        self.name = name
        self.constraints = {}
        for c in constraints or []:
            self.constraints[c.kind] = c


    def to_dict_value(self):
        """
        Returns a pair consisting of the name supplied, or the stored name,
        and an ordered dictionary keyed on constraint kind with the value
        specifying the constraint. For simple constraints, the value is a
        base type; for more complex constraints with several components,
        the value will itself be an (ordered) dictionary.

        The ordering is all to make the JSON file get written in a sensible
        order, rather than being a jumbled mess.
        """
        d = OrderedDict()
        keys = to_preferred_order(self.constraints.keys(),
                                  STANDARD_FIELD_CONSTRAINTS)
        for k in keys:
            d[k] = self.constraints[k].to_dict_value()
        return d

    def __getitem__(self, k):
        if type(k) == int:
            keys = list(self.to_dict_value().keys())
            k = keys[k]
        return self.constraints[k]

    def __str__(self):
        keys = [k for k in STANDARD_FIELD_CONSTRAINTS
                if k in self.constraints]
        keys += list(sorted(set(self.constraints.keys()) - set(keys)))
        return str('Field %s:\n  %s' % (self.name,
                                        '\n  '.join('%13s: %s'
                                                    % (k, self.constraints[k])
                                                       for k in keys)))


class MultiFieldConstraints(FieldConstraints):
    """
    Container for constraints on a pairs (or higher numbers) of fields
    """
    def __init__(self, names=None, constraints=None):
        """
        The names of the fields can be supplied, or left as null (None).
        Leaving them null can be appropriate if the same constraint is
        to be used for multiple field groups, though will not serialize
        terrible well.

        Constraints can be supplied as a list; if so, these will be copied
        into the dictionary using the constraint kind as a key.
        """
        self.names = tuple(names)
        self.constraints = {}
        for c in constraints or []:
            self.constraints[c.kind] = c


    def to_dict_value(self):
        """
        Returns a pair consisting of
            - a comma-separated list of the field names
            - an ordered dictionary keyed on constraint kind with the value
              specifying the constraint.

        For simple constraints, the value is a
        base type; for more complex constraints with several components,
        the value will itself be an (ordered) dictionary.

        The ordering is all to make the JSON file get written in a sensible
        order, rather than being a jumbled mess.
        """
        d = OrderedDict()
        for k in STANDARD_FIELD_GROUP_CONSTRAINTS:
            if k in self.constraints:
                d[k] = self.constraints[k].to_dict_value()
        remainder = sorted(set(self.constraints.keys())
                           - set(STANDARD_FIELD_GROUP_CONSTRAINTS))
        for k in remainder:
            d[k] = self.constraints[k].to_dict_value()
        return d

    def __getitem__(self, k):
        if type(k) == int:
            keys = list(self.to_dict_value().keys())
            k = keys[k]
        return self.constraints[k]

    def name_key(self):
        return ','.join(self.names)

    def __str__(self):
        keys = [k for k in STANDARD_FIELD_GROUP_CONSTRAINTS
                if k in self.constraints]
        keys += list(sorted(set(self.constraints.keys()) - set(keys)))
        return str('Field %s:\n  %s' % (self.name_key(),
                                        '\n  '.join('%13s: %s'
                                                    % (k, self.constraints[k])
                                                       for k in keys)))

class Constraint(object):
    """
    Base container for a single constraint.
    All specific constraint types (should) subclass this.
    """
    def __init__(self, kind, value, **kwargs):
        """
        All constraints have a kind (a string) and a value, which should
        be a base type. The convention is that the value is a simple type,
        and that if it is null (None) the constraint is always satisifed.
        Some constraints do not really need a value (e.g., no_nulls),
        and in such cases the convention is the set the value to True
        to indicate that the constraint is in force.

        Some constraints accept or require extra parameters.
        These are supplied through keyword arguments.
        """
        self.kind = kind
        self.value = value
        for (k, v) in kwargs.items():
            self.__dict__[k] = v

        assert constraint_class(kind) == self.__class__.__name__

    def __repr__(self):
        """
        """
        kws = ', '.join('%s=%s' % (k, repr(v))
                        for (k, v) in sorted(self.__dict__.items())
                        if k not in ('kind', 'value'))
        return '%s(value=%s%s)' % (constraint_class(self.kind),
                                   repr(self.value),
                                   (', ' + kws) if kws else '')

    def to_dict_value(self):
        return self.value


#
# SINGLE FIELD CONSTRAINTS
#

class MinConstraint(Constraint):
    def __init__(self, value, precision=None):
        assert precision is None or precision in PRECISIONS
        Constraint.__init__(self, 'min', value, precision=precision)

    def to_dict_value(self):
        if self.precision is None:
            return Constraint.to_dict_value(self)
        else:
            return OrderedDict((('value', self.value),
                                ('precision', self.precision)))


class MaxConstraint(Constraint):
    def __init__(self, value, precision=None):
        assert precision is None or precision in PRECISIONS
        Constraint.__init__(self, 'max', value, precision=precision)

    def to_dict_value(self):
        if self.precision is None:
            return Constraint.to_dict_value(self)
        else:
            return OrderedDict((('value', self.value),
                                ('precision', self.precision)))


class SignConstraint(Constraint):
    def __init__(self, value):
        assert value is None or value in SIGNS
        Constraint.__init__(self, 'sign', value)


class TypeConstraint(Constraint):
    def __init__(self, value):
        if type(value) in (list, tuple):
            assert all(t in TYPES for t in value)
        else:
            assert value is None or value in TYPES
        Constraint.__init__(self, 'type', value)


class MaxNullsConstraint(Constraint):
    def __init__(self, value):
        Constraint.__init__(self, 'max_nulls', value)


class NoDuplicatesConstraint(Constraint):
    def __init__(self, value=True):
        assert value is None or value == True
        Constraint.__init__(self, 'no_duplicates', value)


class AllowedValuesConstraint(Constraint):
    def __init__(self, value):
        Constraint.__init__(self, 'allowed_values', value)


class MinLengthConstraint(Constraint):
    def __init__(self, value):
        Constraint.__init__(self, 'min_length', value)


class MaxLengthConstraint(Constraint):
    def __init__(self, value):
        Constraint.__init__(self, 'max_length', value)


#
# MULTI-FIELD CONSTRAINTS
#


class LtConstraint(Constraint):
    def __init__(self, value):
        Constraint.__init__(self, 'lt', value)


class LteConstraint(Constraint):
    def __init__(self, value):
        Constraint.__init__(self, 'lte', value)

class EqConstraint(Constraint):
    def __init__(self, value):
        Constraint.__init__(self, 'eq', value)


class GtConstraint(Constraint):
    def __init__(self, value):
        Constraint.__init__(self, 'gt', value)


class GteConstraint(Constraint):
    def __init__(self, value):
        Constraint.__init__(self, 'gte', value)


class Verification(object):
    def __init__(self, constraints, report='all', one_per_line=False):
        self.fields = TDDAObject()
        self.failures = 0
        self.passes = 0
        self.report = report
        self.one_per_line = one_per_line
        assert report in ('all', 'fields', 'constraints')

    def __str__(self):
        if self.report == 'fields':  # Report only fields with failures
            field_items = list((field, ver)
                                      for (field, ver) in self.fields.items()
                                      if ver.failures > 0)
        else:
            field_items = self.fields.items()
        fields = '\n\n'.join('%s: %s  %s  %s'
                           % (field,
                              plural(ver.failures, 'failure'),
                              plural(ver.passes, 'pass', 'es'),
                             '  '.join('%s %s' % (c, tcn(s))
                                       for (c, s) in ver.items()))
                           for field, ver in field_items)
        fields_part = 'FIELDS:\n\n%s\n\n' % fields if fields else ''
        return ('%sSUMMARY:\n\nPasses: %d\nFailures: %d'
                % (fields_part, self.passes, self.failures))


def constraint_class(kind):
    """
    The convention is that name of the class implementing the constraint
    has a simple relationship to the constraint kind, namely that
    a constraint whose kind is 'this_kind' is implemented by a class
    called ThisKindConstraint.

    So:

        min      --> MinConstraint
        min_length  --> MinLengthConstraint
        no_nulls --> NoNullsConstraint

    etc.

    This function maps the constraint kind to the class name using this rule.
    """
    return '%sConstraint' % ''.join(part.title() for part in kind.split('_'))


def strip_lines(s, side='r'):
    """
    Splits the given string into lines (at newlines), strips each line
    and rejoins. Is careful about last newline and default to stripping
    on the right only (side='r'). Use 'l' for left strip or anything
    else to strip both sides.
    """
    strip = (str.rstrip if side == 'r' else str.lstrip if side == 'l'
             else str.strip)
    end = '\n' if s.endswith('\n') else ''
    return '\n'.join([strip(line) for line in s.splitlines()]) + end


def verify(constraints, verifiers, VerificationClass=None, **kwargs):
    VerificationClass = VerificationClass or Verification
    results = VerificationClass(constraints, **kwargs)
    for name in constraints.fields:
        field_results = TDDAObject()  # results.fields[name]
        failures = passes = 0
        for c in constraints.fields[name]:
            verify = verifiers.get(c.kind)
            if verify:
                satisfied = verify(name, c)
                if satisfied:
                    passes += 1
                else:
                    failures += 1
            else:
                satisfied = None
            field_results[c.kind] = satisfied
        field_results.failures = failures
        results.failures += failures
        field_results.passes = passes
        results.passes += passes
        results.fields[name] = field_results
    return results


def tcn(sat):
    """
    Convert True/False/None value to the appropriate tick, cross
    or nothing mark for printing.
    """
    return Marks.nothing if sat is None else Marks.tick if sat else Marks.cross


def warn(s):
    print(s, file=sys.stderr)



#
# Mapping from constraint kind (e.g. 'min_length') to constraint class
# e.g. MinLengthConstraint.
#
# Note: Each mapped value is the class iself, not its name.
#

FIELD_CONSTRAINTS_MAP = {
    kind: eval(constraint_class(kind)) for kind in STANDARD_FIELD_CONSTRAINTS
}


def plural(n, s, pl=None):
    """
    Returns a string like '23 fields' or '1 field' where the
    number is n, the stem is s and the plural is either stem + 's'
    or stem + pl (if provided).
    """
    if pl is None:
        pl = 's'
    if n == 1:
        return '%s %s' % (n, s)
    else:
        return '%s %s%s' % (n, s, pl)


def sanitize(o):
    return o if sys.version_info.major >= 3 else UTF8DefiniteObject(o)


def UTF8Definite(s):
    """
    Converts a string to UTF-8 if it is unicode.
    Otherwise just returns the string.
    """
    return s if type(s) == types.StringType else s.encode(UTF8)

def UTF8DefiniteObject(s):
    """
    Converts all unicode within scalar or object, recursively, to unicode.
    Handles lists, tuples and dictionaries, as well as scalars.
    """
    if type(s) == unicode:
        return s.encode(UTF8)
    elif type(s) == list:
        return [UTF8DefiniteObject(v) for v in s]
    elif type(s) == tuple:
        return tuple([UTF8DefiniteObject(v) for v in s])
    elif type(s) == dict:
        return {UTF8DefiniteObject(k): UTF8DefiniteObject(v)
                for (k, v) in s.items()}
    return s


def get_date(d):
    for rex, L in ((RD, 3), (RDT, 6)):
        m = re.match(rex, d)
        if m:
            try:
                return datetime.datetime(*(int(m.group(i))
                                           for i in range(1, L + 1)))
            except ValueError:
                print ('Failed to read "%s" as date' % d, file=sys.stderr)
                return d
    return d


def to_preferred_order(keys, preferred_order):
    return ([k for k in preferred_order if k in list(keys)]
               + list(sorted(set(keys) - set(preferred_order))))

