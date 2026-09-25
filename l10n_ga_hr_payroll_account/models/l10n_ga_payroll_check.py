"""Contrôle « comptes de paie manquants » ajouté à la chaîne F8 (patron 8, D-62).

Sans compte, le standard équilibre la pièce en silence par une ligne « Adjustment Entry »
(``E/hr_payroll_account/models/hr_payslip.py:113-116``) : le lot est bloqué à la place.
"""

from odoo.addons.l10n_ga_hr_payroll.models.l10n_ga_payroll_check import CheckRule

from .account_chart_template import RULE_ACCOUNTS


def missing_account_rules(structure, company):
    """Codes des règles de la structure dont un compte attendu est vide pour la société."""
    return [
        rule.code
        for rule in structure.rule_ids.with_company(company)
        if any(not rule[f'account_{key}'] for key in RULE_ACCOUNTS.get(rule.code, {}))
    ]


class MissingRuleAccounts(CheckRule):
    code = 'GA_NO_ACCOUNT'

    def applies(self, slip):
        return bool(slip.struct_id.with_company(slip.company_id).journal_id)

    def run(self, slip):
        codes = missing_account_rules(slip.struct_id, slip.company_id)
        if not codes:
            return []
        return [self.issue(missing_accounts_message(slip, codes), slip.struct_id)]


def missing_accounts_message(slip, codes):
    return slip.env._(
        '%(company)s : règles de paie sans compte comptable (%(codes)s). '
        'Lancez « Configurer les comptes de paie Gabon » sur la société.',
        company=slip.company_id.name,
        codes=', '.join(codes),
    )
