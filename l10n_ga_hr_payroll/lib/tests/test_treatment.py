"""Vocabulaire du traitement social / fiscal d'une rubrique (ADR-17, F6, D-16)."""

import pytest
from ga_fiscal_core.exemptions import SOCIAL_CAPS, TAX_CAPS
from ga_fiscal_core.treatment import (
    CAPPED,
    DAS_COLUMNS,
    SOCIAL_BASES,
    TAX_BASES,
    check_treatment,
    social_group,
    tax_group,
)


def test_vocabularies():
    assert SOCIAL_BASES == ('subject', 'excluded', 'capped', 'none')
    assert TAX_BASES == ('taxable', 'exempt', 'capped', 'none')
    assert 'none' in DAS_COLUMNS
    assert CAPPED == 'capped'


@pytest.mark.parametrize(
    ('base', 'group', 'expected'),
    [('subject', None, None), ('excluded', None, 'EXCLUDED'), ('capped', 'TRANSPORT_35K', 'TRANSPORT_35K')],
)
def test_social_group(base, group, expected):
    assert social_group(base, group) == expected
    assert expected is None or expected in SOCIAL_CAPS


@pytest.mark.parametrize(
    ('base', 'group', 'expected'),
    [('taxable', None, None), ('exempt', None, 'EXEMPT'), ('capped', 'BONUS_4M', 'BONUS_4M')],
)
def test_tax_group(base, group, expected):
    assert tax_group(base, group) == expected
    assert expected is None or expected in TAX_CAPS


def test_none_base_has_no_group():
    assert social_group('none', None) is None
    assert tax_group('none', None) is None


def test_valid_treatments_pass():
    check_treatment('GA_X', 'capped', 'TRANSPORT_35K', 'capped', 'TRANSPORT_DAILY')
    check_treatment('GA_Y', 'excluded', None, 'exempt', None)
    check_treatment('GA_Z', 'none', None, 'none', None)


@pytest.mark.parametrize(
    ('args', 'message'),
    [
        (('bad', None, 'taxable', None), 'sociale'),
        (('subject', None, 'bad', None), 'fiscale'),
        (('capped', None, 'taxable', None), 'groupe'),
        (('subject', None, 'capped', None), 'groupe'),
        (('subject', 'TRANSPORT_35K', 'taxable', None), 'plafonn'),
        (('subject', None, 'taxable', 'BONUS_4M'), 'plafonn'),
        (('capped', 'UNKNOWN', 'taxable', None), 'inconnu'),
        (('subject', None, 'capped', 'UNKNOWN'), 'inconnu'),
        (('capped', 'EXCLUDED', 'taxable', None), 'total'),
        (('subject', None, 'capped', 'EXEMPT'), 'total'),
        (('none', None, 'taxable', None), 'none'),
    ],
)
def test_invalid_treatments(args, message):
    with pytest.raises(ValueError, match=message):
        check_treatment('GA_BAD', *args)
