"""
Tests for tdda.serial.dateformats — format parsing, translation,
canonicalization.
"""

import unittest

from tdda.referencetest import ReferenceTestCase, tag

from tdda.serial.dateutils import (
    canonicalize_date_format,
    detect_format_style,
    literaldate_to_strftime,
    strftime_to_literaldate,
    strftime_to_yyyydate,
    to_strftime,
    yyyydate_to_strftime,
)


class TestDetectFormatStyle(ReferenceTestCase):
    def test_pcdate(self):
        self.assertEqual(detect_format_style('%Y-%m-%d'), 'pcdate')

    def test_pcdate_datetime(self):
        self.assertEqual(detect_format_style('%Y-%m-%dT%H:%M:%S'), 'pcdate')

    def test_isodate_date(self):
        self.assertEqual(detect_format_style('iso8601-date'), 'isodate')

    def test_isodate_datetime(self):
        self.assertEqual(detect_format_style('iso8601-datetime'), 'isodate')

    def test_isodate_datetime_tz(self):
        self.assertEqual(detect_format_style('iso8601-datetime-tz'), 'isodate')

    def test_isodate_generic(self):
        self.assertEqual(detect_format_style('iso8601'), 'isodate')

    def test_isodate_case_insensitive(self):
        self.assertEqual(detect_format_style('ISO8601-DATE'), 'isodate')

    def test_yyyydate_yyyy(self):
        self.assertEqual(detect_format_style('YYYY-MM-DD'), 'yyyydate')

    def test_yyyydate_lowercase(self):
        self.assertEqual(detect_format_style('yyyy-mm-dd'), 'yyyydate')

    def test_yyyydate_with_time(self):
        self.assertEqual(
            detect_format_style('YYYY-MM-DD HH:MM:SS'), 'yyyydate'
        )

    def test_yyyydate_dd_mm(self):
        self.assertEqual(detect_format_style('DD/MM/YYYY'), 'yyyydate')

    def test_literaldate_iso(self):
        self.assertEqual(detect_format_style('2000-12-31'), 'literaldate')

    def test_literaldate_euro(self):
        self.assertEqual(detect_format_style('31/12/2000'), 'literaldate')

    def test_literaldate_us(self):
        self.assertEqual(detect_format_style('12/31/2000'), 'literaldate')

    def test_literaldate_datetime(self):
        self.assertEqual(
            detect_format_style('2000-12-31T12:34:56'), 'literaldate'
        )

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            detect_format_style('')


