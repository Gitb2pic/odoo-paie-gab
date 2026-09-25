#!/usr/bin/env python3
"""Génère les règles salariales et les types d'entrée depuis ``data/catalogue_rubriques_ga.csv`` (F6).

Genres : `standard` (BASIC, GROSS, NET), `input` (lue sur une entrée de bulletin), `core`
(calculée par le noyau en une ligne : `payslip._l10n_ga_compute(<core_value>, ...)`).

Sorties (ne pas modifier à la main) :
- ``l10n_ga_hr_payroll/data/hr_salary_rule_data.xml`` : une règle par rubrique, structure
  « Gabon — Employé », traitement social / fiscal porté par les champs ``l10n_ga_*`` (ADR-17) ;
- ``l10n_ga_hr_payroll/data/hr_payslip_input_type_data.xml`` : un type d'entrée par rubrique
  lue sur entrée ; ``available_in_attachments`` pour les indemnités contractuelles (ADR-16),
  jamais pour ``GA_LOAN`` (sprint 0 point 6).

Le catalogue est validé avant génération (codes uniques — RG22 —, traitement cohérent et
groupes connus du noyau, source citée). Aucune formule ne contient de nombre (règle d'or 1).

Usage :
    tools/csv_to_salary_rules.py           # écrit les fichiers
    tools/csv_to_salary_rules.py --check   # code 1 si un fichier versionné diffère
"""

import argparse
import csv
import dataclasses
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'l10n_ga_hr_payroll' / 'lib'))

from ga_fiscal_core.engine import PayResult  # noqa: E402
from ga_fiscal_core.labour import GAIN_VALUES  # noqa: E402
from ga_fiscal_core.params import BENEFIT_KINDS  # noqa: E402
from ga_fiscal_core.print_layout import CONTRIBUTIONS, GAINS, VIRTUAL_CODES, section  # noqa: E402
from ga_fiscal_core.rounding import CASH_VALUES  # noqa: E402
from ga_fiscal_core.treatment import DAS_COLUMNS, check_treatment  # noqa: E402

MODULE = REPO / 'l10n_ga_hr_payroll'
CSV_PATH = MODULE / 'data' / 'catalogue_rubriques_ga.csv'
RULES_XML = MODULE / 'data' / 'hr_salary_rule_data.xml'
INPUTS_XML = MODULE / 'data' / 'hr_payslip_input_type_data.xml'

COLUMNS = (
    'code',
    'name',
    'kind',
    'category',
    'sequence',
    'input_kind',
    'core_value',
    'social_base',
    'social_cap_group',
    'tax_base',
    'tax_cap_group',
    'prorate',
    'leave_base',
    'severance_base',
    'das_column',
    'das_exempt_column',
    'account',
    'print_code',
    'print_name',
    'source',
)
CATEGORIES = {
    'BASIC': 'hr_payroll.BASIC',
    'ALW': 'hr_payroll.ALW',
    'GROSS': 'hr_payroll.GROSS',
    'DED': 'hr_payroll.DED',
    'NET': 'hr_payroll.NET',
    'GA_AIK': 'category_ga_aik',
    'GA_SOC': 'category_ga_soc',
    'GA_TAX': 'category_ga_tax',
    'GA_EMPLOYER': 'category_ga_employer',
    'GA_CASH': 'category_ga_cash',
}
# Catégories filles de DED : montant négatif (retenue).
DEDUCTION_CATEGORIES = ('DED', 'GA_SOC', 'GA_TAX')
# Rubriques calculées par le noyau (genre « core ») : attribut de PayResult, ou avantage en
# nature « benefit:<nature> » valorisé par le noyau (art. 93, décision D-18), ou gain calculé
# avant le PayResult (ancienneté, heures sup., allocation de congé : GAIN_VALUES, étape 2.4), ou
# arrondi espèces après le NET (CASH_VALUES, F2, étape 2.6).
CORE_VALUES = frozenset(
    {f.name for f in dataclasses.fields(PayResult)}
    | {f'benefit:{kind}' for kind in BENEFIT_KINDS}
    | GAIN_VALUES
    | CASH_VALUES
)
KINDS = ('standard', 'input', 'core')
# Règles standard conformes à hr_payroll (E/hr_payroll/data/hr_salary_rule_data.xml:10-123) ;
# le brut Gabon ajoute les avantages en nature, le net unique ne les contient pas (non versés).
STANDARD_FORMULAS = {
    'BASIC': 'result = payslip.paid_amount',
    'GROSS': "result = categories['BASIC'] + categories['ALW'] + categories['GA_AIK']",
    'NET': "result = categories['BASIC'] + categories['ALW'] + categories['DED']",
}
INPUT_KINDS = ('attachment', 'monthly')
BOOLEANS = {'0': False, '1': True}
HEADER = """<?xml version="1.0" encoding="utf-8"?>
<!--
    FICHIER GÉNÉRÉ par tools/csv_to_salary_rules.py depuis data/catalogue_rubriques_ga.csv :
    ne pas modifier à la main (modifier le catalogue puis relancer le générateur).
-->
<odoo>
    <data noupdate="0">
"""
FOOTER = """    </data>
</odoo>
"""


