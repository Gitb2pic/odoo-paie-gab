"""Mise en page du bulletin imprimé (plan 2.7 b) : sections et lignes calculées."""

import pytest
from ga_fiscal_core import print_layout as pl


@pytest.mark.parametrize(
    ('code', 'expected'),
    [
        ('10000', pl.GAINS),
        (19999, pl.GAINS),
        ('25150', pl.CONTRIBUTIONS),
        ('30110', pl.BENEFITS),
        ('31500', pl.TAXES),
        ('32500', pl.TAXES),
        ('34010', pl.ALLOWANCES),
        ('40100', pl.DEDUCTIONS),
        ('80900', pl.PAY),
    ],
)
def test_section(code, expected):
    assert pl.section(code) == expected


@pytest.mark.parametrize('code', ['20000', '9999', '99999', '70000'])
def test_section_out_of_range(code):
    with pytest.raises(ValueError):
        pl.section(code)


def test_virtual_codes_order():
    assert pl.ABSENCE < pl.TOTAL_GROSS < pl.TOTAL_CONTRIBUTIONS < pl.TOTAL_BENEFITS < pl.TCS_BASE
    assert pl.TCS_BASE < pl.TOTAL_GAINS < pl.TOTAL_DEDUCTIONS
    assert pl.section(pl.ABSENCE) == pl.GAINS
