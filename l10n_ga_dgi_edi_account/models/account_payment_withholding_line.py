from odoo import api, models

from .account_move_line import check_withholding


class AccountPaymentWithholdingLine(models.Model):
    _inherit = 'account.payment.withholding.line'

    @api.constrains('tax_id', 'payment_id')
    def _check_l10n_ga_withholding(self):
        for payment in self.payment_id:
            check_withholding(
                payment.partner_id, payment.withholding_line_ids.tax_id.mapped('l10n_ga_withholding_kind'), payment.env
            )
