import pytest
from ga_fiscal_core.benefits import benefit_amount, benefit_code, benefits_base


def test_benefits_base_is_cash_minus_employee_contributions(params_2026):
    # D-11 : 1 000 000 − CNSS 50 000 − CNAMGS 20 000
    assert benefits_base(1_000_000, params_2026) == 930_000
    # plafonds CNSS / CNAMGS appliqués aux cotisations déduites
    assert benefits_base(3_000_000, params_2026) == 3_000_000 - 75_000 - 50_000


@pytest.mark.parametrize(
    ('kind', 'expected'),
    [('housing', 55_800), ('domestic', 46_500), ('utilities', 46_500)],
)
def test_rates_on_base(params_2026, kind, expected):
    assert benefit_amount(kind, 930_000, 800_000, params_2026) == expected


def test_food_on_main_salary_with_cap(params_2026):
    assert benefit_amount('food', 930_000, 300_000, params_2026) == 75_000  # 25 % du salaire principal
    assert benefit_amount('food', 930_000, 800_000, params_2026) == 120_000  # plafond mensuel


def test_unknown_benefit(params_2026):
    with pytest.raises(ValueError, match='vehicle'):
        benefit_amount('vehicle', 930_000, 800_000, params_2026)


def test_benefit_code_names_the_core_line():
    assert benefit_code('housing') == 'AN_HOUSING'
    assert benefit_code('food') == 'AN_FOOD'
