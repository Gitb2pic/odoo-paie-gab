"""Indemnités récurrentes (F15) : montant selon le mode, prorata des jours de validité (D-35)."""

from datetime import date

import pytest
from ga_fiscal_core.allowances import FIXED, QUANTITY_RATE, WAGE_PERCENT, allowance_amount, validity_ratio


@pytest.mark.parametrize(
    ('mode', 'value', 'quantity', 'wage', 'expected'),
    [
        (FIXED, 50000, 0, 900000, 50000),
        (WAGE_PERCENT, 10, 0, 450000, 45000),
        (WAGE_PERCENT, 12.5, 0, 333333, 41667),
        (QUANTITY_RATE, 2500, 22, 0, 55000),
        (QUANTITY_RATE, 2500, 0, 0, 0),
    ],
)
def test_allowance_amount(mode, value, quantity, wage, expected):
    assert allowance_amount(mode, value, quantity, wage) == expected


def test_allowance_amount_unknown_mode():
    with pytest.raises(ValueError):
        allowance_amount('other', 1, 1, 1)


APRIL = (date(2026, 4, 1), date(2026, 4, 30))


@pytest.mark.parametrize(
    ('start', 'end', 'expected'),
    [
        (date(2026, 1, 1), None, 1.0),
        (date(2026, 4, 1), date(2026, 4, 30), 1.0),
        (date(2026, 4, 16), None, 0.5),  # 15 jours sur 30
        (date(2026, 1, 1), date(2026, 4, 15), 0.5),
        (date(2026, 4, 10), date(2026, 4, 12), 0.1),
        (date(2026, 5, 1), None, 0.0),
        (date(2026, 1, 1), date(2026, 3, 31), 0.0),
    ],
)
def test_validity_ratio(start, end, expected):
    assert validity_ratio(start, end, *APRIL) == pytest.approx(expected)


def test_validity_ratio_invalid_period():
    with pytest.raises(ValueError):
        validity_ratio(date(2026, 1, 1), None, date(2026, 4, 30), date(2026, 4, 1))
