from odoo import fields, models

WITHHOLDING_KINDS = [('ras_095', 'RAS 9,5 % (prestataires, ID18)'), ('ras_20', 'RAS 20 % (non-résidents, ID27)')]


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_ga_withholding_kind = fields.Selection(
        WITHHOLDING_KINDS,
        string='Retenue gabonaise',
        help='Nature de la retenue à la source (Gabon) : lue par les déclarations ID18, ID27, ID24 et ID26.',
    )

    def _l10n_ga_withholding_taxes(self, company, kind=None):
        domain = [
            *self._check_company_domain(company),
            ('l10n_ga_withholding_kind', '=', kind) if kind else ('l10n_ga_withholding_kind', '!=', False),
        ]
        return self.with_context(active_test=False).search(domain)
