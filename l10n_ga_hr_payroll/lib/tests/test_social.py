from datetime import date

import pytest
from ga_fiscal_core.params import load_from_yaml
from ga_fiscal_core.social import social_base, social_contributions


def test_social_base_floor_is_smig_times_presence(params_2026):
    assert social_base(555_000, 1.0, params_2026) == 555_000
    assert social_base(60_000, 1.0, params_2026) == 80_000  # décret 599 art. 34
    assert social_base(30_000, 0.5, params_2026) == 40_000  # entrée le 15 : SMIG proratisé
    assert social_base(0, 0.0, params_2026) == 0


def test_social_base_rejects_invalid_presence(params_2026):
    with pytest.raises(ValueError, match='présence'):
        social_base(100_000, 1.5, params_2026)


def test_contributions_f16_case(params_2026):
    c = social_contributions(555_000, params_2026)
    assert (c.cnss_employee, c.cnamgs_employee) == (27_750, 11_100)
    assert c.cnss_employer_pf + c.cnss_employer_at + c.cnss_employer_avid == 99_900
    assert (c.cnss_employer_pf, c.cnss_employer_at, c.cnss_employer_avid) == (27_750, 11_100, 61_050)
    assert c.cnamgs_employer == 22_755
    assert c.cnss_employer == 99_900


def test_contributions_ceilings(params_2026):
    c = social_contributions(5_000_000, params_2026)
    assert c.cnss_employee == 75_000  # plafond CNSS 1 500 000
    assert c.cnamgs_employee == 50_000  # plafond CNAMGS 2 500 000
    assert c.cnss_employer == 270_000
    assert c.cnamgs_employer == 102_500


def test_contributions_before_reform(yaml_path):
    p2025 = load_from_yaml(yaml_path, date(2025, 12, 31))
    c = social_contributions(1_000_000, p2025)
    assert c.cnss_employee == 25_000  # 2,5 %
    assert (c.cnss_employer_pf, c.cnss_employer_at, c.cnss_employer_avid) == (80_000, 30_000, 50_000)
