from odoo import fields, models


class HrPayslipInput(models.Model):
    _inherit = 'hr.payslip.input'

    # Entrées créées par le code (marquées) ; une entrée non marquée est une saisie manuelle (F15).
    l10n_ga_allowance_id = fields.Many2one(
        'hr.salary.attachment', string='Indemnité', readonly=True, ondelete='set null', index='btree_not_null'
    )
    l10n_ga_loan_line_id = fields.Many2one(
        'l10n_ga.employee.loan.line',
        string='Échéance de prêt',
        readonly=True,
        ondelete='set null',
        index='btree_not_null',
    )
    l10n_ga_forced_taxable = fields.Boolean(
        string='Forcée imposable', readonly=True, help='Recopié de l’indemnité : aucune exonération fiscale (F15).'
    )
