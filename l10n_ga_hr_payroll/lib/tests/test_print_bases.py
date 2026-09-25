"""Base et taux imprimés (plan 2.7 b) : cas 590 000 (F16), plafonds, option CFP."""

import dataclasses

import pytest
from ga_fiscal_core.engine import PayslipFacts, compute
from ga_fiscal_core.exemptions import GainLine
from ga_fiscal_core.print_bases import print_bases
from ga_fiscal_core.rounding import round_fcfa

F16_LINES = (
    GainLine('BASIC', 450_000),
    GainLine('TRANSP', 35_000, 'TRANSPORT_35K', 'TRANSPORT_DAILY'),
    GainLine('RESP', 105_000, None, 'EXEMPT'),
)
FULL_MONTH = {'main_salary': 450_000, 'presence_days': 22, 'transport_trips': 2}


@pytest.fixture
def f16(params_2026):
    return compute(PayslipFacts(lines=F16_LINES, **FULL_MONTH), params_2026)


def test_bases_and_rates_reproduce_amounts(f16, params_2026):
    bases = print_bases(f16, params_2026)
    for value in ('cnss_employee', 'cnamgs_employee', 'cnamgs_employer', 'fnh', 'cfp'):
        base, rate = bases[value]
        assert round_fcfa(base * rate / 100) == getattr(f16, value), value
    employer = sum(bases[v][1] for v in ('cnss_employer_pf', 'cnss_employer_at', 'cnss_employer_avid'))
    assert round_fcfa(bases['cnss_employee'][0] * employer / 100) == f16.cnss_employer
    assert bases['cnss_employee'][0] == 555_000
    assert bases['tcs'] == (f16.tcs_base, params_2026.tcs_rate * 100)
    assert bases['irpp'] == (f16.irpp_base_monthly, None)
    assert bases['irpp_regularisation'] == (None, None)
    assert bases['fnh_employee'][1] + bases['fnh'][1] == pytest.approx(params_2026.fnh_rate * 100)


def test_ceilings_apply(params_2026):
    lines = (GainLine('BASIC', 5_000_000),)
    result = compute(PayslipFacts(lines=lines, main_salary=5_000_000, presence_days=22), params_2026)
    bases = print_bases(result, params_2026)
    assert bases['cnss_employee'][0] == params_2026.cnss_ceiling
    assert bases['cnamgs_employee'][0] == params_2026.cnamgs_ceiling
    assert bases['fnh'][0] == min(result.social_base, params_2026.fnh_ceiling)


def test_cfp_on_gross_option(f16, params_2026):
    gross = dataclasses.replace(params_2026, cfp_base='gross')
    assert print_bases(f16, gross)['cfp'][0] == min(f16.gains, params_2026.cfp_ceiling)
    assert print_bases(f16, params_2026)['cfp'][0] == min(f16.social_base, params_2026.cfp_ceiling)
