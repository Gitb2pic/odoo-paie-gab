"""Recette C5 de l'étape 2.2 : cas F16 (590 000 → net 514 897) rejoué avec les DONNÉES GÉNÉRÉES.

Les paramètres viennent de ``data/hr_rule_parameters_data.xml`` et le traitement des lignes
du catalogue ``data/catalogue_rubriques_ga.csv`` (via ``treatment.social_group`` /
``tax_group``) : le noyau, le catalogue et les paramètres installés sont cohérents entre eux.
"""

import sys
from datetime import date
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import csv_to_salary_rules as rules_gen  # noqa: E402
import yaml_to_rule_parameters as params_gen  # noqa: E402
from ga_fiscal_core import GainLine, PayslipFacts, compute  # noqa: E402
from ga_fiscal_core.param_codes import params_from_values  # noqa: E402
from ga_fiscal_core.treatment import social_group, tax_group  # noqa: E402


@pytest.fixture(scope='module')
def params():
    return params_from_values(params_gen.values_at(params_gen.read_generated(), date(2026, 9, 30)), cash_rounding=500)


@pytest.fixture(scope='module')
def catalogue():
    return {row['code']: row for row in rules_gen.load_catalogue()}


def _line(catalogue, code, amount, **extra):
    row = catalogue[code]
    return GainLine(
        code,
        amount,
        social_group(row['social_base'], row['social_cap_group'] or None),
        tax_group(row['tax_base'], row['tax_cap_group'] or None),
        **extra,
    )


def _facts(catalogue, forced=False):
    lines = (
        _line(catalogue, 'BASIC', 450_000, forced_taxable=forced),
        _line(catalogue, 'GA_TRANSP', 35_000, forced_taxable=forced),
        _line(catalogue, 'GA_RESP', 105_000, forced_taxable=forced),
    )
    return PayslipFacts(lines=lines, presence_days=22, transport_trips=2)


def test_f16_net_514897_with_generated_data(params, catalogue):
    result = compute(_facts(catalogue), params)
    assert (result.gains, result.social_base, result.taxable_gross) == (590_000, 555_000, 450_000)
    assert (result.cnss_employee, result.cnamgs_employee, result.tcs, result.irpp) == (27_750, 11_100, 13_058, 23_195)
    assert result.net == 514_897
    assert (result.cnamgs_employer, result.fnh, result.cfp) == (22_755, 16_650, 2_775)
    assert result.cnss_employer_pf + result.cnss_employer_at + result.cnss_employer_avid == 99_900


def test_f16_all_taxable_net_486617_with_generated_data(params, catalogue):
    result = compute(_facts(catalogue, forced=True), params)
    assert (result.social_base, result.taxable_gross, result.net) == (555_000, 590_000, 486_617)
