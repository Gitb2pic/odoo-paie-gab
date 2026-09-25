from odoo import models

from .l10n_ga_payroll_check import MissingRuleAccounts, missing_account_rules, missing_accounts_message


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    def _l10n_ga_payroll_checks(self):
        return (*super()._l10n_ga_payroll_checks(), MissingRuleAccounts())

    def _action_create_account_move(self):
        """Pièces des bulletins Gabon créées dans le contexte de leur société.

        Journal et comptes sont ``company_dependent`` et lus avec ``env.company``
        (``E/hr_payroll_account/models/hr_payslip.py:66``, ``:185-186``) : sans ce découpage,
        des bulletins de plusieurs sociétés validés ensemble prendraient les comptes d'une seule.
        """
        ga_slips = self.filtered('l10n_ga_is_ga')
        others = self - ga_slips
        if others:
            super(HrPayslip, others)._action_create_account_move()
        for company, slips in ga_slips.grouped('company_id').items():
            super(HrPayslip, slips.with_company(company))._action_create_account_move()
        return True

    def _l10n_ga_blocking_issues(self):
        """Bulletin validé hors lot : même blocage que le contrôle du lot (GA_NO_ACCOUNT)."""
        messages = super()._l10n_ga_blocking_issues()
        if MissingRuleAccounts().applies(self):
            codes = missing_account_rules(self.struct_id, self.company_id)
            if codes:
                messages.append(missing_accounts_message(self, codes))
        return messages
