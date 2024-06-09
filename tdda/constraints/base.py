# -*- coding: utf-8 -*-

"""
Classes for representing individual constraints.
"""
import datetime
import getpass
import json
import os
import re
import socket
import sys

from collections import OrderedDict

from tdda.version import version

PRECISIONS = ('open', 'closed', 'fuzzy')

CONSTRAINT_SUFFIX_MAP = OrderedDict((
    ('type', 'type'),
    ('min', 'min'),
    ('min_length', 'min_length'),
    ('max', 'max'),
    ('max_length', 'max_length'),
    ('sign', 'sign'),
    ('max_nulls', 'nonnull'),
    ('no_duplicates', 'nodups'),
    ('allowed_values', 'values'),
    ('rex', 'rex'),
    ('transform', None),  # this mapped value isn't used
))

STANDARD_FIELD_CONSTRAINTS = tuple(CONSTRAINT_SUFFIX_MAP.keys())
STANDARD_CONSTRAINT_SUFFIXES = tuple(CONSTRAINT_SUFFIX_MAP.values())
STANDARD_FIELD_GROUP_CONSTRAINTS = ('lt', 'lte', 'eq', 'gt', 'gte')
SIGNS = ('positive', 'non-negative', 'zero', 'non-positive', 'negative',
         'null')
TYPES = ('bool', 'int', 'real', 'date', 'string')
DATE_VALUED_CONSTRAINTS = ('min', 'max')
UTF8 = 'UTF-8'


RD = re.compile(r'^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$')
RDT = re.compile(r'^(\d{4})[-/](\d{1,2})[-/](\d{1,2})[ T]'
                 r'(\d{1,2}):(\d{2}):(\d{2})$')
RDTM = re.compile(r'^(\d{4})[-/](\d{1,2})[-/](\d{1,2})[ T]'
                  r'(\d{1,2}):(\d{2}):(\d{2})'
                  r'\.(\d+)$')

UNICODE_TYPE = str if sys.version_info[0] >= 3 else unicode

EPSILON_DEFAULT = 0.0   # no tolerance for min/max constraints for
                        # real (i.e. floating point) fields.

METADATA_KEYS = ('as_at', 'local_time', 'utc_time', 'creator',
                 'rdbms', 'source', 'host','user', 'dataset',
                 'n_records', 'n_selected', 'tddafile')



class Marks:
    tick = '✓'     # This is a tick mark; whether or not it displays in editors
    cross = '✗'    # This is a cross; again, it may not display
    nothing = '-'  # This is an en-dash; again, it may not display in editors


class SafeMarks:
    tick = 'OK'
    cross = 'X'
    nothing = '-'