class TestYyyydateToStrftime(ReferenceTestCase):
    """yyyydate_to_strftime: token strings → strftime."""

    def test_iso_date(self):
        self.assertEqual(yyyydate_to_strftime('YYYY-MM-DD'), '%Y-%m-%d')

    def test_iso_date_lower(self):
        self.assertEqual(yyyydate_to_strftime('yyyy-mm-dd'), '%Y-%m-%d')

    def test_euro_date(self):
        self.assertEqual(yyyydate_to_strftime('DD/MM/YYYY'), '%d/%m/%Y')

    def test_us_date(self):
        self.assertEqual(yyyydate_to_strftime('MM/DD/YYYY'), '%m/%d/%Y')

    def test_2y_date(self):
        self.assertEqual(yyyydate_to_strftime('DD/MM/YY'), '%d/%m/%y')

    def test_iso_datetime_T(self):
        self.assertEqual(
            yyyydate_to_strftime('YYYY-MM-DDTHH:MM:SS'),
            '%Y-%m-%dT%H:%M:%S',
        )

    def test_iso_datetime_space(self):
        self.assertEqual(
            yyyydate_to_strftime('YYYY-MM-DD HH:MM:SS'),
            '%Y-%m-%d %H:%M:%S',
        )

    def test_fractional_seconds(self):
        self.assertEqual(
            yyyydate_to_strftime('YYYY-MM-DDTHH:MM:SS.S'),
            '%Y-%m-%dT%H:%M:%S.%f',
        )

    def test_fractional_seconds_many(self):
        self.assertEqual(
            yyyydate_to_strftime('YYYY-MM-DDTHH:MM:SS.SSS'),
            '%Y-%m-%dT%H:%M:%S.%f',
        )

    def test_timezone_colon(self):
        self.assertEqual(
            yyyydate_to_strftime('YYYY-MM-DDTHH:MM:SS+ZZ:ZZ'),
            '%Y-%m-%dT%H:%M:%S%z',
        )

    def test_timezone_no_colon(self):
        self.assertEqual(
            yyyydate_to_strftime('YYYY-MM-DDTHH:MM:SS+ZZZZ'),
            '%Y-%m-%dT%H:%M:%S%z',
        )

    def test_timezone_minus(self):
        self.assertEqual(
            yyyydate_to_strftime('YYYY-MM-DDTHH:MM:SS.S-ZZ:ZZ'),
            '%Y-%m-%dT%H:%M:%S.%f%z',
        )

    def test_time_only_24h(self):
        self.assertEqual(yyyydate_to_strftime('HH:MM:SS'), '%H:%M:%S')

    def test_time_only_dot_sep(self):
        self.assertEqual(yyyydate_to_strftime('HH.MM.SS'), '%H.%M.%S')

    def test_time_only_pm(self):
        self.assertEqual(yyyydate_to_strftime('HH:MM:SSPM'), '%I:%M:%S%p')

    def test_time_only_am(self):
        self.assertEqual(yyyydate_to_strftime('HH:MM:SSAM'), '%I:%M:%S%p')

    def test_ampm_datetime(self):
        self.assertEqual(
            yyyydate_to_strftime('YY-MM-DDTHH:MM:SS.SPM'),
            '%y-%m-%dT%I:%M:%S.%f%p',
        )

    def test_hhmm_only(self):
        self.assertEqual(
            yyyydate_to_strftime('YYYY-MM-DD HH:MM'), '%Y-%m-%d %H:%M'
        )

    def test_mon_abbrev(self):
        self.assertEqual(yyyydate_to_strftime('DD-MON-YYYY'), '%d-%b-%Y')

    def test_month_full(self):
        self.assertEqual(yyyydate_to_strftime('DD-MONTH-YYYY'), '%d-%B-%Y')

    def test_dot_date(self):
        self.assertEqual(yyyydate_to_strftime('MM.DD.YY'), '%m.%d.%y')

    def test_no_tokens_raises(self):
        with self.assertRaises(ValueError):
            yyyydate_to_strftime('not-a-format')

    def test_ambiguous_mm_raises(self):
        # MM alone with no adjacent tokens to disambiguate
        with self.assertRaises(ValueError):
            yyyydate_to_strftime('MM')


