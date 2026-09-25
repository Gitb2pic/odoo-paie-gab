from odoo import api, fields, models
from odoo.exceptions import UserError

PAYABLE_STATES = ('validated', 'filed', 'paid')


class L10nGaDeclarationPayment(models.Model):
    """Quittance de paiement d'une déclaration (F11, RG16) : plusieurs par déclaration (RS, FNH, CFP…).

    L'écriture comptable du paiement (``move_id``) est ajoutée par ``l10n_ga_dgi_edi_account`` (D-73).
    """

    _name = 'l10n_ga.declaration.payment'
    _description = 'Quittance de déclaration (Gabon)'
    _order = 'declaration_id, date, id'
    _check_company_auto = True

    declaration_id = fields.Many2one(
        'l10n_ga.declaration', string='Déclaration', required=True, ondelete='cascade', index=True
    )
    company_id = fields.Many2one(related='declaration_id.company_id', store=True, index=True)
    currency_id = fields.Many2one(related='declaration_id.currency_id')
    date = fields.Date(required=True, default=fields.Date.context_today)
    amount = fields.Monetary(string='Montant', required=True)
    receipt_number = fields.Char(string='N° de quittance', required=True)
    kind = fields.Selection(
        [('rs', 'Retenues sur salaires (IRPP, TCS)'), ('fnh', 'FNH'), ('cfp', 'CFP'), ('other', 'Autre')],
        string='Nature',
        required=True,
        default='rs',
    )
    mode = fields.Selection(
        [('cash', 'Espèces'), ('cheque', 'Chèque'), ('transfer', 'Virement')],
        string='Mode de versement',
        required=True,
        default='transfer',
    )
    attachment_ids = fields.Many2many(
        'ir.attachment',
        'l10n_ga_declaration_payment_attachment_rel',
        'payment_id',
        'attachment_id',
        string='Pièces jointes',
    )
    note = fields.Char()

    _amount_positive = models.Constraint('CHECK (amount > 0)', 'Le montant d’une quittance doit être positif.')

    def _check_payable(self):
        self.env['l10n_ga.declaration']._check_declarant()
        bad = self.declaration_id.filtered(lambda d: d.state not in PAYABLE_STATES)
        if bad:
            raise UserError(
                self.env._(
                    '%(name)s : une quittance ne s’enregistre que sur une déclaration validée.', name=bad[0].name
                )
            )

    @api.model_create_multi
    def create(self, vals_list):
        payments = super().create(vals_list)
        payments._check_payable()
        payments.declaration_id._l10n_ga_update_payment_state()
        return payments

    def write(self, vals):
        declarations = self.declaration_id
        result = super().write(vals)
        self._check_payable()
        (declarations | self.declaration_id)._l10n_ga_update_payment_state()
        return result

    def unlink(self):
        declarations = self.declaration_id
        self._check_payable()
        result = super().unlink()
        declarations._l10n_ga_update_payment_state()
        return result
