"""Contrôle « comptabilisation de la paie incomplète » ajouté à la chaîne F8 (patron 8, D-62).

Le standard ne comptabilise pas les bulletins dont la structure n'a pas de journal et équilibre
en silence une pièce incomplète par une ligne « Adjustment Entry »
(``E/hr_payroll_account/models/hr_payslip.py:51``, ``:113-116``) : le lot est bloqué à la place,
dès que la société tient une comptabilité (plan comptable chargé).
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


def payroll_account_issues(slip):
    """Messages bloquants : structure sans journal de paie, règles sans compte."""
    company = slip.company_id
    if not company.chart_template:
        return []
    structure = slip.struct_id.with_company(company)
    if not structure.journal_id:
        return [
            slip.env._(
                '%(company)s : la structure %(structure)s n’a pas de journal de paie ; '
                'les bulletins ne seraient pas comptabilisés. '
                'Lancez « Configurer les comptes de paie Gabon » sur la société.',
                company=company.name,
                structure=structure.name,
            )
        ]
    codes = missing_account_rules(structure, company)
    if not codes:
        return []
    return [
        slip.env._(
            '%(company)s : règles de paie sans compte comptable (%(codes)s). '
            'Lancez « Configurer les comptes de paie Gabon » sur la société.',
            company=company.name,
            codes=', '.join(codes),
        )
    ]


class MissingRuleAccounts(CheckRule):
    code = 'GA_NO_ACCOUNT'

    def applies(self, slip):
        return bool(slip.struct_id and slip.company_id.chart_template)

    def run(self, slip):
        return [self.issue(message, slip.struct_id) for message in payroll_account_issues(slip)]
