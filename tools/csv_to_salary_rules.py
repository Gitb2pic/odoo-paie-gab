#!/usr/bin/env python3
"""Génère les règles salariales et les types d'entrée depuis ``data/catalogue_rubriques_ga.csv`` (F6).

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
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'l10n_ga_hr_payroll' / 'lib'))

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
    'source',
)
CATEGORIES = {
    'BASIC': 'hr_payroll.BASIC',
    'ALW': 'hr_payroll.ALW',
    'GROSS': 'hr_payroll.GROSS',
    'DED': 'hr_payroll.DED',
    'NET': 'hr_payroll.NET',
    'GA_AIK': 'category_ga_aik',
}
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
    if row['kind'] not in ('standard', 'input'):
        _fail(row, f'kind invalide {row["kind"]!r}')
    if (row['kind'] == 'standard') != (code in STANDARD_FORMULAS):
        _fail(row, 'seules BASIC, GROSS et NET sont des règles standard, et elles doivent l’être')
    if row['kind'] == 'input' and not code.startswith('GA_'):
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
    with open(path, encoding='utf-8', newline='') as stream:
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
    return rows


def _xml_id(prefix, code):
    return prefix + code.removeprefix('GA_').lower()


def _bool(value):
    return 'True' if BOOLEANS[value] else 'False'


def _formulas(row):
    code = row['code']
    if row['kind'] == 'standard':
        return None, STANDARD_FORMULAS[code]
    sign = '-' if row['category'] == 'DED' else ''
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
    for column in ('social_cap_group', 'tax_cap_group'):
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
    return (
        f'        <record id="{_xml_id("input_type_ga_", row["code"])}" model="hr.payslip.input.type">\n'
        f'            <field name="name">{escape(row["name"])}</field>\n'
        f'            <field name="code">{row["code"]}</field>\n'
        '            <field name="country_id" ref="base.ga"/>\n'
        '            <field name="struct_ids" eval="[Command.link(ref(\'structure_ga_employee\'))]"/>\n'
        f'            <field name="available_in_attachments" eval="{attachment}"/>\n'
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
