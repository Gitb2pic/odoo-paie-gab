"""Générateur des paramètres datés (règle d'or 1, RG06, F14, sprint 0 point 11)."""

import ast
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import date
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import yaml_to_rule_parameters as gen  # noqa: E402
from ga_fiscal_core.param_codes import params_from_values  # noqa: E402
from ga_fiscal_core.params import load_from_yaml  # noqa: E402


@pytest.fixture(scope='module')
def data():
    return gen.load_yaml()


@pytest.fixture(scope='module')
def parsed():
    """{code: [(date_from, valeur), ...]} lu dans le fichier versionné."""
    root = ET.parse(gen.XML_PATH).getroot()
    codes = {}
    values = defaultdict(list)
    for record in root.iter('record'):
        fields = {f.get('name'): f for f in record.findall('field')}
        if record.get('model') == 'hr.rule.parameter':
            codes[record.get('id')] = fields['code'].text
        else:
            code = codes[fields['rule_parameter_id'].get('ref')]
            day = date.fromisoformat(fields['date_from'].text)
            values[code].append((day, ast.literal_eval(fields['parameter_value'].text)))
    return values


def _at(parsed, on_date):
    return {code: max(v for v in rows if v[0] <= on_date)[1] for code, rows in parsed.items()}


def test_versioned_file_is_up_to_date(data):
    assert gen.XML_PATH.read_text(encoding='utf-8') == gen.render(data)


def test_generation_is_idempotent(data):
    assert gen.render(data) == gen.render(data)


def test_check_mode(tmp_path, monkeypatch, data):
    assert gen.main(['--check']) == 0
    stale = tmp_path / 'stale.xml'
    stale.write_text('<odoo/>', encoding='utf-8')
    monkeypatch.setattr(gen, 'XML_PATH', stale)
    assert gen.main(['--check']) == 1
    missing = tmp_path / 'missing.xml'
    monkeypatch.setattr(gen, 'XML_PATH', missing)
    assert gen.main(['--check']) == 1


def test_write_mode(tmp_path, monkeypatch, data):
    target = tmp_path / 'data' / 'out.xml'
    monkeypatch.setattr(gen, 'XML_PATH', target)
    assert gen.main([]) == 0
    assert target.read_text(encoding='utf-8') == gen.render(data)


def test_codes_prefixed_unique_and_country(parsed):
    root = ET.parse(gen.XML_PATH).getroot()
    params = [r for r in root.iter('record') if r.get('model') == 'hr.rule.parameter']
    codes = [r.find("field[@name='code']").text for r in params]
    assert len(codes) == len(set(codes))
    assert all(c.startswith('l10n_ga_') for c in codes)
    assert all(r.find("field[@name='country_id']").get('ref') == 'base.ga' for r in params)


def test_one_value_per_effective_date(parsed):
    assert parsed['l10n_ga_cnss_employee_rate'] == [(date(2000, 1, 1), 0.025), (date(2026, 1, 1), 0.05)]
    assert parsed['l10n_ga_fnh_rate'] == [(date(2000, 1, 1), 0.02), (date(2026, 7, 17), 0.03)]
    assert [d for d, _ in parsed['l10n_ga_tcs_exemption']] == [date(2010, 1, 1), date(2014, 1, 1)]


def test_f14_min_withholding_is_zero(parsed):
    assert parsed['l10n_ga_irpp_min_withholding'] == [(date(2000, 1, 1), 0)]


def test_values_are_python_literals_without_inf():
    root = ET.parse(gen.XML_PATH).getroot()
    for field in root.iter('field'):
        if field.get('name') == 'parameter_value':
            assert 'inf' not in field.text
            ast.literal_eval(field.text)


@pytest.mark.parametrize('on_date', [date(2025, 12, 31), date(2026, 1, 1), date(2026, 7, 16), date(2026, 7, 17)])
def test_parity_generated_values_vs_yaml_loader(parsed, on_date):
    """Les valeurs installées reconstruisent exactement les FiscalParams du chargeur de test."""
    assert params_from_values(_at(parsed, on_date), cash_rounding=500) == load_from_yaml(gen.YAML_PATH, on_date)
