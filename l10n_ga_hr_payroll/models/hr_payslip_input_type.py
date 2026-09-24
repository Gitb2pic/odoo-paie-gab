from odoo import fields, models


class HrPayslipInputType(models.Model):
    _inherit = 'hr.payslip.input.type'

    l10n_ga_is_allowance = fields.Boolean(
        string='Indemnité (Gabon)',
        help='Gain lu par une rubrique Gabon : ajustement traité comme une indemnité récurrente (F15, ADR-16).',
    )
