import dataclasses
import math
from datetime import date
from types import MappingProxyType

import pytest
import yaml
from ga_fiscal_core.params import FiscalParams, _dated, load_from_yaml


def test_params_are_frozen(params_2026):
    with pytest.raises(dataclasses.FrozenInstanceError):
        params_2026.cnss_employee_rate = 0.1


def test_values_2026_after_lfr(params_2026):
    p = params_2026
    assert p.smig == 80_000
    assert (p.cnss_ceiling, p.cnss_employee_rate) == (1_500_000, 0.05)
    assert (p.cnss_employer_pf_rate, p.cnss_employer_at_rate, p.cnss_employer_avid_rate) == (0.05, 0.02, 0.11)
    assert p.social_transport_cap == 35_000
    assert (p.cnamgs_ceiling, p.cnamgs_employee_rate, p.cnamgs_employer_rate) == (2_500_000, 0.02, 0.041)
    assert (p.tcs_rate, p.tcs_monthly_exemption) == (0.05, 150_000)
    assert p.tcs_deduct_cnss is True and p.tcs_deduct_cnamgs is True
    assert (p.fp_rate, p.fp_annual_cap, p.max_children) == (0.20, 10_000_000, 6)
    assert (p.parts_single, p.parts_single_extra, p.parts_married) == (1, 1.5, 2)
    assert (p.parts_single_first_child, p.parts_single_per_extra_child, p.parts_married_per_child) == (1, 0.5, 0.5)
    assert (p.parts_disabled_child, p.forced_parts_min, p.forced_parts_max) == (0.5, 1, 6.5)
    assert p.irpp_min_withholding == 0
    assert (p.fnh_rate, p.fnh_ceiling, p.fnh_employee_share) == (0.03, 1_500_000, 0.0)
    assert (p.cfp_rate, p.cfp_ceiling, p.cfp_base) == (0.005, 1_500_000, 'social')
    assert p.bonus_annual_cap == 4_000_000
    assert p.vehicle_monthly_cap == 100_000
    assert (p.transport_daily_2_trips, p.transport_daily_4_trips) == (2_500, 5_000)
    assert p.family_monthly_per_child == 20_000
    assert p.isr_taxable_ratio_retirement == 0.5
    assert dict(p.benefit_rates) == {'housing': 0.06, 'domestic': 0.05, 'utilities': 0.05, 'food': 0.25}
    assert p.food_monthly_cap == 120_000
    assert p.cash_rounding == 500
    assert p.cash_denominations == (10_000, 5_000, 2_000, 1_000, 500)


def test_irpp_brackets_loaded_with_open_last_bracket(params_2026):
    brackets = params_2026.irpp_brackets
    assert len(brackets) == 8
    assert brackets[0] == (0, 1_500_000, 0.0, 0)
    assert brackets[-1][:2] == (11_000_001, math.inf)
    assert brackets[-1][2:] == (0.35, 1_669_000)


@pytest.mark.parametrize(
    ('on_date', 'cnss_rate', 'pf_rate', 'fnh_rate'),
    [
        (date(2025, 12, 31), 0.025, 0.08, 0.02),
        (date(2026, 1, 1), 0.05, 0.05, 0.02),
        (date(2026, 1, 31), 0.05, 0.05, 0.02),
        (date(2026, 7, 16), 0.05, 0.05, 0.02),
        (date(2026, 7, 17), 0.05, 0.05, 0.03),
        (date(2026, 7, 31), 0.05, 0.05, 0.03),
    ],
)
def test_dated_values_rg06(yaml_path, on_date, cnss_rate, pf_rate, fnh_rate):
    p = load_from_yaml(yaml_path, on_date)
    assert (p.cnss_employee_rate, p.cnss_employer_pf_rate, p.fnh_rate) == (cnss_rate, pf_rate, fnh_rate)


def test_tcs_exemption_history(yaml_path):
    node = yaml.safe_load(yaml_path.read_text(encoding='utf-8'))['tcs']['fraction_exoneree_mensuelle']
    assert _dated(node, date(2013, 12, 31), 'tcs') == 100_000
    assert _dated(node, date(2014, 1, 1), 'tcs') == 150_000
    assert _dated(42, date(1990, 1, 1), 'scalaire') == 42


def test_cfp_absent_before_2017(yaml_path):
    with pytest.raises(ValueError, match=r'cfp\.taux'):
        load_from_yaml(yaml_path, date(2016, 12, 31))


def test_options_override(yaml_path):
    p = load_from_yaml(yaml_path, date(2026, 9, 30), cash_rounding=0, cfp_base='gross', tcs_deduct_cnamgs=False)
    assert (p.cash_rounding, p.cfp_base, p.tcs_deduct_cnamgs) == (0, 'gross', False)


def test_no_value_before_first_date(yaml_path):
    with pytest.raises(ValueError, match='smig'):
        load_from_yaml(yaml_path, date(2000, 1, 1))


def test_invalid_cfp_base_rejected(params_2026):
    with pytest.raises(ValueError, match='cfp_base'):
        dataclasses.replace(params_2026, cfp_base='net')


def test_invalid_brackets_rejected(params_2026):
    with pytest.raises(ValueError, match='barème'):
        dataclasses.replace(params_2026, irpp_brackets=())


def test_fiscal_params_is_a_dataclass():
    assert dataclasses.is_dataclass(FiscalParams)


def test_incomplete_benefit_rates_rejected(params_2026):
    with pytest.raises(ValueError, match='avantages'):
        dataclasses.replace(params_2026, benefit_rates=MappingProxyType({'housing': 0.06}))
