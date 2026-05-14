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
import tomli_w
import yaml


from collections import OrderedDict, namedtuple

from tdda.state import get_config
from tdda.tables import Table
from tdda.utils import (
    swap_ext,
    dict_to_json,
    dict_to_yaml,
    dict_to_toml,
    json_sanitize,
    strip_lines,
    nvl,
    richgood,
    richbad,
    unicode_definite,
    richgoodbad,
    write_or_return,
    tdda_css,
    constraint_val,
    indicator_field_name,
    rednz,
    redblack,
    coloured_tick_cross,
    print_stderr,
    TDDAError,
    globlike_match,
    plural,
)
from tdda.version import writable_version
from tdda.xmlgen import XML

from rich import print as rprint

from tdda.rexpy.rexutils import colour_regexes

outdict = dict

PRECISIONS = ('open', 'closed', 'fuzzy')

CONSTRAINT_SUFFIX_MAP = OrderedDict(
    (
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
    )
)

CONSTRAINT_COLS = dict(
    (
        ('type', 'Type Allowed'),
        ('min', 'Min Allowed'),
        ('max', 'Max Allowed'),
        ('sign', 'Sign Allowed'),
        ('max_nulls', 'Nulls Allowed'),
        ('no_duplicates', 'Duplicates Allowed'),
        ('allowed_values', 'Values Allowed'),
        ('rex', 'Regular Expressions'),
    )
)


STANDARD_FIELD_CONSTRAINTS = tuple(CONSTRAINT_SUFFIX_MAP.keys())
STANDARD_CONSTRAINT_SUFFIXES = tuple(CONSTRAINT_SUFFIX_MAP.values())
STANDARD_FIELD_GROUP_CONSTRAINTS = ('lt', 'lte', 'eq', 'gt', 'gte')
SIGNS = (
    'positive',
    'non-negative',
    'zero',
    'non-positive',
    'negative',
    'null',
)
TYPES = ('bool', 'int', 'real', 'date', 'string')
DATE_VALUED_CONSTRAINTS = ('min', 'max')
UTF8 = 'UTF-8'


RD = re.compile(r'^(\d{4})[-/](\d{1,2})[-/](\d{1,2})$')
RDT = re.compile(
    r'^(\d{4})[-/](\d{1,2})[-/](\d{1,2})[ T]'
    r'(\d{1,2}):(\d{2}):(\d{2})$'
)
RDTM = re.compile(
    r'^(\d{4})[-/](\d{1,2})[-/](\d{1,2})[ T]'
    r'(\d{1,2}):(\d{2}):(\d{2})'
    r'\.(\d+)$'
)

UNICODE_TYPE = str

EPSILON_DEFAULT = 0.0  # no tolerance for min/max constraints for
# real (i.e. floating point) fields.

METADATA_KEYS = (
    'as_at',
    'local_time',
    'utc_time',
    'creator',
    'rdbms',
    'source',
    'host',
    'user',
    'dataset',
    'n_records',
    'n_selected',
    'tddafile',
)


class Marks:
    tick = '✓'  # This is a tick mark; whether or not it displays in editors
    cross = '✗'  # This is a cross; again, it may not display
    nothing = '-'  # This is an en-dash; again, it may not display in editors


class SafeMarks:
    tick = 'OK'
    cross = 'X'
    nothing = '-'


class InvalidConstraintSpecification(TDDAError):
    pass


class PassFailCount:
    """
    Container for pass & fail counts for anything,
    with a few convenience properties
    """

    def __init__(self, name, passes, failures):
        self.name = name
        self.passes = passes
        self.failures = failures

    @property
    def total(self):
        return self.passes + self.failures

    @property
    def failure_rate(self):
        return self.failures / (self.total or 1)

    @property
    def bad_pc(self):
        return f'{self.failure_rate * 100:.2f}%'

    def __str__(self):
        return (
            f'PassFailCount({repr(self.name)}, {repr(self.passes)}, '
            f'{repr(self.failures)})'
        )