def _fail(row, message):
    raise ValueError(f'{row.get("code") or "?"} : {message}')


def _check_kind(row):
    code = row['code']
    if row['kind'] not in KINDS:
        _fail(row, f'kind invalide {row["kind"]!r}')
    if (row['kind'] == 'standard') != (code in STANDARD_FORMULAS):
        _fail(row, 'seules BASIC, GROSS et NET sont des règles standard, et elles doivent l’être')
    if row['kind'] != 'standard' and not code.startswith('GA_'):
        _fail(row, 'le code d’une rubrique Gabon commence par GA_')
    if row['category'] not in CATEGORIES:
        _fail(row, f'catégorie inconnue {row["category"]!r}')
    if not row['sequence'].isdigit():
        _fail(row, f'séquence invalide {row["sequence"]!r}')
    expected_kinds = INPUT_KINDS if row['kind'] == 'input' else ('',)
    if row['input_kind'] not in expected_kinds:
        _fail(row, f'input_kind invalide {row["input_kind"]!r}')
    if code == 'GA_LOAN' and row['input_kind'] != 'monthly':
        _fail(row, 'GA_LOAN ne doit jamais être disponible dans les ajustements (sprint 0 point 6)')
    if row['kind'] == 'core' and row['core_value'] not in CORE_VALUES:
        _fail(row, f'core_value inconnue du noyau {row["core_value"]!r}')
    if row['kind'] != 'core' and row['core_value']:
        _fail(row, 'core_value réservée aux rubriques calculées par le noyau')
    if row['core_value'].startswith('benefit:') != (row['category'] == 'GA_AIK'):
        _fail(row, 'core_value benefit:<nature> réservée aux avantages en nature (GA_AIK)')


def _check_row(row):
    _check_kind(row)
    code = row['code']
    check_treatment(code, row['social_base'], row['social_cap_group'], row['tax_base'], row['tax_cap_group'])
    for flag in ('prorate', 'leave_base', 'severance_base'):
        if row[flag] not in BOOLEANS:
            _fail(row, f'{flag} doit être un booléen 0 / 1')
    for column in ('das_column', 'das_exempt_column'):
        if row[column] not in DAS_COLUMNS:
            _fail(row, f'colonne DAS inconnue {row[column]!r}')
    if row['account'] and not re.fullmatch(r'pcg_\d+', row['account']):
        _fail(row, f'compte cible invalide {row["account"]!r} (attendu pcg_<code>)')
    if not row['source'].strip():
        _fail(row, 'source obligatoire (F6)')


