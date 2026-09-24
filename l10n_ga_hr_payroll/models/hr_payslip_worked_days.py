from odoo import api, models

CNSS_PAY_MODE = 'cnss'


class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    @api.depends('payslip_id.company_id.l10n_ga_cnss_subrogation', 'work_entry_type_id.l10n_ga_pay_mode')
    def _compute_is_paid(self):
        """Maternité / accident du travail hors salaire de base sans subrogation (F4, D-26)."""
        super()._compute_is_paid()
        for worked_days in self:
            if (
                worked_days.is_paid
                and worked_days.work_entry_type_id.l10n_ga_pay_mode == CNSS_PAY_MODE
                and not worked_days.payslip_id.company_id.l10n_ga_cnss_subrogation
            ):
                worked_days.is_paid = False