class InvalidConstraintSpecification(Exception):
    pass


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
    """
    Container for constraints pertaining to a dataset.
    Currently only supports per-field constraints.
    """
    def __init__(self, per_field_constraints=None, loadpath=None):
        self.as_at = None
        self.local_time = None
        self.utc_time = None
        self.host = None
        self.user = None
        self.creator = None
        self.loadpath = self.tddafile = loadpath
        self.source = None
        self.dataset = None
        self.n_records = None
        self.n_selected = None
        if loadpath:
            self.fields = Fields()
            self.load(loadpath)
        else:
            self.fields = Fields(per_field_constraints)

    def set_creator(self, creator=None):
        self.creator = creator or 'TDDA %s' % version

    def set_rdbms(self, rdbms):
        self.rdbms = rdbms

    def set_source(self, source, dataset=None):
        self.source = source
        self.dataset = (dataset
                        or (os.path.basename(source) if source else None))

    def set_stats(self, n_records, n_selected=None):
        self.n_records = n_records
        self.n_selected = n_selected

    def __getitem__(self, k):
        if type(k) == int:
            k = self.fields.keys()[k]
        return self.fields[k]

    def __contains__(self, k):
        return k in self.fields

    def add_field(self, fc):
        self.fields[fc.name] = fc

    def remove_field(self, name):
        if name in self.fields:
            del self.fields[name]

    def __str__(self):
        return 'FIELDS:\n\n%s' % str(self.fields)

    def load(self, path):
        """
        Builds a DatasetConstraints object from a json file
        """
        with open(path) as f:
            text = f.read()
        obj = json.loads(text, object_pairs_hook=OrderedDict)
        self.initialize_from_dict(native_definite(obj))

    def initialize_from_dict(self, in_constraints):
        """
        Initializes this object from a dictionary in_constraints.
        Currently, the only key used from in_constraints is fields.

        The value of in_constraints['fields'] is expected to be
        a dictionary, keyed on field name, whose values are the
        constraints for that field.

        They constraints are keyed on the kind of constraint, and should
        contain either a single value (a scalar or a list), or a dictionary
        of keyword arguments for the constraint initializer.
        """
        fields = in_constraints['fields'] or {}
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
                elif not kind.startswith('#'):
                    warn('Constraint kind %s for field %s unknown: ignored.'
                         % (kind, fieldname))
            if fc:
                self.add_field(FieldConstraints(fieldname, fc))
        metadata = in_constraints.get('creation_metadata', {})
        for (k, v) in metadata.items():
            if k in METADATA_KEYS and v is not None:
                self.__dict__[k] = v
                if k == 'tddafile':
                    self.loadpath = v  # I think...

        try:
            self.postloadhook(in_constraints)
        except:
            pass

    def set_dates_user_host_creator(self, as_at=None):
        now = datetime.datetime.now()
        utcnow = datetime.datetime.utcnow()
        self.as_at = as_at
        self.local_time = now.isoformat(timespec='seconds')
        self.utc_time = utcnow.isoformat(timespec='seconds')
        self.host = socket.gethostname()
        try:    # Issue 18: getuser() can fail under Docker with password
                # files with no non-root users
            self.user = getpass.getuser()
        except:
            self.user = ''
        self.set_creator()

    def get_metadata(self, tddafile=None):
        d = OrderedDict(
            (k, getattr(self, k, None))
            for k in METADATA_KEYS if getattr(self, k, None) is not None
        )
        if tddafile:
            d['tddafile'] = tddafile
        return d

    def clear_metadata(self):
        self.metadata = None

    def to_dict(self, tddafile=None):
        """
        Converts the constraints in this object to a dictionary.
        """
        constraints = OrderedDict((
            (f, v.to_dict_value()) for f, v in self.fields.items()
        ))
        metadata = self.get_metadata(tddafile=tddafile)
        d = OrderedDict()
        if metadata:
            d['creation_metadata'] = metadata
        d['fields'] = constraints
        try:
            self.postdicthook(d)
        except:
            pass

        return d

    def to_json(self, tddafile=None):
        """
        Converts the constraints in this object to JSON.
        The resulting JSON is returned.
        """
        return strip_lines(json.dumps(self.to_dict(tddafile=tddafile),
                                      indent=4, ensure_ascii=False)) + '\n'

    def sort_fields(self, fields=None):
        """
        Sorts the field constraints within the object by field order,
        by default by alphabetical order.

        If a list of field names is provided, then the fields will appear
        in that given order (with any additional fields appended at the end).
        """
        if fields is None:
            fields = sorted(self.fields.keys())
        self.fields.set_key_order(fields)


