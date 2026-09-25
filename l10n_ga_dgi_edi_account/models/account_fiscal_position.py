from odoo import fields, models

from .account_tax import WITHHOLDING_KINDS


class AccountFiscalPosition(models.Model):
    _inherit = 'account.fiscal.position'

    l10n_ga_withholding_kind = fields.Selection(
        WITHHOLDING_KINDS,
        string='Retenue gabonaise',
        help='Retenue à la source ajoutée aux lignes des factures fournisseurs de cette position (D-96).',
    )
