"""Droit du travail : ancienneté, heures supplémentaires, allocation de congé (base 05 §2-5)."""

from datetime import date

import pytest
from ga_fiscal_core.labour import completed_years, leave_allowance, overtime_amount, seniority_rate

# Tronc commun des conventions (base 05 §4) : 2 % à 2 ans, +1 % par an.
COMMON = {'start_years': 2, 'start_rate': 0.02, 'step_rate': 0.01}


@pytest.mark.parametrize(
    ('start', 'on', 'expected'),
    [
        (date(2020, 3, 15), date(2026, 3, 14), 5),
        (date(2020, 3, 15), date(2026, 3, 15), 6),
        (date(2026, 1, 1), date(2026, 12, 31), 0),
        (date(2024, 2, 29), date(2026, 2, 28), 1),
        (date(2026, 5, 1), date(2026, 4, 30), 0),  # date d'ancienneté future
        (None, date(2026, 4, 30), 0),
    ],
)
def test_completed_years(start, on, expected):
    assert completed_years(start, on) == expected


@pytest.mark.parametrize(
    ('years', 'max_rate', 'expected'),
    [
        (0, 0.15, 0),
        (1, 0.15, 0),
        (2, 0.15, 0.02),
        (3, 0.15, 0.03),
        (10, 0.15, 0.10),
        (30, 0.15, 0.15),  # plafond
        (30, 0, 0.30),  # 0 = pas de plafond
    ],
)
def test_seniority_rate(years, max_rate, expected):
    assert seniority_rate(years, max_rate=max_rate, **COMMON) == pytest.approx(expected)


def test_seniority_rate_rejects_negative_settings():
    with pytest.raises(ValueError, match='ancienneté'):
        seniority_rate(5, start_years=2, start_rate=-0.01, step_rate=0.01, max_rate=0)


TRANCHES = ((0, 8, 0.10), (8, 16, 0.25), (16, None, 0.50))


@pytest.mark.parametrize(
    ('hours', 'expected'),
    [
        (0, 0),
        (5, 5 * 1000 * 1.10),
        (8, 8 * 1000 * 1.10),
        (12, 8 * 1000 * 1.10 + 4 * 1000 * 1.25),
        (20, 8 * 1000 * 1.10 + 8 * 1000 * 1.25 + 4 * 1000 * 1.50),
    ],
)
def test_overtime_by_tranche(hours, expected):
    assert overtime_amount(1000, hours, TRANCHES) == round(expected)


def test_overtime_rounded_once_to_the_franc():
    assert overtime_amount(461.547, 3, ((0, None, 0.25),)) == 1731  # 1730,80…


@pytest.mark.parametrize('tranches', [(), ((0, 8, 0.10),), ((2, None, 0.10),)])
def test_overtime_hours_not_covered_rejected(tranches):
    with pytest.raises(ValueError, match='majoration'):
        overtime_amount(1000, 10, tranches)


def test_overtime_without_hours_needs_no_rate():
    assert overtime_amount(1000, 0, ()) == 0


def test_leave_allowance_twelfth_more_favourable():
    # 3 600 000 sur 12 mois × 1/12 × 12 jours / 24 jours = 150 000 > maintien 120 000
    assert leave_allowance(
        maintained=120_000, reference_pay=3_600_000, ratio=1 / 12, days_taken=12, annual_days=24
    ) == (150_000)


def test_leave_allowance_maintained_salary_more_favourable():
    assert leave_allowance(
        maintained=160_000, reference_pay=3_600_000, ratio=1 / 12, days_taken=12, annual_days=24
    ) == (160_000)


def test_leave_allowance_minor_ratio():
    # 1 200 000 × 5/48 × 30 / 30
    assert (
        leave_allowance(maintained=0, reference_pay=1_200_000, ratio=5 / 48, days_taken=30, annual_days=30) == 125_000
    )


def test_leave_allowance_zero_days():
    assert leave_allowance(maintained=0, reference_pay=3_600_000, ratio=1 / 12, days_taken=0, annual_days=24) == 0


def test_leave_allowance_requires_annual_days():
    with pytest.raises(ValueError, match='jours'):
        leave_allowance(maintained=0, reference_pay=1, ratio=1 / 12, days_taken=1, annual_days=0)
