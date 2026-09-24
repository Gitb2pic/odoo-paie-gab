import dataclasses
import itertools

import pytest
from ga_fiscal_core.tax import (
    irpp_monthly,
    irpp_regularisation,
    tax_one_part,
    tcs_amount,
    tcs_base,
)


def test_tcs_base_deducts_employee_contributions(params_2026):
    assert tcs_base(450_000, 27_750, 11_100, params_2026) == 411_150
    no_cnamgs = dataclasses.replace(params_2026, tcs_deduct_cnamgs=False)
    assert tcs_base(450_000, 27_750, 11_100, no_cnamgs) == 422_250  # point 09-3
    no_cnss = dataclasses.replace(params_2026, tcs_deduct_cnss=False)
    assert tcs_base(450_000, 27_750, 11_100, no_cnss) == 438_900


def test_tcs_amount(params_2026):
    assert tcs_amount(411_150, params_2026) == 13_058  # cas 590 000
    assert tcs_amount(790_500, params_2026) == 32_025  # exemple 2
    assert tcs_amount(150_000, params_2026) == 0
    assert tcs_amount(90_000, params_2026) == 0


def test_brackets_are_continuous(params_2026):
    brackets = params_2026.irpp_brackets
    for previous, current in itertools.pairwise(brackets):
        limit = current[0] - 1
        assert tax_one_part(limit, brackets) == pytest.approx(previous[2] * limit - previous[3])
        assert previous[2] * limit - previous[3] == pytest.approx(current[2] * limit - current[3])


@pytest.mark.parametrize(
    ('quotient', 'expected'),
    [(0, 0), (1_500_000, 0), (1_920_000, 21_000), (2_427_120, 71_712), (4_440_019, 402_003.8), (20_000_000, 5_331_000)],
)
def test_tax_one_part(params_2026, quotient, expected):
    assert tax_one_part(quotient, params_2026.irpp_brackets) == pytest.approx(expected)


def test_tax_one_part_rejects_negative(params_2026):
    with pytest.raises(ValueError, match='quotient'):
        tax_one_part(-1, params_2026.irpp_brackets)


def test_irpp_example_2(params_2026):
    detail = irpp_monthly(758_475, 3, params_2026)  # 790 500 − TCS 32 025
    assert detail.annual_base == 9_101_700
    assert detail.annual_net_taxable == pytest.approx(7_281_360)
    assert detail.quotient == pytest.approx(2_427_120)
    assert detail.monthly == 17_928


def test_irpp_abatement_cap_for_executive(params_2026):
    detail = irpp_monthly(4_166_667, 1, params_2026)
    assert detail.abatement == 10_000_000
    below = irpp_monthly(4_000_000, 1, params_2026)
    assert below.abatement == pytest.approx(9_600_000)


def test_irpp_negative_base_is_zero(params_2026):
    assert irpp_monthly(-5_000, 1, params_2026).monthly == 0


def test_irpp_min_withholding_f14(params_2026):
    small = irpp_monthly(160_000, 1, params_2026)
    assert small.monthly == 150  # Q = 1 536 000 → 1 800 par an
    with_threshold = dataclasses.replace(params_2026, irpp_min_withholding=1_000)
    assert irpp_monthly(160_000, 1, with_threshold).monthly == 0
    assert irpp_monthly(758_475, 3, with_threshold).monthly == 17_928


def test_irpp_rejects_invalid_parts(params_2026):
    with pytest.raises(ValueError, match='parts'):
        irpp_monthly(500_000, 0, params_2026)


def test_regularisation_departure_mid_year(params_2026):
    """Départ fin juin : l'impôt est recalculé sur le cumul réel de l'année."""
    base = 400_000
    monthly = irpp_monthly(base, 1, params_2026).monthly
    regul = irpp_regularisation(
        ytd_base=5 * base, month_base=base, ytd_withheld=5 * monthly, month_irpp=monthly, parts=1, p=params_2026
    )
    # cumul 2 400 000 − 20 % = 1 920 000 → 5 % × 1 920 000 − 75 000 = 21 000 dus sur l'année
    assert regul == 21_000 - 6 * monthly
    assert regul < 0  # trop retenu par l'annualisation : restitution


def test_regularisation_full_year_is_neutral(params_2026):
    base = 758_475
    monthly = irpp_monthly(base, 3, params_2026).monthly
    regul = irpp_regularisation(
        ytd_base=11 * base, month_base=base, ytd_withheld=11 * monthly, month_irpp=monthly, parts=3, p=params_2026
    )
    assert abs(regul) <= 6  # écart des arrondis mensuels seulement


def test_regularisation_irregular_bonus_retains_more(params_2026):
    base = 500_000
    monthly = irpp_monthly(base, 1, params_2026).monthly
    december = irpp_monthly(base + 3_000_000, 1, params_2026).monthly
    regul = irpp_regularisation(
        ytd_base=11 * base,
        month_base=base + 3_000_000,
        ytd_withheld=11 * monthly,
        month_irpp=december,
        parts=1,
        p=params_2026,
    )
    assert regul < 0  # l'annualisation du mois de prime a sur-retenu
