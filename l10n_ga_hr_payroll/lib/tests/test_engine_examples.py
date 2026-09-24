"""Cas chiffrés : fichier 04 §8 de la base, cas 590 000 (prompt 02, F16), jeux 06 §3."""

import dataclasses
from datetime import date

import pytest
from ga_fiscal_core.engine import PayslipFacts, compute
from ga_fiscal_core.exemptions import GainLine
from ga_fiscal_core.params import load_from_yaml

TRANSPORT_30K = GainLine('TRANSP', 30_000, 'TRANSPORT_35K', 'TRANSPORT_DAILY')
FULL_MONTH = {'presence_days': 22, 'transport_trips': 2}


def _check(result, expected):
    got = {key: getattr(result, key) for key in expected}
    assert got == expected


# 04 §8, au franc près
EXAMPLES = [
    (
        'Ex.1 célibataire, 545 000 dont transport 30 000',
        PayslipFacts(lines=(GainLine('BASIC', 515_000), TRANSPORT_30K), **FULL_MONTH),
        {
            'social_base': 515_000,
            'cnss_employee': 25_750,
            'cnamgs_employee': 10_300,
            'tcs_base': 478_950,
            'tcs': 16_448,
            'tax_parts': 1,
            'irpp': 33_500,
            'net': 459_002,
            'cnss_employer': 92_700,
            'cnamgs_employer': 21_115,
            'fnh': 15_450,
            'cfp': 2_575,
            'employer_cost': 676_840,
        },
    ),
    (
        'Ex.2 marié 2 enfants, 850 000',
        PayslipFacts(lines=(GainLine('BASIC', 850_000),), marital='married', children=2),
        {
            'social_base': 850_000,
            'cnss_employee': 42_500,
            'cnamgs_employee': 17_000,
            'tcs_base': 790_500,
            'tcs': 32_025,
            'tax_parts': 3,
            'irpp': 17_928,
            'net': 740_547,
            'cnss_employer': 153_000,
            'cnamgs_employer': 34_850,
            'fnh': 25_500,
            'cfp': 4_250,
            'employer_cost': 1_067_600,
        },
    ),
    (
        'Ex.3 célibataire 1 enfant, 2 000 000',
        PayslipFacts(lines=(GainLine('BASIC', 2_000_000),), children=1),
        {
            'social_base': 2_000_000,
            'cnss_employee': 75_000,
            'cnamgs_employee': 40_000,
            'tcs_base': 1_885_000,
            'tcs': 86_750,
            'tax_parts': 2,
            'irpp': 245_080,
            'net': 1_553_170,
            'cnss_employer': 270_000,
            'cnamgs_employer': 82_000,
            'fnh': 45_000,
            'cfp': 7_500,
            'employer_cost': 2_404_500,
        },
    ),
    (
        'Ex.4 marié 3 enfants, 5 000 000',
        PayslipFacts(lines=(GainLine('BASIC', 5_000_000),), marital='married', children=3),
        {
            'social_base': 5_000_000,
            'cnss_employee': 75_000,
            'cnamgs_employee': 50_000,
            'tcs_base': 4_875_000,
            'tcs': 236_250,
            'tax_parts': 3.5,
            'irpp': 845_104,
            'net': 3_793_646,
            'cnss_employer': 270_000,
            'cnamgs_employer': 102_500,
            'fnh': 45_000,
            'cfp': 7_500,
            'employer_cost': 5_425_000,
        },
    ),
]


@pytest.mark.parametrize(('title', 'facts', 'expected'), EXAMPLES, ids=[e[0] for e in EXAMPLES])
def test_reference_examples(params_2026, title, facts, expected):
    _check(compute(facts, params_2026), expected)


def test_example_annual_values(params_2026):
    result = compute(EXAMPLES[1][1], params_2026)
    assert round(result.annual_net_taxable) == 7_281_360
    assert round(result.quotient) == 2_427_120
    ex4 = compute(EXAMPLES[3][1], params_2026)
    assert round(ex4.annual_net_taxable) == 45_665_000  # abattement plafonné à 10 000 000


F16_LINES = (
    GainLine('BASIC', 450_000),
    GainLine('TRANSP', 35_000, 'TRANSPORT_35K', 'TRANSPORT_DAILY'),
    GainLine('RESP', 105_000, None, 'EXEMPT'),
)


def test_case_590000_net_514897(params_2026):
    result = compute(PayslipFacts(lines=F16_LINES, **FULL_MONTH), params_2026)
    _check(
        result,
        {
            'gains': 590_000,
            'social_base': 555_000,
            'taxable_gross': 450_000,
            'cnss_employee': 27_750,
            'cnamgs_employee': 11_100,
            'tcs': 13_058,
            'irpp': 23_195,
            'net': 514_897,
            'cnss_employer': 99_900,
            'cnamgs_employer': 22_755,
            'fnh': 16_650,
            'cfp': 2_775,
        },
    )
    by_code = {line.code: line for line in result.lines}
    assert (by_code['TRANSP'].social_excluded, by_code['TRANSP'].tax_exempt) == (35_000, 35_000)
    assert (by_code['RESP'].social_excluded, by_code['RESP'].tax_exempt) == (0, 105_000)


def test_case_590000_all_taxable_net_486617(params_2026):
    lines = tuple(dataclasses.replace(line, forced_taxable=True) for line in F16_LINES)
    result = compute(PayslipFacts(lines=lines, **FULL_MONTH), params_2026)
    assert (result.social_base, result.taxable_gross, result.net) == (555_000, 590_000, 486_617)