class TestLiteraldateToStrftime(ReferenceTestCase):
    """literaldate_to_strftime: example dates → strftime."""

    def test_iso_date(self):
        self.assertEqual(literaldate_to_strftime('2000-12-31'), '%Y-%m-%d')

    def test_euro_date(self):
        self.assertEqual(literaldate_to_strftime('31/12/2000'), '%d/%m/%Y')

    def test_us_date(self):
        self.assertEqual(literaldate_to_strftime('12/31/2000'), '%m/%d/%Y')

    def test_euro_2y_year00(self):
        self.assertEqual(literaldate_to_strftime('31/12/00'), '%d/%m/%y')

    def test_euro_2y_year_ge60(self):
        self.assertEqual(literaldate_to_strftime('31/12/75'), '%d/%m/%y')

    def test_iso_datetime_T(self):
        self.assertEqual(
            literaldate_to_strftime('2000-12-31T12:34:56'),
            '%Y-%m-%dT%H:%M:%S',
        )

    def test_iso_datetime_space(self):
        self.assertEqual(
            literaldate_to_strftime('2000-12-31 12:34:56'),
            '%Y-%m-%d %H:%M:%S',
        )

    def test_iso_datetime_frac(self):
        self.assertEqual(
            literaldate_to_strftime('2000-12-31T12:34:56.789'),
            '%Y-%m-%dT%H:%M:%S.%f',
        )

    def test_iso_datetime_tz(self):
        self.assertEqual(
            literaldate_to_strftime('2000-12-31T12:34:56.789+0000'),
            '%Y-%m-%dT%H:%M:%S.%f%z',
        )

    def test_euro_datetime(self):
        self.assertEqual(
            literaldate_to_strftime('31/12/2000 12:34:56'),
            '%d/%m/%Y %H:%M:%S',
        )

    def test_ampm_datetime(self):
        self.assertEqual(
            literaldate_to_strftime('2000-12-31T12:34:56.789PM'),
            '%Y-%m-%dT%I:%M:%S.%f%p',
        )

    def test_ampm_datetime_am(self):
        self.assertEqual(
            literaldate_to_strftime('2000-12-31T12:34:56.789AM'),
            '%Y-%m-%dT%I:%M:%S.%f%p',
        )

    def test_time_only(self):
        self.assertEqual(literaldate_to_strftime('12:34:56'), '%H:%M:%S')

    def test_time_only_frac(self):
        self.assertEqual(
            literaldate_to_strftime('12:34:56.789'), '%H:%M:%S.%f'
        )

    def test_time_only_pm(self):
        self.assertEqual(literaldate_to_strftime('12:34:56PM'), '%I:%M:%S%p')

    def test_time_only_space_pm(self):
        self.assertEqual(literaldate_to_strftime('12:34:56 PM'), '%I:%M:%S%p')

    def test_alpha_month_abbrev(self):
        self.assertEqual(literaldate_to_strftime('31 Dec 2000'), '%d %b %Y')

    def test_alpha_month_full(self):
        self.assertEqual(
            literaldate_to_strftime('31 December 2000'), '%d %B %Y'
        )

    def test_alpha_month_us(self):
        self.assertEqual(literaldate_to_strftime('Dec 31 00'), '%b %d %y')

    # Ambiguous examples that should raise

    def test_ambiguous_day_month_raises(self):
        with self.assertRaises(ValueError):
            literaldate_to_strftime('01/02/2000')

    def test_ambiguous_2y_raises(self):
        # year=45, < 60 and != 00
        with self.assertRaises(ValueError):
            literaldate_to_strftime('31/12/45')

    def test_ambiguous_alpha_2y_raises(self):
        # 01 Dec 22: year=22 < 60
        with self.assertRaises(ValueError):
            literaldate_to_strftime('01 Dec 22')

    def test_ambiguous_alpha_day_year_raises(self):
        # 22 Dec 01: year=01 < 60
        with self.assertRaises(ValueError):
            literaldate_to_strftime('22 Dec 01')

    # Apache-style dates: [DD/Mon/YYYY:HH:MM:SS +ZZZZ]

    def test_apache_style(self):
        self.assertEqual(
            literaldate_to_strftime('[31/Dec/2000:12:34:56 +0000]'),
            '[%d/%b/%Y:%H:%M:%S%z]',
        )

    def test_apache_style_negative_tz(self):
        self.assertEqual(
            literaldate_to_strftime('[31/Dec/2000:12:34:56 -0500]'),
            '[%d/%b/%Y:%H:%M:%S%z]',
        )


class TestStrftimeToYyyydate(ReferenceTestCase):
    """strftime_to_yyyydate: strftime → token strings."""

    def test_iso_date(self):
        self.assertEqual(strftime_to_yyyydate('%Y-%m-%d'), 'YYYY-MM-DD')

    def test_euro_date(self):
        self.assertEqual(strftime_to_yyyydate('%d/%m/%Y'), 'DD/MM/YYYY')

    def test_us_date(self):
        self.assertEqual(strftime_to_yyyydate('%m/%d/%Y'), 'MM/DD/YYYY')

    def test_iso_datetime(self):
        self.assertEqual(
            strftime_to_yyyydate('%Y-%m-%dT%H:%M:%S'),
            'YYYY-MM-DDTHH:MM:SS',
        )

    def test_fractional(self):
        self.assertEqual(
            strftime_to_yyyydate('%Y-%m-%dT%H:%M:%S.%f'),
            'YYYY-MM-DDTHH:MM:SS.SSS',
        )

    def test_timezone(self):
        self.assertEqual(
            strftime_to_yyyydate('%Y-%m-%dT%H:%M:%S%z'),
            'YYYY-MM-DDTHH:MM:SS+ZZ:ZZ',
        )

    def test_ampm(self):
        self.assertEqual(
            strftime_to_yyyydate('%d/%m/%Y %I:%M:%S%p'),
            'DD/MM/YYYY HH:MM:SSPM',
        )

    def test_alpha_abbrev(self):
        self.assertEqual(strftime_to_yyyydate('%d-%b-%Y'), 'DD-MON-YYYY')

    def test_alpha_full(self):
        self.assertEqual(strftime_to_yyyydate('%d-%B-%Y'), 'DD-MONTH-YYYY')

    def test_2y(self):
        self.assertEqual(strftime_to_yyyydate('%d/%m/%y'), 'DD/MM/YY')