class ConstraintResult:
    """
    Container for a pass or fail result (in ok).
    Evaluates as boolean as self.ok

    info is usually used to store an information value for the constraint,
    e.g. the actual max for a max constraint.
    """

    def __init__(self, ok, info=None):
        self.ok = ok
        self.info = info


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
    """Constraints discovered for a dataset.

    Returned by ``discover_df``, ``discover_db_table``, and related
    functions. Can also be loaded from a ``.tdda`` JSON file.

    Attributes:
        fields: Per-field constraints, keyed by field name.
        n_records: Number of records in the source dataset.
        n_selected: Number of records selected (if filtering was applied).
        source: Source path or description.

    The key method for saving discovered constraints is ``to_json()``,
    which serializes the constraints to a ``.tdda`` JSON string.
    """

    def __init__(
        self,
        per_field_constraints=None,
        loadpath=None,
        no_md=False,
        allowed_fields=True,
        required_fields=True,
    ):
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
        self.allowed_fields = None
        self.required_fields = None
        self.no_md = no_md
        if loadpath:
            self.fields = Fields()
            self.load(loadpath)
        else:
            self.fields = Fields(per_field_constraints)
            self.allowed_fields = [] if allowed_fields else None
            self.required_fields = ['*'] if required_fields else None

    @property
    def table(self):
        if not hasattr(self, '_table'):
            self.to_table()
        return self._table

    def set_creator(self, creator=None):
        self.creator = creator or 'TDDA %s' % writable_version()

    def set_rdbms(self, rdbms):
        self.rdbms = rdbms

    def set_source(self, source, dataset=None):
        self.source = source
        self.dataset = dataset or (
            os.path.basename(source) if source else None
        )

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

    def load(self, path):
        """
        Builds a DatasetConstraints object from a json file
        """
        with open(path) as f:
            text = f.read()
        obj = json.loads(text, object_pairs_hook=OrderedDict)
        self.initialize_from_dict(unicode_definite(obj))

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
                    print(
                        'Constraint kind %s for field %s unknown: ignored.'
                        % (kind, fieldname),
                        file=sys.stderr,
                    )
            if fc:
                self.add_field(FieldConstraints(fieldname, fc))
        dataset = in_constraints.get('dataset', {})
        self.allowed_fields = dataset.get('allowed_fields', None)
        self.required_fields = dataset.get('required_fields', None)

        metadata = in_constraints.get('creation_metadata', {})
        for k, v in metadata.items():
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
        utcnow = datetime.datetime.now(datetime.timezone.utc)
        self.as_at = as_at
        self.local_time = now.isoformat(timespec='seconds')
        self.utc_time = utcnow.isoformat(timespec='seconds')
        self.host = socket.gethostname()
        try:  # Issue 18: getuser() can fail under Docker with password
            # files with no non-root users
            self.user = getpass.getuser()
        except:
            self.user = ''
        self.set_creator()

    def get_metadata(self, tddafile=None):
        d = outdict(
            (k, getattr(self, k, None))
            for k in METADATA_KEYS
            if getattr(self, k, None) is not None
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
        constraints = outdict(
            ((f, v.to_dict_value()) for f, v in self.fields.items())
        )
        metadata = self.get_metadata(tddafile=tddafile)
        if self.no_md:
            metadata = None
        d = outdict()
        if metadata:
            d['creation_metadata'] = metadata
        d['fields'] = constraints
        try:
            self.postdicthook(d)
        except:
            pass
        if self.allowed_fields is not None or self.required_fields is not None:
            D = {}
            if self.allowed_fields is not None:
                D['allowed_fields'] = self.allowed_fields
            if self.required_fields is not None:
                D['required_fields'] = self.required_fields
            d['dataset'] = D

        return d

    def to_json(self, tddafile=None):
        """
        Converts the constraints in this object to JSON.
        The resulting JSON is returned.
        """
        return dict_to_json(self.to_dict(tddafile=tddafile))

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

    def write_discovery_reports(self, reports_path, formats):
        """
        If any detection reports are specified by report_formats parameter
        or by configuration, this writes the report or reports.
        """

        for fmt in formats:
            outpath = swap_ext(reports_path, f'.{fmt}')
            if fmt == 'json':
                self.to_json_report(outpath)
            elif fmt == 'yaml':
                self.to_yaml_report(outpath)
            elif fmt == 'toml':
                self.to_toml_report(outpath)
            elif fmt in ('txt', 'text'):
                self.to_text_report(outpath)
            elif fmt in ('md', 'markdown'):
                self.to_markdown_report(outpath)
            elif fmt == 'html':
                self.to_html_report(outpath)
            else:
                print(
                    f'Ignoring unknown output format "{fmt}".', file=sys.stderr
                )

    def to_json_report(self, outpath=None):
        return write_or_return(
            self.to_json(), fwrite, json.dumps, path=outpath
        )

    def to_yaml_report(self, outpath=None):
        return write_or_return(
            self.to_dict(), yaml.dump, yaml.dump, path=outpath
        )

    def to_toml_report(self, outpath=None):
        return write_or_return(
            self.to_dict(),
            tomli_w.dump,
            tomli_w.dumps,
            path=outpath,
            binary=True,
        )

    def to_text_report(self, outpath=None):
        return write_or_return(
            self.table.toString(), fwrite, passthrough, path=outpath
        )

    def to_markdown_report(self, outpath=None, flavour='github'):
        return write_or_return(
            self.table.toMarkdown(flavour=flavour),
            fwrite,
            passthrough,
            path=outpath,
        )

    def to_html_report(self, outpath=None):
        xml = XML(
            html=True,
            headerAttr={'title': 'TDDA Discover Report'},
            css=tdda_css(),
        )
        xml.WriteElement('h1', 'TDDA Discover Report')
        xml.AddBalancedXML(self.table.toHTML())
        xml.CloseXML()
        return write_or_return(xml.xml(), fwrite, passthrough, path=outpath)

    def to_table(self):
        headers = ['Field name'] + list(CONSTRAINT_COLS.values())
        rows = []
        htmlrows = []
        any_rex = False
        for field in self.fields.values():
            row = [field.name]
            htmlrow = [None]
            for kind in CONSTRAINT_COLS:
                c = field.constraints.get(kind, None)
                if c is None and kind in ('min', 'max'):
                    c = field.constraints.get(kind + '_length', None)
                if c is not None:
                    v = c.value
                    row.append(constraint_val(c.value, kind))
                    if kind == 'rex':
                        htmlrow.append(colour_regexes(c.value))
                        any_rex = True
                    else:
                        htmlrow.append('')
                else:
                    row.append('')
                    htmlrow.append(None)
            rows.append(row)
            htmlrows.append(htmlrow)
        self._table = Table(
            headers,
            rows,
            attr={'class': 'solid tdda'},
            groupHeader='Individual Field Constraints',
            commonHeadColour=True,
            htmlrows=htmlrows if any_rex else None,
        )

    def __str__(self):
        return 'FIELDS:\n\n%s' % str(self.fields)


class Fields(TDDAObject):
    def __init__(self, constraints=None):
        TDDAObject.__init__(self)
        for c in constraints or {}:
            self[c.name] = c

    def to_dict_value(self, raw=False):
        return OrderedDict(
            (name, c.to_dict_value(raw=raw)) for (name, c) in self.items()
        )

    def __str__(self):
        return str('\n\n'.join(str(v) for v in self.values()))


class FieldConstraints(object):
    """Constraints discovered for a single field.

    Holds a dictionary of constraints keyed by constraint kind. The
    constraint kinds potentially present are:

    - **type**: coarse TDDA type (``'bool'``, ``'int'``, ``'real'``,
      ``'string'``, or ``'date'``).
    - **min**: minimum value (non-string fields).
    - **max**: maximum value (non-string fields).
    - **min_length**: shortest string length (string fields).
    - **max_length**: longest string length (string fields).
    - **sign**: sign constraint (``'positive'``, ``'non-negative'``,
      ``'zero'``, ``'non-positive'``, ``'negative'``, or ``'null'``).
    - **max_nulls**: maximum number of null values allowed.
    - **no_duplicates**: ``True`` if all non-null values are distinct
      (string fields).
    - **allowed_values**: list of permitted values (string fields with
      few distinct values).
    - **rex**: list of regular expressions that values must match
      (string fields, if rex discovery is enabled).

    Attributes:
        name: Field name.
        constraints: ``OrderedDict`` of constraint objects keyed by kind.

    Args:
        name: Field name, or ``None`` if applying to multiple fields.
        constraints: List of constraint objects to initialise with.
    """

    def __init__(self, name=None, constraints=None):
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
        d = outdict()
        keys = to_preferred_order(
            self.constraints.keys(), STANDARD_FIELD_CONSTRAINTS
        )
        for k in keys:
            d[k] = self.constraints[k].to_dict_value(raw=raw)
        return d

    def __getitem__(self, k):
        if type(k) == int:
            keys = list(self.to_dict_value().keys())
            k = keys[k]
        return self.constraints[k]

    def __str__(self):
        keys = [k for k in STANDARD_FIELD_CONSTRAINTS if k in self.constraints]
        keys += list(sorted(set(self.constraints.keys()) - set(keys)))
        return str(
            'Field %s:\n  %s'
            % (
                self.name,
                '\n  '.join(
                    '%13s: %s' % (k, self.constraints[k]) for k in keys
                ),
            )
        )


class MultiFieldConstraints(FieldConstraints):
    """Constraints discovered for a group of two or more fields.

    Subclass of ``FieldConstraints`` for multi-field constraints such
    as cross-field relationships.

    Attributes:
        names: Tuple of field names.
        constraints: ``OrderedDict`` of constraint objects keyed by kind.

    Args:
        names: Field names, or ``None``. Leaving them null can be
            appropriate if the same constraint is to be used for
            multiple field groups, though it will not serialize
            particularly well.
        constraints: List of constraint objects to initialise with.
    """

    def __init__(self, names=None, constraints=None):
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
        remainder = sorted(
            set(self.constraints.keys())
            - set(STANDARD_FIELD_GROUP_CONSTRAINTS)
        )
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
        keys = [
            k
            for k in STANDARD_FIELD_GROUP_CONSTRAINTS
            if k in self.constraints
        ]
        keys += list(sorted(set(self.constraints.keys()) - set(keys)))
        return str(
            'Field %s:\n  %s'
            % (
                self.name_key(),
                '\n  '.join(
                    '%13s: %s' % (k, self.constraints[k]) for k in keys
                ),
            )
        )


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
        for k, v in kwargs.items():
            self.__dict__[k] = v

        assert constraint_class(kind) == self.__class__.__name__

    def __repr__(self):
        """ """
        kws = ', '.join(
            '%s=%s' % (k, repr(v))
            for (k, v) in sorted(self.__dict__.items())
            if k not in ('kind', 'value')
        )
        return '%s(value=%s%s)' % (
            constraint_class(self.kind),
            repr(self.value),
            (', ' + kws) if kws else '',
        )

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
        errmsg = 'must be one of: %s' % (
            ', '.join([json.dumps(v) for v in allowed])
        )
        raise InvalidConstraintSpecification(
            'Invalid %s constraint value %s (%s)' % (name, value, errmsg)
        )

    def to_dict_value(self, raw=False):
        return (
            self.value
            if raw
            or type(self.value) not in (datetime.datetime, datetime.date)
            else str(self.value)
        )


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
            return OrderedDict(
                (('value', self.value), ('precision', self.precision))
            )


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
            return OrderedDict(
                (('value', self.value), ('precision', self.precision))
            )


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
        Constraint.__init__(self, 'rex', [unicode_definite(v) for v in value])


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
    """Result of verifying a dataset against a set of constraints.

    Returned by ``verify_df``, ``verify_db_table``, and related functions.
    Also used to represent detection results when anomaly detection is
    performed.

    Attributes:
        passes: Number of constraints that passed.
        failures: Number of constraints that failed.
        fields: Per-field verification results, keyed by field name.
        n_source_records: Number of records in the source dataset.
        report: Which fields to include in string output: ``'all'``
            or ``'fields'`` (only fields with failures).
    """

    def __init__(
        self,
        constraints,
        n_source_records,
        report='all',
        ascii=False,
        detect=False,
        outpath=None,
        write_all_records=False,
        per_constraint=False,
        output_fields=None,
        index=False,
        in_place=False,
        colour=False,
        verify_allowed_fields=None,
        verify_required_fields=None,
        config=None,
        **kwargs,
    ):
        self.config = config = get_config(config)
        self.constraints = constraints
        self.n_source_records = n_source_records
        self.fields = TDDAObject()
        self.failures = 0  # constraints
        self.passes = 0  # constraints
        self.detection = None
        self.report = report
        self.ascii = ascii
        self.colour = config.get('colour', colour)
        self.detect = detect
        self.outpath = outpath
        self.write_all_records = write_all_records
        self.per_constraint = per_constraint
        self.output_fields = output_fields
        self.index = index
        self.in_place = in_place
        self.detect_key = kwargs.get('key', [])
        self.detect_report_formats = kwargs.get('report_formats', [])
        cconfig = config.constraints
        self.detect_passes = cconfig.get('detect_passes')
        self.int_bools = cconfig.get('int_bools')

        self.verify_allowed_fields = nvl(
            cconfig.get('verify_allowed_fields', verify_allowed_fields),
            self.constraints.allowed_fields is not None,
        )
        self.verify_required_fields = nvl(
            cconfig.get('verify_required_fields', verify_required_fields),
            self.constraints.allowed_fields is not None,
        )

        if self.int_bools:
            self.bad_val = 0 if self.detect_passes else 1
        else:
            self.bad_val = False if self.detect_passes else True
        self.report_path = kwargs.get('report_path', outpath)

        if report not in ('all', 'fields', 'records'):
            raise TDDAError(
                'Value for report must be one of "all", "fields"'
                ' or "records", not "%s".' % report
            )
        if (
            not outpath
            and not detect
            and not in_place
            and not getattr(self, 'is_db', None)
        ):
            if any((write_all_records, per_constraint, output_fields, index)):
                raise TDDAError(
                    'You have specified detection parameters '
                    'without specifying\na detection output path.'
                )

    def indicator_field_name(self, field, constraint):
        return indicator_field_name(
            field,
            constraint,
            CONSTRAINT_SUFFIX_MAP,
            detect_passes=self.detect_passes,
        )

    def create_summary_stats(self, field_stats=None):
        n_fields_with_failures = len(
            list(
                (field, ver)
                for (field, ver) in self.fields.items()
                if ver.failures > 0
            )
        )

        self.summary_stats = stats = {
            'fields': PassFailCount(
                'fields',
                len(self.fields) - n_fields_with_failures,
                n_fields_with_failures,
            ),
            'constraints': PassFailCount(
                'constraints', self.passes, self.failures
            ),
        }
        if field_stats:
            r = nvl(self.detection, self)  # TODO: pd vs. db
            stats['records'] = PassFailCount(
                'records', r.n_passing_records, r.n_failing_records
            )
            stats['values'] = PassFailCount(
                'values',
                field_stats['_values'].passes,
                field_stats['_values'].failures,
            )

        if self.verify_allowed_fields or (
            self.verify_allowed_fields is None
            and self.allowed_fields is not None
        ):
            stats['extras'] = len(self.extra_fields)
        if self.verify_required_fields or (
            self.verify_required_fields is None
            and self.required_fields is not None
        ):
            stats['missing'] = len(self.missing_fields)

    def apply_required_and_allowed_constraints(self):
        if self.verify_required_fields:
            if self.missing_fields:
                self.failures += 1
            else:
                self.passes += 1
        else:
            self.missing_fields = None  # No longer relevant

        if self.verify_allowed_fields:
            if self.extra_fields:
                self.failures += 1
            else:
                self.passes += 1
        else:
            self.extra_fields = None  # No longer relevant

    def dataset_constraints_results(self):
        out = []
        if self.verify_allowed_fields:
            if self.extra_fields or self.report not in ('fields', 'records'):
                out.append(
                    'Extra (disallowed) fields: %s'
                    % (', '.join(self.extra_fields) or 'None')
                )

        if self.verify_required_fields:
            if self.missing_fields or self.report not in ('fields', 'records'):
                out.append(
                    'Missing (required) fields: %s'
                    % (', '.join(self.missing_fields) or 'None')
                )
        s = '\n'.join(out)
        return ('DATASET:\n\n%s\n\n' % s) if s else ''

    def to_string(self, colour=None, ascii=None):
        """
        Returns string representation of the ``Verification`` object.

        The format of the string is controlled by the value of the
        object's ``report`` property. If this is set to 'fields',
        then it reports only those fields that have failures.
        """
        ascii = nvl(ascii, self.ascii)
        colour = nvl(colour, self.colour)
        n_fields = len(self.fields)
        failing_field_items = list(
            (field, ver)
            for (field, ver) in self.fields.items()
            if ver.failures > 0
        )

        n_fields_with_failures = len(failing_field_items)
        if self.report in ('fields', 'records'):
            # Report only fields with failures
            field_items = failing_field_items
        else:
            field_items = self.fields.items()
        fields = '\n\n'.join(
            '%s: %s  %s  %s'
            % (
                field,
                richbad(
                    plural(ver.failures, 'failure'), colour, ver.failures > 0
                ),
                richgood(
                    plural(ver.passes, 'pass', 'es'), colour, ver.failures == 0
                ),
                '  '.join(
                    '%s %s' % (c, tcn(s, ascii, colour))
                    for (c, s) in ver.items()
                ),
            )
            for field, ver in field_items
        )
        fields_part = 'FIELDS:\n\n%s\n\n' % fields if fields else '\n'

        dataset_part = self.dataset_constraints_results()

        out = ['%s%sSUMMARY:\n' % (fields_part, dataset_part)]
        ss = self.summary_stats
        if self.report == 'records' and 'records' in ss:
            sr = ss['records']
            out.extend(
                [
                    f'Records: {sr.total:,}',
                    'Failing Records: %s'
                    % richgoodbad(
                        f'{sr.failures:,} ({sr.bad_pc})',
                        colour,
                        sr.failures == 0,
                    ),
                    '',
                ]
            )

        sf = ss['fields']
        out.extend(
            [
                f'Constrained Fields: {sf.total:,}',
                'Failing Fields: %s'
                % richgoodbad(
                    f'{sf.failures:,} ({sf.bad_pc})', colour, sf.failures == 0
                ),
                '',
            ]
        )

        if 'values' in ss:
            sv = ss['values']
            out.extend(
                [
                    f'Constrained Values: {sv.total:,}',
                    'Failing Values: %s'
                    % richgoodbad(
                        f'{sv.failures:,} ({sv.bad_pc})',
                        colour,
                        sv.failures == 0,
                    ),
                    '',
                ]
            )

        sc = ss['constraints']
        out.extend(
            [
                f'Constraints: {sc.total:,}',
                'Failing Constraints: %s'
                % richgoodbad(
                    f'{sc.failures:,} ({sc.bad_pc})', colour, sc.failures == 0
                ),
            ]
        )

        lines = []
        if self.verify_allowed_fields:
            n_extras = ss['extras']
            lines.append(
                f'Extra (disallowed) fields: %s'
                % richgoodbad(f'{n_extras}', colour, n_extras == 0)
            )
        if self.verify_required_fields:
            n_missing = ss['missing']
            lines.append(
                f'Missing (required) fields: %s'
                % richgoodbad(f'{n_missing}', colour, n_missing == 0)
            )
        if lines:
            out.extend([''] + lines)
        return '\n'.join(out)

    __str__ = to_string

    def to_table(self, fails, constraints):
        """
        Produce the summary table for detection.

        ARGS:

            fails: dictionary keyed on fieldname for fields with any failures.
            constraints: original constraints
        """
        headers = ['Values', 'Constraints'] + [
            'Allowed',
            'Actual',
            Marks.tick,
        ] * 8
        structured_header = [
            [1, 2, 'Name'],
            [2, 1, 'Failures'],
            [3, 1, 'Type'],
            [3, 1, 'Minimum'],
            [3, 1, 'Maximum'],
            [3, 1, 'Sign'],
            [3, 1, 'Max Nulls'],
            [3, 1, 'Duplicates'],
            [3, 1, 'Values'],
            [3, 1, 'Rex'],
        ]
        rows = []
        htmlrows = []
        any_rex = False
        constraint_fields = constraints['fields']
        for field, fc in constraint_fields.items():
            fail_details = fails['_field_stats'].get(field)
            cfail_details = fails['_constraint_stats'].get(field)
            field_info = self.field_info.get(field)  # actual field vals
            if fail_details:
                n_failing_values = fail_details.failures
                failing_constraints = fails['fields'].get(field)
                n_failing_constraints = (
                    len(failing_constraints) if failing_constraints else 0
                )
                row = [
                    field,
                    f'{n_failing_values:,}',
                    f'{n_failing_constraints}',
                ]
                htmlrow = [
                    field,
                    rednz(n_failing_values),
                    rednz(n_failing_constraints),
                ]
            else:
                row = [field, '0', '0']
                htmlrow = ['field', '0', '0']
            for k in CONSTRAINT_COLS:
                kind = k
                c = fc.get(kind, None)
                if c is None and kind in ('min', 'max'):
                    c = fc.get(kind + '_length', None)
                    if c:
                        kind = kind + '_length'
                if kind in cfail_details:
                    cfail = cfail_details[kind].n_failures > 0
                else:
                    cfail = False
                tick_or_cross = Marks.cross if cfail else Marks.tick
                if c is not None:
                    actual = (
                        field_info[kind]
                        if field_info and kind in field_info
                        else None
                    )
                    row.extend(
                        [
                            constraint_val(c, kind),
                            str(nvl(actual, '')),
                            tick_or_cross,
                        ]
                    )
                    if kind == 'rex':
                        htmlrow.extend(
                            [
                                colour_regexes(c),
                                None,
                                coloured_tick_cross(not cfail),
                            ]
                        )
                        any_rex = True
                    else:
                        htmlrow.extend(
                            [
                                None,
                                redblack(str(nvl(actual, '')), red=cfail),
                                coloured_tick_cross(not cfail),
                            ]
                        )
                else:
                    row.extend(['', '', ''])
                    htmlrow.extend([None, None, None])
            rows.append(row)
            htmlrows.append(htmlrow)
        self._table = Table(
            headers,
            rows,
            attr={'class': 'solid tdda'},
            structuredHeader=structured_header,
            commonHeadColour=True,
            htmlrows=htmlrows,
        )

    def write_detection_reports(self, minimal=True):
        """
        If any detection reports are specified (by the extension
        of the output file, or -r / --report flags, or by
        configuration, this writes the report or reports.
        """
        #        if not (self.report_path and self.detect_report_formats):
        #            return

        # TODO: If detection reports are no, and output_fields
        # are specified and do not include fields with failures
        # self.get_failure_values below will fail.

        d = self.constraints.to_dict()
        d_raw = self.constraints.to_dict()
        key_fields = self.detect_key
        field_stats = {}
        constraint_stats = {}
        if hasattr(self, 'build_field_stats'):
            self.build_field_stats(list(d['fields']))
        for field in list(d['fields']):
            constraints = d['fields'][field]
            field_stats[field] = self.get_field_stats(field)
            constraint_stats[field] = cstats = {}
            for constraint in list(constraints):
                value = constraints[constraint]
                c = constraints[constraint] = {'constraint_value': value}
                stats = self.get_constraint_stats(field, constraint)
                cstats[constraint] = stats
                if stats.n_failures == 0:
                    if minimal:
                        del constraints[constraint]
                    else:
                        c['n_failures'] = 0
                else:
                    c.update(stats.to_dict())
                    failures = self.get_failure_values(
                        field, constraint, key_fields
                    )
                    c['failures'] = (
                        json_sanitize(list(failures)) if failures else []
                    )
            if constraints == {}:
                del d['fields'][field]
        field_stats['_values'] = PassFailCount(
            '_values',
            sum(f.passes for f in field_stats.values()),
            sum(f.failures for f in field_stats.values()),
        )
        d['_field_stats'] = field_stats
        d['_constraint_stats'] = constraint_stats
        self.create_summary_stats(field_stats)
        self.fill_in_missing_db_rex_failures()
        self.to_table(d, d_raw)
        d = json_sanitize(d)

        for fmt in self.detect_report_formats:
            outpath = swap_ext(nvl(self.report_path, self.outpath), f'.{fmt}')
            if fmt == 'json':
                dict_to_json(d, outpath)
            elif fmt == 'yaml':
                dict_to_yaml(d, outpath)
            elif fmt == 'toml':
                dict_to_toml(d, outpath)
            elif fmt in ('txt', 'text'):
                write_text_detect_report(d, outpath, self.config)
            elif fmt in ('md', 'markdown'):
                write_markdown_detect_report(d, outpath, self.config)
            elif fmt == 'html':
                write_html_detect_report(d, outpath, self.config, self._table)
            else:
                print(
                    f'Ignoring unknown output format "{fmt}".', file=sys.stderr
                )

    def fill_in_missing_db_rex_failures(self):
        for fieldname, info in self.field_info.items():
            if 'rex' in info:
                if info['rex'] == []:  # DB does not return bad rex value
                    # And nor does pandas!
                    failures = self.get_failure_values(
                        fieldname, 'rex', [], max_vals=1
                    )
                    info['rex'] = (
                        json.dumps(list(failures)[0][0]) if failures else ''
                    )


class Detection(object):
    """
    Object to represent the result of running detect.
    """

    def __init__(self, obj, n_passing_records, n_failing_records):
        """
        Args:
            obj: Object containing information about the detection,
                of a type specific to the data source.
            n_passing_records: Number of passing records.
            n_failing_records: Number of failing records.
        """
        self.obj = obj
        self.n_passing_records = n_passing_records
        self.n_failing_records = n_failing_records

    @property
    def n_source_records(self):
        return self.n_passing_records + self.n_failing_records


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


def verify(
    constraints,
    fieldnames,
    verifiers,
    VerificationClass=None,
    detected_records_writer=None,
    config=None,
    **kwargs,
):
    """
    Perform a verification of a set of constraints.
    This is primarily an internal function, intended to be used by
    specific verifiers for various types of data.

    (Specifically, at the moment, the Pandas verifier verify_df, and
    the database verifier, verify_db_table, both use this function, as
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

        detected_records_writer  Function for writing failing records
                                 when detect is used.

        kwargs              Any keyword arguments provided are passed to
                            the VerificationClass chosen.

    Returns a Verification object.
    """
    VerificationClass = VerificationClass or Verification
    config = get_config(config)
    results = VerificationClass(constraints, config=config, **kwargs)
    outpath = kwargs.get('outpath')
    report_path = kwargs.get('reportpath')
    detect = (
        outpath is not None
        or kwargs.get('detect') is not None
        or kwargs.get('in_place') is not None
    )

    constrained_fields = constraints.fields
    glob_matches = globlike_match(constraints.allowed_fields, fieldnames)
    results.extra_fields = [
        f
        for f in fieldnames
        if f
        in set(fieldnames)
        - set(constrained_fields)
        - set(constraints.allowed_fields or [])
        - set(glob_matches)
    ]
    if constraints.required_fields:
        results.required_fields = globlike_match(
            constraints.required_fields, constrained_fields
        )
        results.missing_fields = [
            f for f in results.required_fields if f not in set(fieldnames)
        ]
    else:
        results.missing_fields = [
            f
            for f in constrained_fields
            if f in (set(constrained_fields) - set(fieldnames))
        ]
    allfields = [f for f in constrained_fields if f in set(fieldnames)]

    if outpath:
        # empty (and then remove) the detection output file first,
        # so that we can get an early error if the file isn't writable,
        # and so that we don't leave a bogus wrong file in place if
        # we turn out not to detect anything.
        with open(outpath, 'w') as f:
            pass
        os.remove(outpath)

    results.field_info = {}
    for name in allfields:
        field_results = TDDAObject()
        info = results.field_info[name] = {}
        failures = passes = 0
        for c in constraints.fields[name]:
            verify = verifiers.get(c.kind)
            if verify:
                satisfied = verify(name, c, detect)
                if (satisfied == True) or (
                    satisfied != False and satisfied.ok
                ):
                    passes += 1
                else:
                    failures += 1
            else:
                satisfied = ConstraintResult(None, None)
            if hasattr(satisfied, 'ok'):
                field_results[c.kind] = satisfied.ok
                info[c.kind] = satisfied.info
            else:
                field_results[c.kind] = satisfied
                info[c.kind] = None

        field_results.failures = failures  # constraints for this field
        field_results.passes = passes
        results.failures += failures  # all constraints
        results.passes += passes
        results.fields[name] = field_results

    results.apply_required_and_allowed_constraints()

    if detect:
        if detected_records_writer and results.failures > 0:
            if results.per_constraint:
                failing_fields = [
                    field
                    for field, result in results.fields.items()
                    if any(v != True for v in result.values())
                ]
                missing_failing_fields = set(results.output_fields) - set(
                    failing_fields
                )
                results.output_fields.extend(missing_failing_fields)
            results.detection = detected_records_writer(**kwargs)
            if not hasattr(results, 'is_db'):
                results.write_detection_reports()

        elif detected_records_writer and results.failures == 0:
            n_records = results.n_source_records
            n_fields = len(results.fields)
            n_constraints = sum(len(v) for v in results.fields.values())
            results.summary_stats = {
                'fields': PassFailCount('fields', n_fields, 0),
                'constraints': PassFailCount('constraints', n_constraints, 0),
                'records': PassFailCount('records', n_records, 0),
                'values': PassFailCount('values', n_records * n_fields, 0),
            }
    else:
        results.create_summary_stats()
    return results


def detect(
    constraints,
    fieldnames,
    verifiers,
    VerificationClass=None,
    detected_records_writer=None,
    **kwargs,
):
    """
    Variation of verify which does detection too.
    """
    return verify(
        constraints,
        fieldnames,
        verifiers,
        VerificationClass=VerificationClass,
        detect=True,
        detected_records_writer=detected_records_writer,
        **kwargs,
    )


def tcn(sat, ascii=False, colour=False):
    """
    Convert True/False/None value to the appropriate tick, cross
    or nothing mark for printing.
    """
    marks = SafeMarks if ascii else Marks
    mark = marks.nothing if sat is None else marks.tick if sat else marks.cross
    if colour:
        return (
            mark if sat is None else richgood(mark) if sat else richbad(mark)
        )
    else:
        return mark


#
# Mapping from constraint kind (e.g. 'min_length') to constraint class
# e.g. MinLengthConstraint.
#
# Note: Each mapped value is the class iself, not its name.
#

FIELD_CONSTRAINTS_MAP = {
    kind: eval(constraint_class(kind)) for kind in STANDARD_FIELD_CONSTRAINTS
}


def NativeDefiniteObject(s):
    """
    Converts all non-native strings within scalar or object, recursively,
    to native strings.
    Handles lists, tuples and dictionaries, as well as scalars.
    """
    NON_NATIVE_STR = bytes
    if type(s) is NON_NATIVE_STR:
        return unicode_definite(s)
    elif type(s) is list:
        return [NativeDefiniteObject(v) for v in s]
    elif type(s) is tuple:
        return tuple([NativeDefiniteObject(v) for v in s])
    elif isinstance(s, OrderedDict):
        return OrderedDict(
            (
                (NativeDefiniteObject(k), NativeDefiniteObject(v))
                for (k, v) in s.items()
            )
        )
    elif isinstance(s, dict):
        return {
            NativeDefiniteObject(k): NativeDefiniteObject(v)
            for (k, v) in s.items()
        }
    return s


def get_date(d):
    for rex, L in ((RD, 3), (RDT, 6), (RDTM, 7)):
        m = re.match(rex, d)
        if m:
            try:
                return datetime.datetime(
                    *(int(m.group(i)) for i in range(1, L + 1))
                )
            except ValueError:
                print('Failed to read "%s" as date' % d, file=sys.stderr)
                return d
    return d


def to_preferred_order(keys, preferred_order):
    return [k for k in preferred_order if k in list(keys)] + list(
        sorted(set(keys) - set(preferred_order))
    )


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
    constraintkey = [
        'type',
        'min',
        'max',
        'min_length',
        'max_length',
        'sign',
        'max_nulls',
        'no_duplicates',
        'allowed_values',
        'rex',
    ]
    fields = OrderedDict(
        (
            (
                f,
                OrderedDict(
                    (
                        (k, kv)
                        for k, kv in sorted(
                            v.items(), key=lambda x: constraintkey.index(x[0])
                        )
                    )
                ),
            )
            for f, v in sorted(d['fields'].items())
        )
    )
    return OrderedDict((('fields', fields),))


def write_text_detect_report(d, outpath, config):
    """
    Writes a human-readable textual report on detection failures
    """
    indent = '  '
    ffv = config.format_failure_values
    with open(outpath, 'w') as f:
        f.write('TDDA FAILURES REPORT\n\n')
        f.write('FIELDS:\n')
        for field, constraints in d['fields'].items():
            f.write(f'\nField: {field}\n')
            for ic, (constraint, results) in enumerate(constraints.items()):
                label = f'{indent}Constraint: {constraint}: '
                value = results['constraint_value']
                is_rex = constraint == 'rex'
                fval = config.format_constraint_value(
                    value, len(label), 4, rex=is_rex
                )
                if fval.startswith('\n'):
                    label = label[:-1]
                nl = '\n' if ic > 0 else ''
                f.write(f'{nl}{label}{fval}\n')
                nf = results['n_failures']
                n = nf + results['n_passes']
                pc = results['failure_rate']
                f.write(f'{indent * 2}Failures: {nf:,} / {n:,} ({pc})\n')
                for failure in results['failures']:
                    f.write(f'{indent * 3}{ffv(failure)}\n')


def write_markdown_detect_report(d, outpath, config):
    """
    Writes a human-readable textual report on detection failures
    """
    ffv = config.format_failure_values
    with open(outpath, 'w') as f:
        f.write('# TDDA FAILURES REPORT:\n')
        f.write('## FIELDS:\n')
        for field, constraints in d['fields'].items():
            f.write(f'\n### Field: {field}\n')
            for ic, (constraint, results) in enumerate(constraints.items()):
                label = f'**Constraint:** `{constraint}`: '
                value = results['constraint_value']
                is_rex = constraint == 'rex'
                fval = config.format_constraint_value(
                    value, len(label), 4, rex=is_rex
                )
                if fval.startswith('\n'):
                    label = label[:-1]
                nl = '\n' if ic > 0 else ''
                f.write(f'{nl} * {label}`{fval}`\n')
                nf = results['n_failures']
                n = nf + results['n_passes']
                pc = results['failure_rate']
                f.write(f'   * **Failures:** {nf:,} / {n:,} ({pc})\n')
                for failure in results['failures']:
                    f.write(f'      * `{ffv(failure)}`\n')


def write_html_detect_report(d, outpath, config, table=None):
    """
    Writes a human-readable textual report on detection failures
    """
    indent = '  '
    ffv = config.format_failure_values
    xml = XML(
        html=True,
        headerAttr={'title': 'TDDA Failure Report'},
        css=tdda_css(),
    )

    xml.WriteElement('h1', 'TDDA FAILURE REPORT')
    xml.OpenElement('div', attributes=(('id', 'tdda-discover'),))

    if table:
        xml.WriteElement('h2', 'Summary:')
        table.toHTML(xml=xml)

    xml.WriteElement('h2', 'Fields:')
    for field, constraints in d['fields'].items():
        xml.WriteElement('h3', f'Field: {field}')

        for ic, (constraint, results) in enumerate(constraints.items()):
            xml.OpenElement('ul')
            xml.OpenElement('li')
            xml.WriteElement('b', 'Constraint: ')
            xml.WriteElement('code', constraint)
            value = results['constraint_value']
            xml.WriteContent(':')
            xml.WriteElement('code', value)
            xml.CloseElement('li')

            is_rex = constraint == 'rex'
            label = f'Constraint: {constraint}: '
            fval = config.format_constraint_value(
                value, len(label), 4, rex=is_rex
            )

            nf = results['n_failures']
            n = nf + results['n_passes']
            pc = results['failure_rate']
            xml.OpenElement('li')
            xml.WriteElement('b', 'Failures: ')
            xml.WriteContent(f'{nf:,} / {n:,} ({pc})')
            xml.CloseElement('li')

            xml.OpenElement('ul')
            for failure in results['failures']:
                xml.OpenElement('li')
                xml.WriteElement('code', f'{ffv(failure)}')
                xml.CloseElement('li')
            xml.CloseElement('ul')
            xml.CloseElement('ul')
    xml.CloseElement('div')

    xml.CloseXML()

    with open(outpath, 'w') as f:
        f.write(xml.xml())


def fwrite(content, f):
    f.write(content)


def passthrough(content):
    return content


def constraints_from_path_or_dict(path_or_dict):
    if isinstance(path_or_dict, dict):
        constraints = DatasetConstraints()
        constraints.initialize_from_dict(unicode_definite(path_or_dict))
    else:
        constraints = DatasetConstraints(loadpath=path_or_dict)
    return constraints
