"""Catalogue des rubriques (F6) et générateur des règles salariales (RG22, ADR-16, ADR-17)."""

import csv
import dataclasses
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(TOOLS))

import csv_to_salary_rules as gen  # noqa: E402
from ga_fiscal_core.engine import PayResult  # noqa: E402
from ga_fiscal_core.exemptions import SOCIAL_CAPS, TAX_CAPS  # noqa: E402
from ga_fiscal_core.labour import GAIN_VALUES  # noqa: E402
from ga_fiscal_core.params import BENEFIT_KINDS  # noqa: E402
from ga_fiscal_core.rounding import CASH_VALUES  # noqa: E402

ODOO_PATH = Path(os.environ.get('ODOO_PATH', '/home/ubuntu/odoo/odoo'))
SYSCOHADA_ACCOUNTS = ODOO_PATH / 'addons' / 'l10n_syscohada' / 'data' / 'template' / 'account.account-syscohada.csv'


@pytest.fixture(scope='module')
def rows():
    return gen.load_catalogue()


def _records(path, model):
    root = ET.parse(path).getroot()
    for record in root.iter('record'):
        if record.get('model') == model:
            yield record, {f.get('name'): f for f in record.findall('field')}


def _write_catalogue(tmp_path, mutate):
    with open(gen.CSV_PATH, encoding='utf-8', newline='') as stream:
        data = list(csv.DictReader(stream))
    mutate(data)
    path = tmp_path / 'catalogue.csv'
    with open(path, 'w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)
    return path


# --- catalogue -----------------------------------------------------------------------------


def test_catalogue_size(rows):
    assert 70 <= len(rows) <= 85


def test_codes_unique(rows):
    codes = [row['code'] for row in rows]
    assert len(codes) == len(set(codes))


def test_standard_rules_only_basic_gross_net(rows):
    standard = [row['code'] for row in rows if row['kind'] == 'standard']
    assert standard == ['BASIC', 'GROSS', 'NET']
    assert all(row['code'].startswith('GA_') for row in rows if row['kind'] != 'standard')


def test_every_rubric_has_treatment_and_source(rows):
    for row in rows:
        assert row['social_base'] and row['tax_base'], row['code']
        assert row['source'].strip(), row['code']


def test_cap_groups_known_by_core(rows):
    for row in rows:
        if row['social_cap_group']:
            assert row['social_cap_group'] in SOCIAL_CAPS, row['code']
        if row['tax_cap_group']:
            assert row['tax_cap_group'] in TAX_CAPS, row['code']


def test_loan_not_in_attachments(rows):
    (loan,) = [row for row in rows if row['code'] == 'GA_LOAN']
    assert loan['input_kind'] == 'monthly'


def test_housing_cash_allowance_fully_taxable(rows):
    (housing,) = [row for row in rows if row['code'] == 'GA_LOGT_ESP']
    assert (housing['tax_base'], housing['tax_cap_group']) == ('taxable', '')  # D-14


def test_benefits_in_kind_outside_net(rows):
    aik = [row for row in rows if row['category'] == 'GA_AIK']
    assert len(aik) == 4
    assert {row['core_value'] for row in aik} == {f'benefit:{kind}' for kind in BENEFIT_KINDS}  # D-18
    assert "categories['GA_AIK']" not in gen.STANDARD_FORMULAS['NET']
    assert "categories['GA_AIK']" in gen.STANDARD_FORMULAS['GROSS']


def test_target_accounts_exist_in_syscohada(rows):
    with open(SYSCOHADA_ACCOUNTS, encoding='utf-8', newline='') as stream:
        ids = {line['id'] for line in csv.DictReader(stream)}
    for row in rows:
        if row['account']:
            assert row['account'] in ids, row['code']


@pytest.mark.parametrize(
    ('mutate', 'message'),
    [
        (lambda d: d.append(dict(d[1])), 'double'),
        (lambda d: d[1].update(kind='bad'), 'kind'),
        (lambda d: d[1].update(kind='standard'), 'standard'),
        (lambda d: d[0].update(kind='input'), 'standard'),
        (lambda d: d[1].update(category='XXX'), 'catégorie'),
        (lambda d: d[1].update(sequence='x'), 'séquence'),
        (lambda d: d[1].update(input_kind=''), 'input_kind'),
        (lambda d: d[0].update(input_kind='monthly'), 'input_kind'),
        (lambda d: d[1].update(social_base='capped'), 'groupe'),
        (lambda d: d[1].update(tax_cap_group='NOPE', tax_base='capped'), 'inconnu'),
        (lambda d: d[1].update(prorate='oui'), 'booléen'),
        (lambda d: d[1].update(das_column='bad'), 'DAS'),
        (lambda d: d[1].update(source=' '), 'source'),
        (lambda d: d[1].update(code='SURSAL'), 'GA_'),
        (lambda d: d[1].update(account='6611'), 'compte'),
        (lambda d: [r.update(input_kind='attachment') for r in d if r['code'] == 'GA_LOAN'], 'GA_LOAN'),
        (lambda d: d.append({**d[1], 'code': 'NET'}), 'double'),
        (lambda d: [r.pop('source') for r in d], 'colonne'),
        (lambda d: d[1].update(core_value='net'), 'core_value'),
        (lambda d: [r.update(core_value='nope') for r in d if r['code'] == 'GA_IRPP'], 'core_value'),
        (lambda d: [r.update(core_value='benefit:car') for r in d if r['code'] == 'GA_AN_LOGT'], 'core_value'),
        (lambda d: [r.update(input_kind='monthly') for r in d if r['code'] == 'GA_IRPP'], 'input_kind'),
        (lambda d: [r.update(sequence='95') for r in d if r['code'] == 'GA_SURSAL'], 'avantages en nature'),
    ],
)
def test_invalid_catalogue_rejected(tmp_path, mutate, message):
    path = _write_catalogue(tmp_path, mutate)
    with pytest.raises(ValueError, match=message):
        gen.load_catalogue(path)


# --- génération ----------------------------------------------------------------------------


def test_versioned_files_up_to_date(rows):
    rules, inputs = gen.render(rows)
    assert gen.RULES_XML.read_text(encoding='utf-8') == rules
    assert gen.INPUTS_XML.read_text(encoding='utf-8') == inputs


def test_generation_idempotent(rows):
    assert gen.render(rows) == gen.render(rows)


def test_check_and_write_modes(tmp_path, monkeypatch):
    assert gen.main(['--check']) == 0
    monkeypatch.setattr(gen, 'RULES_XML', tmp_path / 'data' / 'rules.xml')
    monkeypatch.setattr(gen, 'INPUTS_XML', tmp_path / 'data' / 'inputs.xml')
    assert gen.main(['--check']) == 1
    assert gen.main([]) == 0
    assert gen.main(['--check']) == 0


def test_one_rule_per_rubric_single_net(rows):
    codes = [fields['code'].text for _, fields in _records(gen.RULES_XML, 'hr.salary.rule')]
    assert codes == [row['code'] for row in rows]
    assert codes.count('NET') == 1


def test_rules_attached_to_ga_structure_with_treatment(rows):
    for _, fields in _records(gen.RULES_XML, 'hr.salary.rule'):
        assert fields['struct_id'].get('ref') == 'structure_ga_employee'
        assert fields['l10n_ga_social_base'].text
        assert fields['l10n_ga_tax_base'].text


def test_no_numeric_literal_in_formulas():
    for _, fields in _records(gen.RULES_XML, 'hr.salary.rule'):
        for name in ('amount_python_compute', 'condition_python'):
            if name in fields:
                code = re.sub(r"'[^']*'", "''", fields[name].text)
                assert not re.search(r'(?<!\w)\d', code), code  # nombre littéral (pas l10n)


def test_input_rules_read_their_input(rows):
    by_code = {fields['code'].text: fields for _, fields in _records(gen.RULES_XML, 'hr.salary.rule')}
    assert by_code['GA_SURSAL']['amount_python_compute'].text.strip().startswith("result = inputs['GA_SURSAL'].amount")
    assert by_code['GA_LOAN']['amount_python_compute'].text.strip().startswith("result = -inputs['GA_LOAN'].amount")
    assert by_code['GA_SURSAL']['condition_python'].text.strip() == "result = 'GA_SURSAL' in inputs"


def test_core_rules_read_the_core_in_one_line(rows):
    by_code = {fields['code'].text: fields for _, fields in _records(gen.RULES_XML, 'hr.salary.rule')}
    core = [row for row in rows if row['kind'] == 'core']
    assert {row['code'] for row in core} >= {
        'GA_CNSS_SAL', 'GA_CNAMGS_SAL', 'GA_TCS', 'GA_IRPP', 'GA_IRPP_REGUL', 'GA_FNH_SAL',
        'GA_CNSS_PF', 'GA_CNSS_AT', 'GA_CNSS_AVID', 'GA_CNAMGS_PAT', 'GA_FNH', 'GA_CFP',
    }  # fmt: skip
    for row in core:
        call = f"payslip._l10n_ga_compute('{row['core_value']}', categories, result_rules)"
        sign = '-' if row['category'] in ('GA_SOC', 'GA_TAX') else ''
        assert by_code[row['code']]['amount_python_compute'].text == f'result = {sign}{call}', row['code']
        assert by_code[row['code']]['condition_python'].text == f'result = bool({call})', row['code']
        assert by_code[row['code']]['l10n_ga_core_value'].text == row['core_value'], row['code']
    assert 'GA_IRPP' not in {row['code'] for row in rows if row['kind'] == 'input'}


def test_core_values_are_payresult_fields(rows):
    fields = {f.name for f in dataclasses.fields(PayResult)}
    for row in rows:
        if row['kind'] == 'core' and not row['core_value'].startswith('benefit:'):
            assert row['core_value'] in fields | GAIN_VALUES | CASH_VALUES, row['code']


def test_labour_rubrics_computed(rows):
    by_code = {row['code']: row for row in rows}
    assert 'GA_HS' not in by_code  # remplacé par une rubrique par période (étape 2.4)
    expected = {
        'GA_ANC': 'seniority',
        'GA_CONGE': 'leave_allowance',
        'GA_HS_J': 'overtime:day',
        'GA_HS_N': 'overtime:night',
        'GA_HS_DIM': 'overtime:sunday',
        'GA_HS_FER': 'overtime:holiday',
    }
    for code, value in expected.items():
        assert (by_code[code]['kind'], by_code[code]['core_value'], by_code[code]['category']) == ('core', value, 'ALW')
    assert {row['core_value'] for row in rows if row['core_value'] in GAIN_VALUES} == GAIN_VALUES


def test_cash_rounding_rules_after_single_net(rows):
    """F2, D-44 : trois règles GA_CASH après le NET unique, sans traitement social ni fiscal."""
    by_code = {row['code']: row for row in rows}
    net_sequence = int(by_code['NET']['sequence'])
    expected = {'GA_ROUND_PREV': 'cash_prev', 'GA_ROUND': 'cash_adjust', 'GA_NET_PAY': 'cash_pay'}
    sequences = []
    for code, value in expected.items():
        row = by_code[code]
        assert (row['kind'], row['category'], row['core_value']) == ('core', 'GA_CASH', value)
        assert (row['social_base'], row['tax_base'], row['das_column']) == ('none', 'none', 'none')
        sequences.append(int(row['sequence']))
    assert net_sequence < sequences[0] < sequences[1] < sequences[2]
    assert {row['core_value'] for row in rows if row['category'] == 'GA_CASH'} == CASH_VALUES
    assert [row['code'] for row in rows if row['category'] == 'NET'] == ['NET']


def test_cash_gains_computed_before_benefits_in_kind(rows):
    first_aik = min(int(row['sequence']) for row in rows if row['category'] == 'GA_AIK')
    for row in rows:
        if row['social_base'] != 'none' and row['category'] != 'GA_AIK':
            assert int(row['sequence']) < first_aik, row['code']


def test_input_types(rows):
    types = {fields['code'].text: fields for _, fields in _records(gen.INPUTS_XML, 'hr.payslip.input.type')}
    assert set(types) == {row['code'] for row in rows if row['kind'] == 'input'}
    assert types['GA_LOAN']['available_in_attachments'].get('eval') == 'False'
    assert types['GA_SURSAL']['available_in_attachments'].get('eval') == 'True'  # ADR-16
    assert all(f['country_id'].get('ref') == 'base.ga' for f in types.values())
    # F15 : gains = indemnités, retenues (prêt, cessions, saisies) exclues
    assert types['GA_TRANSP']['l10n_ga_is_allowance'].get('eval') == 'True'
    assert types['GA_LOAN']['l10n_ga_is_allowance'].get('eval') == 'False'
    assert types['GA_GARNISH']['l10n_ga_is_allowance'].get('eval') == 'False'
