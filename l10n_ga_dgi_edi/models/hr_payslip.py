from odoo import models


class HrPayslip(models.Model):
    """Observer (patron 11, ADR-10, ADR-19) : chaque changement d'état d'un bulletin met à jour les
    déclarations non figées de sa période (lot ou bulletin seul)."""

    _inherit = 'hr.payslip'

    def _l10n_ga_notify_declarations(self):
        self.env['l10n_ga.declaration']._l10n_ga_on_payslips_done(self)

    def action_payslip_done(self):
        result = super().action_payslip_done()
        self._l10n_ga_notify_declarations()
        return result

    def action_payslip_paid(self):
        result = super().action_payslip_paid()
        self._l10n_ga_notify_declarations()
        return result

    def action_payslip_cancel(self):
        result = super().action_payslip_cancel()
        self._l10n_ga_notify_declarations()
        return result

    def action_payslip_draft(self):
        result = super().action_payslip_draft()
        self._l10n_ga_notify_declarations()
        return result
