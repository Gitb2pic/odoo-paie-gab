"""Remboursement anticipé d'un prêt salarié (F1, décision D-33).

Deux modes : hors paie (échéance « remboursée hors paie ») ou sur le bulletin d'un mois donné
(échéance « à payer » reprise par ``GA_LOAN``). Les échéances restantes sont réduites en partant
de la dernière : la durée raccourcit, la mensualité ne change pas.
"""

from odoo import api, fields, models
from odoo.exceptions import UserError


class L10nGaLoanEarlyRepayment(models.TransientModel):
    _name = 'l10n_ga.loan.early.repayment'
    _description = 'Remboursement anticipé d’un prêt salarié (Gabon)'

    loan_id = fields.Many2one('l10n_ga.employee.loan', string='Prêt', required=True)
    currency_id = fields.Many2one(related='loan_id.currency_id')
    remaining_amount = fields.Monetary(related='loan_id.remaining_amount', string='Restant dû')
    amount = fields.Monetary(string='Montant remboursé', required=True)
    mode = fields.Selection(
        [('outside', 'Hors paie (espèces, virement)'), ('payslip', 'Sur le bulletin du mois choisi')],
        required=True,
        default='outside',
    )
    date = fields.Date(required=True, default=fields.Date.context_today)
    note = fields.Char(string='Référence')

    @api.onchange('loan_id')
    def _onchange_loan_id(self):
        self.amount = self.loan_id.remaining_amount

    def action_confirm(self):
        self.ensure_one()
        loan = self.loan_id
        if loan.state not in ('approved', 'running'):
            raise UserError(self.env._('Seul un prêt approuvé ou en cours peut être remboursé par anticipation.'))
        if self.amount <= 0 or self.amount > loan.remaining_amount:
            raise UserError(
                self.env._('Le montant doit être positif et au plus égal au restant dû (%s).', loan.remaining_amount)
            )
        line = self.env['l10n_ga.employee.loan.line'].create(
            {
                'loan_id': loan.id,
                'due_date': self.date,
                'amount': self.amount,
                'note': self.note or self.env._('Remboursement anticipé'),
            }
        )
        loan._reduce_from_end(self.amount, keep=line)
        if self.mode == 'outside':
            line.state = 'repaid'
        loan.message_post(
            body=self.env._(
                'Remboursement anticipé de %(amount)s (%(mode)s) au %(date)s.',
                amount=self.amount,
                mode=dict(self._fields['mode']._description_selection(self.env))[self.mode],
                date=self.date,
            )
        )
        loan._update_state()
        return {'type': 'ir.actions.act_window_close'}