def load_catalogue(path=CSV_PATH):
    """Lit et valide le catalogue ; retourne la liste des lignes (dict) dans l'ordre du fichier."""
    # utf-8-sig : le catalogue porte un BOM pour qu'Excel affiche les accents ; accepté sans BOM aussi.
    with open(path, encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        missing = set(COLUMNS) - set(reader.fieldnames or ())
        if missing:
            raise ValueError(f'catalogue : colonne(s) absente(s) {sorted(missing)}')
        rows = [dict(row) for row in reader]
    seen = set()
    for row in rows:
        if row['code'] in seen:
            _fail(row, 'code en double dans la structure (RG22)')
        seen.add(row['code'])
        _check_row(row)
    _check_gains_before_benefits(rows)
    _check_print_codes(rows)
    return rows


def _expected_section(row):
    """Section d'impression attendue d'après la catégorie et le traitement fiscal (D-54, D-55)."""
    if row['category'] in ('BASIC', 'ALW'):
        return GAINS if row['tax_base'] == 'taxable' else 'allowances'
    if row['category'] in ('GA_SOC', 'GA_EMPLOYER') or row['core_value'] == 'fnh_employee':
        return CONTRIBUTIONS
    return {'GA_AIK': 'benefits', 'GA_TAX': 'taxes', 'DED': 'deductions', 'NET': 'pay', 'GA_CASH': 'pay'}.get(
        row['category']
    )


def _check_print_codes(rows):
    """Code d'impression : 5 chiffres, dans la section de la rubrique, unique sauf parts d'un même organisme."""
    by_code = {}
    for row in rows:
        code = row['print_code']
        if row['category'] == 'GROSS':
            if code:
                _fail(row, 'GROSS n’est pas imprimé (TOTAL BRUT et TOTAL GAINS sont calculés à l’impression)')
            continue
        if not re.fullmatch(r'\d{5}', code):
            _fail(row, f'print_code invalide {code!r} (5 chiffres)')
        if int(code) in VIRTUAL_CODES:
            _fail(row, f'print_code {code} réservé à une ligne calculée à l’impression')
        if section(code) != _expected_section(row):
            _fail(row, f'print_code {code} hors de la section {_expected_section(row)}')
        by_code.setdefault(code, []).append(row)
    for code, shared in by_code.items():
        if len(shared) == 1:
            continue
        employee_rows = [row for row in shared if row['category'] != 'GA_EMPLOYER']
        if section(code) != CONTRIBUTIONS or len(employee_rows) > 1:
            _fail(shared[1], f'print_code {code} partagé hors parts salariale / patronales d’un organisme')


def _check_gains_before_benefits(rows):
    """Les avantages en nature sont valorisés sur les gains en espèces : ceux-ci les précèdent."""
    aik = [int(row['sequence']) for row in rows if row['category'] == 'GA_AIK']
    if not aik:
        return
    for row in rows:
        if row['social_base'] != 'none' and row['category'] != 'GA_AIK' and int(row['sequence']) >= min(aik):
            _fail(row, 'un gain en espèces doit être calculé avant les avantages en nature (séquence)')


def _xml_id(prefix, code):
    return prefix + code.removeprefix('GA_').lower()


def _bool(value):
    return 'True' if BOOLEANS[value] else 'False'


def _formulas(row):
    code = row['code']
    if row['kind'] == 'standard':
        return None, STANDARD_FORMULAS[code]
    sign = '-' if row['category'] in DEDUCTION_CATEGORIES else ''
    if row['kind'] == 'core':
        call = f"payslip._l10n_ga_compute('{row['core_value']}', categories, result_rules)"
        return f'result = bool({call})', f'result = {sign}{call}'
    return (
        f"result = '{code}' in inputs",
        f"result = {sign}inputs['{code}'].amount\nresult_name = inputs['{code}'].name",
    )


def _rule(row):
    code = row['code']
    condition, amount = _formulas(row)
    lines = [
        f'        <record id="{_xml_id("rule_ga_", code)}" model="hr.salary.rule">',
        f'            <field name="name">{escape(row["name"])}</field>',
        f'            <field name="code">{code}</field>',
        f'            <field name="sequence">{row["sequence"]}</field>',
        f'            <field name="category_id" ref="{CATEGORIES[row["category"]]}"/>',
        '            <field name="struct_id" ref="structure_ga_employee"/>',
    ]
    if condition:
        lines += [
            '            <field name="condition_select">python</field>',
            f'            <field name="condition_python">{escape(condition)}</field>',
        ]
    else:
        lines.append('            <field name="condition_select">none</field>')
    lines += [
        '            <field name="amount_select">code</field>',
        f'            <field name="amount_python_compute">{escape(amount)}</field>',
    ]
    if row['kind'] == 'standard':
        lines.append('            <field name="bold" eval="True"/>')
    if code == 'NET':
        lines.append('            <field name="appears_on_employee_cost_dashboard" eval="True"/>')
    lines += [
        f'            <field name="l10n_ga_social_base">{row["social_base"]}</field>',
        f'            <field name="l10n_ga_tax_base">{row["tax_base"]}</field>',
    ]
    for column in ('social_cap_group', 'tax_cap_group', 'core_value', 'print_code', 'print_name'):
        if row[column]:
            lines.append(f'            <field name="l10n_ga_{column}">{row[column]}</field>')
    lines += [
        f'            <field name="l10n_ga_prorate" eval="{_bool(row["prorate"])}"/>',
        f'            <field name="l10n_ga_leave_base" eval="{_bool(row["leave_base"])}"/>',
        f'            <field name="l10n_ga_severance_base" eval="{_bool(row["severance_base"])}"/>',
        f'            <field name="l10n_ga_das_column">{row["das_column"]}</field>',
        f'            <field name="l10n_ga_das_exempt_column">{row["das_exempt_column"]}</field>',
        '        </record>',
    ]
    return '\n'.join(lines) + '\n'


def _input_type(row):
    attachment = 'True' if row['input_kind'] == 'attachment' else 'False'
    allowance = 'True' if row['category'] == 'ALW' else 'False'  # gain : indemnité (F15, onglet « Indemnités »)
    return (
        f'        <record id="{_xml_id("input_type_ga_", row["code"])}" model="hr.payslip.input.type">\n'
        f'            <field name="name">{escape(row["name"])}</field>\n'
        f'            <field name="code">{row["code"]}</field>\n'
        '            <field name="country_id" ref="base.ga"/>\n'
        '            <field name="struct_ids" eval="[Command.link(ref(\'structure_ga_employee\'))]"/>\n'
        f'            <field name="available_in_attachments" eval="{attachment}"/>\n'
        f'            <field name="l10n_ga_is_allowance" eval="{allowance}"/>\n'
        '        </record>\n'
    )


def render(rows):
    rules = HEADER + ''.join(_rule(row) for row in rows) + FOOTER
    inputs = HEADER + ''.join(_input_type(row) for row in rows if row['kind'] == 'input') + FOOTER
    return rules, inputs


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--check', action='store_true', help='vérifie que les fichiers versionnés sont à jour')
    args = parser.parse_args(argv)
    outputs = dict(zip((RULES_XML, INPUTS_XML), render(load_catalogue()), strict=True))
    if args.check:
        stale = [p for p, content in outputs.items() if not p.exists() or p.read_text(encoding='utf-8') != content]
        for path in stale:
            print(f'{path} n’est pas à jour : relancer tools/csv_to_salary_rules.py')
        return 1 if stale else 0
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
