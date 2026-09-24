#!/usr/bin/env python3
"""Génère ``l10n_ga_hr_payroll/data/hr_rule_parameters_data.xml`` depuis le YAML de la base.

Règle d'or 1 : aucun taux, plafond ni barème en dur ; tout passe par ``hr.rule.parameter``.
La table des codes est ``ga_fiscal_core.param_codes.PARAMETERS`` (partagée avec l'adaptateur).
Une ``hr.rule.parameter.value`` par date d'effet ; sortie déterministe (idempotente).

Usage :
    tools/yaml_to_rule_parameters.py           # écrit le fichier
    tools/yaml_to_rule_parameters.py --check   # code 1 si le fichier versionné diffère
"""

import argparse
import sys
from pathlib import Path
from xml.sax.saxutils import escape

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'l10n_ga_hr_payroll' / 'lib'))

from ga_fiscal_core.param_codes import PARAMETERS, dated_values  # noqa: E402

YAML_PATH = REPO / 'docs' / 'base_connaissance' / 'parametres_fiscaux_gabon_2026.yaml'
XML_PATH = REPO / 'l10n_ga_hr_payroll' / 'data' / 'hr_rule_parameters_data.xml'

HEADER = """<?xml version="1.0" encoding="utf-8"?>
<!--
    FICHIER GÉNÉRÉ par tools/yaml_to_rule_parameters.py depuis
    docs/base_connaissance/parametres_fiscaux_gabon_2026.yaml : ne pas modifier à la main.
    Une valeur par date d'effet (RG06) ; une valeur non datée dans le YAML porte la date
    sentinelle 2000-01-01. Valeurs = littéraux Python (safe_eval, sprint 0 point 11).
-->
<odoo>
    <data noupdate="0">
"""
FOOTER = """    </data>
</odoo>
"""


def _xml_id(code):
    return 'rule_parameter_' + code.removeprefix('l10n_ga_')


def load_yaml(path=YAML_PATH):
    import yaml  # noqa: PLC0415 — outil de build

    with open(path, encoding='utf-8') as stream:
        return yaml.safe_load(stream)


def render(data):
    parts = [HEADER]
    for spec in PARAMETERS:
        xml_id = _xml_id(spec.code)
        parts.append(
            f'        <record id="{xml_id}" model="hr.rule.parameter">\n'
            f'            <field name="name">{escape(spec.name)}</field>\n'
            f'            <field name="code">{spec.code}</field>\n'
            '            <field name="country_id" ref="base.ga"/>\n'
            '        </record>\n'
        )
        for day, value in dated_values(data, spec):
            parts.append(
                f'        <record id="{xml_id}_{day:%Y%m%d}" model="hr.rule.parameter.value">\n'
                f'            <field name="rule_parameter_id" ref="{xml_id}"/>\n'
                f'            <field name="date_from">{day.isoformat()}</field>\n'
                f'            <field name="parameter_value">{escape(repr(value))}</field>\n'
                '        </record>\n'
            )
    parts.append(FOOTER)
    return ''.join(parts)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--check', action='store_true', help='vérifie que le fichier versionné est à jour')
    args = parser.parse_args(argv)
    content = render(load_yaml())
    if args.check:
        current = XML_PATH.read_text(encoding='utf-8') if XML_PATH.exists() else ''
        if current != content:
            print(f'{XML_PATH} n’est pas à jour : relancer tools/yaml_to_rule_parameters.py')
            return 1
        return 0
    XML_PATH.parent.mkdir(parents=True, exist_ok=True)
    XML_PATH.write_text(content, encoding='utf-8')
    return 0


if __name__ == '__main__':
    sys.exit(main())