class Fields(TDDAObject):
    def __init__(self, constraints=None):
        TDDAObject.__init__(self)
        for c in constraints or {}:
            self[c.name] = c

    def to_dict_value(self, raw=False):
        return OrderedDict((name, c.to_dict_value(raw=raw))
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
        self.constraints = OrderedDict()
        for c in constraints or {}:
            self.constraints[c.kind] = c

    def to_dict_value(self, raw=False):
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
            d[k] = self.constraints[k].to_dict_value(raw=raw)
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
        self.constraints = OrderedDict()
        for c in constraints or {}:
            self.constraints[c.kind] = c

    def to_dict_value(self):
        """
        Returns a pair consisting of
            - a comma-separated list of the field names
            - an ordered dictionary keyed on constraint kind with the value
              specifying the constraint.

        For simple constraints, the value is a
        base type; for more complex Constraints with several components,
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

    def check_validity(self, name, value, *valids):
        """
        Check that the value of a constraint is allowed. If it isn't,
        then the TDDA file is not valid.
        """
        allowed = []
        for vs in valids:
            allowed.extend(vs)
            if value in vs:
                return
        errmsg = ('must be one of: %s'
                  % (', '.join([json.dumps(v) for v in allowed])))
        raise InvalidConstraintSpecification('Invalid %s constraint value %s '
                                             '(%s)' % (name, value, errmsg))

    def to_dict_value(self, raw=False):
        return (self.value
                   if raw or type(self.value) not in (datetime.datetime,
                                                      datetime.date)
                else str(self.value))


#
# SINGLE FIELD CONSTRAINTS
#

class MinConstraint(Constraint):
    """
    Constraint specifying the minimum allowed value in a field.
    """
    def __init__(self, value, precision=None, comment=None):
        self.check_validity('min precision', precision, [None], PRECISIONS)
        Constraint.__init__(self, 'min', value, precision=precision)

    def to_dict_value(self, raw=False):
        if self.precision is None:
            return Constraint.to_dict_value(self, raw=raw)
        else:
            return OrderedDict((('value', self.value),
                                ('precision', self.precision)))


class MaxConstraint(Constraint):
    """
    Constraint specifying the maximum allowed value in a field.
    """
    def __init__(self, value, precision=None, comment=None):
        self.check_validity('max precision', precision, [None], PRECISIONS)
        Constraint.__init__(self, 'max', value, precision=precision)

    def to_dict_value(self, raw=False):
        if self.precision is None:
            return Constraint.to_dict_value(self, raw=raw)
        else:
            return OrderedDict((('value', self.value),
                                ('precision', self.precision)))


class SignConstraint(Constraint):
    """
    Constraint specifying allowed sign of values in a field.
    Used only for numeric fields (``real``, ``int``, ``bool``), and normally
    used in addition to Min and Max constraints.

    Possible values are ``positive``, ``non-negative``, ``zero``,
    ``non-positive``, ``negative`` and ``null``.
    """
    def __init__(self, value, comment=None):
        self.check_validity('sign', value, [None], SIGNS)
        Constraint.__init__(self, 'sign', value)


class TypeConstraint(Constraint):
    """
    Constraint specifying the allowed (TDDA) type of a field.
    This can be a single value, chosen from:

        - ``bool``
        - ``int``
        - ``real``
        - ``string``
        - ``date``

    or a list of such values, most commonly ``['int', 'real']``,
    sometimes used because of Pandas silent and automatic promotion
    of integer fields to floats if nulls are present.)
    """
    def __init__(self, value, comment=None):
        if type(value) in (list, tuple):
            for t in value:
                self.check_validity('type', t, TYPES)
        else:
            self.check_validity('type', value, [None], TYPES)
        Constraint.__init__(self, 'type', value)


class MaxNullsConstraint(Constraint):
    """
    Constraint on the maximum number of nulls allowed in a field.
    Usually 0 or 1.
    (The constraint generator only generates 0 and 1, but the verifier
    will verify and number.)
    """
    def __init__(self, value, comment=None):
        Constraint.__init__(self, 'max_nulls', value)


class NoDuplicatesConstraint(Constraint):
    """
    Constraint specifying that non dupicate non-null values are allowed
    in a field.

    Currently only generated for string fields, though could be used
    more broadly.
    """
    def __init__(self, value=True, comment=None):
        self.check_validity('no_duplicates', value, [None, True, False])
        Constraint.__init__(self, 'no_duplicates', value)


class AllowedValuesConstraint(Constraint):
    """
    Constraint restricting the allowed values in a field to an explicity list.

    Currently only used for string fields.

    When generating constraints, this code will only generate such a
    constraint if there are no more than ``MAX_CATEGORIES`` (= 20 at the
    time of writing, but check above in case this comment rusts)
    different values in the field.
    """
    def __init__(self, value, comment=None):
        Constraint.__init__(self, 'allowed_values', value)


class MinLengthConstraint(Constraint):
    """
    Constraint restricting the minimum length of strings in a string field.

    Generated instead of a ``MinConstraint`` by this generation code,
    but can be used in conjunction with a ``MinConstraint``.
    """
    def __init__(self, value):
        Constraint.__init__(self, 'min_length', value)


class MaxLengthConstraint(Constraint):
    """
    Constraint restricting the maximum length of strings in a string field.

    Generated instead of a ``MaxConstraint`` by this generation code,
    but can be used in conjunction with a ``MinConstraint``.
    """
    def __init__(self, value, comment=None):
        Constraint.__init__(self, 'max_length', value)


class RexConstraint(Constraint):
    """
    Constraint restricting a string field to match (at least) one of
    the regular expressions in a list given.
    """
    def __init__(self, value, comment=None):
        Constraint.__init__(self, 'rex', [native_definite(v) for v in value])


#
# MULTI-FIELD CONSTRAINTS
#


class LtConstraint(Constraint):
    """
    Constraint specifying that the first field of a pair should be
    (strictly) less than the second, where both are non-null.
    """
    def __init__(self, value):
        Constraint.__init__(self, 'lt', value)


class LteConstraint(Constraint):
    """
    Constraint specifying that the first field of a pair should be
    no greater than the second, where both are non-null.
    """
    def __init__(self, value):
        Constraint.__init__(self, 'lte', value)

class EqConstraint(Constraint):
    """
    Constraint specifying that two fields should have identical values
    where they are both non-null.
    """
    def __init__(self, value):
        Constraint.__init__(self, 'eq', value)


class GtConstraint(Constraint):
    """
    Constraint specifying that the first field of a pair should be
    (strictly) greater than the second, where both are non-null.
    """
    def __init__(self, value):
        Constraint.__init__(self, 'gt', value)


class GteConstraint(Constraint):
    """
    Constraint specifying that the first field of a pair should be
    greater than or equal to the second, where both are non-null.
    """
    def __init__(self, value):
        Constraint.__init__(self, 'gte', value)


class TransformConstraint(Constraint):
    """
    Not really a constraint, but a tranform to be applied to a field,
    allowing constraints to be applied to that transformed field.
    """
    def __init__(self, value):
        Constraint.__init__(self, 'transform', value)


class Verification(object):
    """
    Container for the result of a constraint verification for a dataset
    in the context of a given set of constraints.
    """
    def __init__(self, constraints, report='all',
                 ascii=False, detect=False, detect_outpath=None,
                 detect_write_all=False, detect_per_constraint=False,
                 detect_output_fields=None, detect_index=False,
                 detect_in_place=False, **kwargs):
        self.fields = TDDAObject()
        self.failures = 0
        self.passes = 0
        self.detection = None
        self.report = report
        self.ascii = ascii
        self.detect = detect
        self.detect_outpath = detect_outpath
        self.detect_write_all = detect_write_all
        self.detect_per_constraint = detect_per_constraint
        self.detect_output_fields = detect_output_fields
        self.detect_index = detect_index
        self.detect_in_place = detect_in_place
        if report not in ('all', 'fields', 'records'):
            raise Exception('Value for report must be one of "all", "fields"'
                            ' or "records", not "%s".' % report)
        if not detect_outpath and not detect and not detect_in_place:
            if any((detect_write_all, detect_per_constraint,
                    detect_output_fields, detect_index)):
                raise Exception('You have specified detection parameters '
                                'without specifying\na detection output path.')

    def __str__(self):
        """
        Returns string representation of the :py:class:`Verification` object.

        The format of the string is controlled by the value of the
        object's :py:attr:`report` property. If this is set to 'fields',
        then it reports only those fields that have failures.
        """
        if self.report in ('fields', 'records'):
            # Report only fields with failures
            field_items = list((field, ver)
                               for (field, ver) in self.fields.items()
                               if ver.failures > 0)
        else:
            field_items = self.fields.items()
        fields = '\n\n'.join('%s: %s  %s  %s'
                           % (field,
                              plural(ver.failures, 'failure'),
                              plural(ver.passes, 'pass', 'es'),
                              '  '.join('%s %s' % (c, tcn(s, self.ascii))
                                       for (c, s) in ver.items()))
                           for field, ver in field_items)
        fields_part = 'FIELDS:\n\n%s\n\n' % fields if fields else ''

        if self.report == 'records' and self.detection:
            return ('%sSUMMARY:\n\n'
                    'Records passing: %d\n'
                    'Records failing: %d'
                    % (fields_part,
                       self.detection.n_passing_records,
                       self.detection.n_failing_records))
        else:
            return ('%sSUMMARY:\n\n'
                    'Constraints passing: %d\n'
                    'Constraints failing: %d'
                    % (fields_part, self.passes, self.failures))


class Detection(object):
    """
    Object to represent the result of running detect.
    """
    def __init__(self, obj, n_passing_records, n_failing_records):
        """
        *obj*:
                            Object containing information about the detection,
                            of a type specific to the data source.

        *n_passing_records:
                            Number of passing records.

        *n_failing_records:
                            Number of failing records.
        """
        self.obj = obj
        self.n_passing_records = n_passing_records
        self.n_failing_records = n_failing_records


def constraint_class(kind):
    """
    The convention is that name of the class implementing the constraint
    has a simple relationship to the constraint kind, namely that
    a constraint whose kind is 'this_kind' is implemented by a class
    called ThisKindConstraint.

    So:

        ``min``      --> ``MinConstraint``
        ``min_length``  --> ``MinLengthConstraint``
        ``no_nulls`` --> ``NoNullsConstraint``

    etc.

    This function maps the constraint kind to the class name using this rule.
    """
    return '%sConstraint' % ''.join(part.title() for part in kind.split('_'))


def strip_lines(s):
    """
    Splits the given string into lines (at newlines), strips trailing
    whitespace from each line before rejoining.

    Is careful about last newline.
    """
    end = '\n' if s.endswith('\n') else ''
    return '\n'.join([line.rstrip() for line in s.splitlines()]) + end


def verify(constraints, fieldnames, verifiers, VerificationClass=None,
           detected_records_writer=None, **kwargs):
    """
    Perform a verification of a set of constraints.
    This is primarily an internal function, intended to be used by
    specific verifiers for various types of data.

    (Specifically, at the moment, the Pandas verifier verify_df, and
    the daatabase verifier, verify_db_table, both use this function, as
    does any other extension.)

    Inputs:

        constraints         is a DatasetConstraints object.

        verifiers           is a mapping from constraint kind to a verifier
                            callable.

                            NOTE: normally the verifier callable is a method
                            on a class that "knows" the dataset to be verified.

        VerificationClass   If provided, this should be a subclass of
                            Verificatation. This option is provided so
                            that callers can get back Verification object
                            with extra convenience methods. For example,
                            The Pandas code passes in a PandasVerification
                            class, which as a to_frame() method for turning
                            the result of the verification into a Pandas
                            DataFrame. If not provided, Verification
                            is used.

        kwargs              Any keyword arguments provided are passed to
                            the VerificationClass chosen.

    Returns a Verification object.
    """
    VerificationClass = VerificationClass or Verification
    results = VerificationClass(constraints, **kwargs)
    detect_outpath = kwargs.get('detect_outpath')
    detect = (detect_outpath is not None
              or kwargs.get('detect') is not None
              or kwargs.get('detect_in_place') is not None)

    allfields = sorted(constraints.fields.keys(),
                       key=lambda f: fieldnames.index(f) if f in fieldnames
                                                         else -1)

    if detect_outpath:
        # empty (and then remove) the detection output file first,
        # so that we can get an early error if the file isn't writeable,
        # and so that we don't leave a bogus wrong file in place if
        # we turn out not to detect anything.
        with open(detect_outpath, 'w') as f:
            pass
        os.remove(detect_outpath)

    for name in allfields:
        field_results = TDDAObject()
        failures = passes = 0
        for c in constraints.fields[name]:
            verify = verifiers.get(c.kind)
            if verify:
                satisfied = verify(name, c, detect)
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

    if detect and detected_records_writer and results.failures > 0:
        results.detection = detected_records_writer(**kwargs)
    return results


def detect(constraints, fieldnames, verifiers, VerificationClass=None,
           detected_records_writer=None, **kwargs):
    """
    Variation of verify which does detection too.
    """
    return verify(constraints, fieldnames, verifiers,
                  VerificationClass=VerificationClass,
                  detect=True, detected_records_writer=detected_records_writer,
                  **kwargs)


def tcn(sat, ascii=False):
    """
    Convert True/False/None value to the appropriate tick, cross
    or nothing mark for printing.
    """
    marks = SafeMarks if ascii else Marks
    return marks.nothing if sat is None else marks.tick if sat else marks.cross


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


def native_definite(o):
    return (UnicodeDefinite(o) if sys.version_info[0] >= 3
                               else UTF8DefiniteObject(o))


def UTF8Definite(s):
    """
    Converts a string to UTF-8 if it is unicode.
    Otherwise just returns the string.
    """
    return s if type(s) == bytes else s.encode(UTF8)


def UnicodeDefinite(s):
    """
    Converts a string to unicode if it is unicode.
    Otherwise just returns the string.
    """
    return s.decode(UTF8) if type(s) == bytes else s


def UTF8DefiniteObject(s):
    """
    Converts all unicode within scalar or object, recursively, to unicode.
    Handles lists, tuples and dictionaries, as well as scalars.
    """
    if type(s) == UNICODE_TYPE:
        return s.encode(UTF8)
    elif type(s) == list:
        return [UTF8DefiniteObject(v) for v in s]
    elif type(s) == tuple:
        return tuple([UTF8DefiniteObject(v) for v in s])
    elif isinstance(s, OrderedDict):
        return OrderedDict(((UTF8DefiniteObject(k), UTF8DefiniteObject(v)))
                           for (k, v) in s.items())
    elif isinstance(s, dict):
        return {UTF8DefiniteObject(k): UTF8DefiniteObject(v)
                for (k, v) in s.items()}
    return s


def NativeDefiniteObject(s):
    """
    Converts all non-native strings within scalar or object, recursively,
    to native strings.
    Handles lists, tuples and dictionaries, as well as scalars.
    """
    NON_NATIVE_STR = bytes if sys.version_info[0] >= 3 else unicode
    if type(s) is NON_NATIVE_STR:
        return native_definite(s)
    elif type(s) is list:
        return [NativeDefiniteObject(v) for v in s]
    elif type(s) is tuple:
        return tuple([NativeDefiniteObject(v) for v in s])
    elif isinstance(s, OrderedDict):
        return OrderedDict(((NativeDefiniteObject(k), NativeDefiniteObject(v))
                           for (k, v) in s.items()))
    elif isinstance(s, dict):
        return {NativeDefiniteObject(k): NativeDefiniteObject(v)
                for (k, v) in s.items()}
    return s


def get_date(d):
    for rex, L in ((RD, 3), (RDT, 6), (RDTM, 7)):
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



def fuzzy_greater_than(a, b, epsilon):
    """
    Returns a >~ b (a is greater than or approximately equal to b)

    At the moment, this simply reduces b by 1% if it is positive,
    and makes it 1% more negative if it is negative.
    """
    return (a >= b) or (a >= fuzz_down(b, epsilon))


def fuzzy_less_than(a, b, epsilon):
    """
    Returns a <~ b (a is less than or approximately equal to b)

    At the moment, this increases b by 1% if it is positive,
    and makes it 1% less negative if it is negative.
    """
    return (a <= b) or (a <= fuzz_up(b, epsilon))


def fuzz_down(v, epsilon):
    """
    Adjust v downwards, by a proportion controlled by self.epsilon.
    This is typically used for fuzzy minimum constraints.

    By default, positive values of v are reduced by 1% so that slightly
    smaller values can pass the fuzzy minimum constraint.

    Similarly, negative values are made 1% more negative, so that
    slightly more negative values can still pass a fuzzy minimum
    constraint.
    """
    if type(v) is datetime.datetime or type(v) is datetime.date:
        return v
    else:
        return v * ((1 - epsilon) if v >= 0 else (1 + epsilon))


def fuzz_up(v, epsilon):
    """
    Adjust v upwards, by a proportion controlled by self.epsilon.
    This is typically used for fuzzy maximum constraints.

    By default, positive values of v are increased by 1% so that
    slightly larger values can pass the fuzzy maximum constraint.

    Similarly, negative values are made 1% less negative, so that
    slightly less negative values can still pass a fuzzy maximum
    constraint.
    """
    if type(v) is datetime.datetime or type(v) is datetime.date:
        return v
    else:
        return v * ((1 + epsilon) if v >= 0 else (1 - epsilon))


def sort_constraint_dict(d):
    """
    Helper function for tests, to sort a constraints dictionary (read
    from a .tdda file) into alphabetical order by field name, and with
    all of the individual constraints in the same order in which they
    are generated.
    """
    constraintkey = ['type', 'min', 'max', 'min_length', 'max_length',
                     'sign', 'max_nulls', 'no_duplicates', 'allowed_values',
                     'rex']
    fields = OrderedDict((
        (f, OrderedDict(((k, kv)
                         for k, kv in sorted(v.items(),
                                             key=lambda x:
                                                  constraintkey.index(x[0])))))
        for f, v in sorted(d['fields'].items())
    ))
    return OrderedDict((('fields', fields),))