class TestStrftimeToLiteraldate(ReferenceTestCase):
    """strftime_to_literaldate: strftime → canonical example date."""

    def test_iso_date(self):
        self.assertEqual(strftime_to_literaldate('%Y-%m-%d'), '2000-12-31')

    def test_euro_date(self):
        self.assertEqual(strftime_to_literaldate('%d/%m/%Y'), '31/12/2000')

    def test_us_date(self):
        self.assertEqual(strftime_to_literaldate('%m/%d/%Y'), '12/31/2000')

    def test_iso_datetime(self):
        self.assertEqual(
            strftime_to_literaldate('%Y-%m-%dT%H:%M:%S'),
            '2000-12-31T12:34:56',
        )

    def test_euro_datetime(self):
        self.assertEqual(
            strftime_to_literaldate('%d/%m/%Y %H:%M:%S'),
            '31/12/2000 12:34:56',
        )

    def test_fractional(self):
        # %f gives microseconds (6 digits); canonical usec=789000
        self.assertEqual(
            strftime_to_literaldate('%Y-%m-%dT%H:%M:%S.%f'),
            '2000-12-31T12:34:56.789000',
        )

    def test_ampm(self):
        # hour=12 is noon → PM
        self.assertEqual(
            strftime_to_literaldate('%d/%m/%Y %I:%M:%S%p'),
            '31/12/2000 12:34:56PM',
        )

    def test_2y(self):
        self.assertEqual(strftime_to_literaldate('%d/%m/%y'), '31/12/00')


class TestCanonicalize(ReferenceTestCase):
    def test_yyyydate_uppercase(self):
        self.assertEqual(canonicalize_date_format('yyyy-mm-dd'), 'YYYY-MM-DD')

    def test_yyyydate_already_upper(self):
        self.assertEqual(canonicalize_date_format('YYYY-MM-DD'), 'YYYY-MM-DD')

    def test_literaldate_non_canonical(self):
        self.assertEqual(canonicalize_date_format('31/12/1985'), '31/12/2000')

    def test_literaldate_already_canonical(self):
        self.assertEqual(canonicalize_date_format('31/12/2000'), '31/12/2000')

    def test_literaldate_us(self):
        self.assertEqual(canonicalize_date_format('12/31/1999'), '12/31/2000')

    def test_pcdate_unchanged(self):
        self.assertEqual(canonicalize_date_format('%Y-%m-%d'), '%Y-%m-%d')

    def test_isodate_unchanged(self):
        self.assertEqual(
            canonicalize_date_format('iso8601-date'), 'iso8601-date'
        )

    def test_none(self):
        self.assertIsNone(canonicalize_date_format(None))


class TestToStrftime(ReferenceTestCase):
    """to_strftime: dispatch from any style."""

    def test_pcdate_passthrough(self):
        self.assertEqual(to_strftime('%Y-%m-%d'), '%Y-%m-%d')

    def test_isodate_passthrough(self):
        # isodate formats pass through (resolved by serial_format_to_strftime)
        self.assertEqual(to_strftime('iso8601-date'), 'iso8601-date')

    def test_yyyydate(self):
        self.assertEqual(to_strftime('DD/MM/YYYY'), '%d/%m/%Y')

    def test_literaldate(self):
        self.assertEqual(to_strftime('31/12/2000'), '%d/%m/%Y')

    def test_none(self):
        self.assertIsNone(to_strftime(None))


if __name__ == '__main__':
    ReferenceTestCase.main(testtdda=1)
