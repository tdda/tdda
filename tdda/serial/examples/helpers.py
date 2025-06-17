import datetime

class Dummy:
    pass


def generate_base_python_lists():
    """
    Genenerates intended values for data frame as Python lists.
    """
    d = Dummy()
    d.row = list(range(1, 14))
    d.ints = [(None if i == 3 else i) for i in range(1, 14)]
    d.floats = [None if i == 3 else flt(i) for i in range(1, 14)]
    d.bools = [None if i == 3 else bool(i % 2) for i in range(1, 14)]
    d.stri = [None if v is None else str(v) for v in d.ints]
    d.strf = [None if v is None else f'{v:.2f}' for v in d.floats]
    d.names = ['one', 'two', None, 'four', 'five', 'six', 'seven', 'eight',
               'nine', 'ten', 'eleven', 'twelve', 'thirteen']
    d.accents = ['Café', 'caffè', None, 'Noël', '€£$', 'schloß', 'façade',
                 "Trompe-l'œil", 'Søren', 'à', 'naïve', 'Rhône', 'jalapeños']
    d.torture = ['easy', '"dquoted"', None, "'squoted'", 'with\\escape',
                 '', 'NULL', 'n/a', 'no', 'tab>\t<', '&', '&amp;', 'cpt ,|\tz']
    d.dates = [None if i == 3 else datetime.date(2000, 1, i)
               for i in range(1, 14)]
    d.dts = [None if i == 3 else datetime.datetime(2000, 1, i, 12, 34, 56)
             for i in  range(1, 14)]
    d.dtzs = [None if i == 3 else datetime.datetime(2000, 1, i, 12, 34, 56,
                                                    tzinfo=tz(i))
              for i in  range(1, 14)]
    d.nulls = [None] * 13
    return d


def tz(i):
    """Helper function to construct ith timezone used"""
    return datetime.timezone(datetime.timedelta(hours=i if i < 13 else -1))


def flt(i):
    """Helper function for float generation"""
    return i + i / (100 if i > 9 else 10)


