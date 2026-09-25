from odoo import models

# Dettes de paie rapprochées des déclarations (étape 4) : ID10 (447x) et DTS (431x).
LIABILITY_ACCOUNTS = {
    'tax': ('pcg_4471', 'pcg_4472'),
    'social': ('pcg_4311', 'pcg_4312', 'pcg_4313', 'pcg_4318'),
}


class ResCompany(models.Model):
    _inherit = 'res.company'

    def l10n_ga_payroll_liability_balance(self, kind, date_to, date_from=None):
        """Solde créditeur (reste dû) des comptes de dettes de paie, écritures comptabilisées.

        :param kind: ``'tax'`` (4471, 4472 : ID10) ou ``'social'`` (4311 à 4318 : DTS)
        :return: ``{code du compte: solde}`` ; sans ``date_from``, solde cumulé au ``date_to``.
        """
        self.ensure_one()
        # Code du compte lu dans le contexte de la société (``code`` dépend de la société en 19).
        company = self.with_company(self)
        chart = company.env['account.chart.template']
        accounts = company.env['account.account']
        for template_xmlid in LIABILITY_ACCOUNTS[kind]:
            accounts |= chart.ref(template_xmlid, raise_if_not_found=False)
        domain = [
            ('company_id', '=', self.id),
            ('account_id', 'in', accounts.ids),
            ('parent_state', '=', 'posted'),
            ('date', '<=', date_to),
        ]
        if date_from:
            domain.append(('date', '>=', date_from))
        balances = dict(company.env['account.move.line']._read_group(domain, ['account_id'], ['balance:sum']))
        return {account.code: -balances.get(account, 0.0) for account in accounts}
