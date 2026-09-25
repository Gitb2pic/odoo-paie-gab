"""Salaire de base sur le mois de référence de 173,33 h (FIX 01, arrêté 016/MTEPS art. 5, base 05 §2)."""

import pytest
from ga_fiscal_core.basic import DEDUCT, PRORATA, basic_amount, basic_quantity, hourly_rate

H_REF = 173.33
WAGE = 130_000


def test_hourly_rate_is_wage_over_reference_hours():
    assert round(hourly_rate(WAGE, H_REF), 2) == 750.01
    with pytest.raises(ValueError):
        hourly_rate(WAGE, 0)


@pytest.mark.parametrize('planned', [184, 160])  # janvier 2025, février 2025 : même quantité
def test_full_month_is_reference_hours_and_exact_wage(planned):
    quantity = basic_quantity(H_REF, unpaid_hours=0, out_hours=0, planned_hours=planned)
    assert quantity == H_REF
    assert basic_amount(WAGE, H_REF, quantity) == WAGE  # pas de résidu d'arrondi


def test_unpaid_day_removes_its_hours():
    quantity = basic_quantity(H_REF, unpaid_hours=8, out_hours=0, planned_hours=184)
    assert quantity == pytest.approx(165.33)
    assert basic_amount(WAGE, H_REF, quantity) == 124_000


def test_quantity_never_negative():
    quantity = basic_quantity(H_REF, unpaid_hours=184, out_hours=0, planned_hours=184)
    assert quantity == 0
    assert basic_amount(WAGE, H_REF, quantity) == 0


def test_entry_during_month_deduct_and_prorata():
    # Entrée le 16/01/2025 : 11 jours ouvrés hors contrat (88 h) sur 184 h prévues.
    deducted = basic_quantity(H_REF, unpaid_hours=0, out_hours=88, planned_hours=184, method=DEDUCT)
    assert deducted == pytest.approx(85.33)
    prorated = basic_quantity(H_REF, unpaid_hours=0, out_hours=88, planned_hours=184, method=PRORATA)
    assert prorated == pytest.approx(H_REF * 96 / 184)
    assert basic_amount(WAGE, H_REF, prorated) == round(WAGE * 96 / 184)
    assert basic_quantity(H_REF, 0, 88, 0, method=PRORATA) == pytest.approx(85.33)  # sans heures prévues : (a)


def test_unknown_method_rejected():
    with pytest.raises(ValueError):
        basic_quantity(H_REF, 0, 0, 184, method='autre')