# Jeux prioritaires, fichier 06 §3


def test_single_below_tcs_threshold(params_2026):
    result = compute(PayslipFacts(lines=(GainLine('BASIC', 150_000),)), params_2026)
    assert (result.tcs, result.irpp) == (0, 0)
    assert result.net == 150_000 - 7_500 - 3_000


def test_married_three_children_at_cnss_ceiling(params_2026):
    result = compute(
        PayslipFacts(lines=(GainLine('BASIC', 1_500_000),), marital='married', children=3),
        params_2026,
    )
    assert (result.cnss_employee, result.cnss_employer, result.tax_parts) == (75_000, 270_000, 3.5)
    above = compute(PayslipFacts(lines=(GainLine('BASIC', 1_800_000),), marital='married', children=3), params_2026)
    assert above.cnss_employee == 75_000
    assert above.cnamgs_employee == 36_000  # plafond CNAMGS distinct (2 500 000)


def test_executive_at_abatement_cap(params_2026):
    result = compute(PayslipFacts(lines=(GainLine('BASIC', 4_600_000),)), params_2026)
    assert result.irpp_base_monthly >= 4_166_667
    assert result.abatement == 10_000_000


def test_hired_on_15th_smig_floor(params_2026):
    result = compute(PayslipFacts(lines=(GainLine('BASIC', 30_000),), presence_ratio=0.5), params_2026)
    assert result.social_base == 40_000  # SMIG 80 000 × 0,5
    assert result.cnss_employee == 2_000
    assert result.tcs == 0 and result.irpp == 0


def test_thirteenth_month_over_4m(params_2026):
    lines = (GainLine('BASIC', 1_000_000), GainLine('13M', 5_000_000, None, 'BONUS_4M'))
    first = compute(PayslipFacts(lines=lines), params_2026)
    assert first.bonus_exempted == 4_000_000
    assert first.taxable_gross == 2_000_000
    later = compute(PayslipFacts(lines=lines, ytd_bonus_exempted=3_000_000), params_2026)
    assert later.bonus_exempted == 1_000_000
    assert later.taxable_gross == 5_000_000
    assert first.social_base == later.social_base == 6_000_000  # gratification cotisable


def test_rate_change_1st_january_2026(yaml_path):
    facts = PayslipFacts(lines=(GainLine('BASIC', 850_000),), marital='married', children=2)
    december = compute(facts, load_from_yaml(yaml_path, date(2025, 12, 31)))
    january = compute(facts, load_from_yaml(yaml_path, date(2026, 1, 31)))
    assert (december.cnss_employee, january.cnss_employee) == (21_250, 42_500)
    assert (december.cnss_employer, january.cnss_employer) == (136_000, 153_000)
    assert december.fnh == january.fnh == 17_000  # FNH encore à 2 %


def test_fnh_change_17_july_2026(yaml_path):
    facts = PayslipFacts(lines=(GainLine('BASIC', 850_000),), marital='married', children=2)
    before = compute(facts, load_from_yaml(yaml_path, date(2026, 7, 16)))
    july = compute(facts, load_from_yaml(yaml_path, date(2026, 7, 31)))  # D-06 : lecture à date_to
    assert (before.fnh, july.fnh) == (17_000, 25_500)
    assert before.net == july.net  # FNH 100 % employeur


def test_departure_with_regularisation(params_2026):
    base_facts = PayslipFacts(lines=(GainLine('BASIC', 450_000),))
    monthly = compute(base_facts, params_2026)
    departure = dataclasses.replace(
        base_facts,
        regularize=True,
        ytd_irpp_base=5 * monthly.irpp_base_monthly,
        ytd_irpp_withheld=5 * monthly.irpp,
    )
    result = compute(departure, params_2026)
    assert result.irpp == monthly.irpp
    assert result.irpp_regularisation < 0  # six mois réels : trop retenu par l'annualisation
    assert result.net == monthly.net - result.irpp_regularisation


def test_regularisation_off_by_default(params_2026):
    assert compute(PayslipFacts(lines=(GainLine('BASIC', 450_000),)), params_2026).irpp_regularisation == 0


def test_benefits_in_kind_enter_bases_but_not_cash(params_2026):
    facts = PayslipFacts(lines=(GainLine('BASIC', 1_000_000),), benefits=('housing', 'food'), main_salary=1_000_000)
    result = compute(facts, params_2026)
    assert result.benefits_in_kind == 55_800 + 120_000
    assert result.gains == 1_175_800
    assert result.social_base == 1_175_800
    assert result.net == result.gains - result.benefits_in_kind - result.total_employee_deductions


def test_fnh_employee_share_and_cfp_gross_options(params_2026):
    options = dataclasses.replace(params_2026, fnh_employee_share=0.5, cfp_base='gross')
    result = compute(PayslipFacts(lines=F16_LINES, **FULL_MONTH), options)
    assert (result.fnh, result.fnh_employee) == (8_325, 8_325)
    assert result.cfp == 2_950  # 0,5 % × 590 000
    assert result.net == 514_897 - 8_325


def test_employer_cost_consistency(params_2026):
    result = compute(PayslipFacts(lines=F16_LINES, **FULL_MONTH), params_2026)
    assert result.employer_charges == result.cnss_employer + result.cnamgs_employer + result.fnh + result.cfp
    assert result.employer_cost == result.gains + result.employer_charges
