from odoo import api, fields, models
from odoo.exceptions import UserError

from .l10n_ga_payroll_check import BLOCKING, run_checks


class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    l10n_ga_payment_date = fields.Date(
        string='Date de paiement',
        compute='_compute_l10n_ga_payment_date',
        store=True,
        readonly=False,
        help='Date de paiement du lot, reprise par ses bulletins (rattachement à l’ID10, D-46).',
    )
    l10n_ga_issue_ids = fields.One2many('l10n_ga.check.issue', 'payslip_run_id', string='Anomalies')
    l10n_ga_blocking_count = fields.Integer(string='Anomalies bloquantes', compute='_compute_l10n_ga_issue_counts')
    l10n_ga_warning_count = fields.Integer(string='Avertissements', compute='_compute_l10n_ga_issue_counts')
    l10n_ga_is_ga = fields.Boolean(compute='_compute_l10n_ga_is_ga')

    @api.depends('date_end')
    def _compute_l10n_ga_payment_date(self):
        for run in self:
            run.l10n_ga_payment_date = run.date_end

    @api.depends('l10n_ga_issue_ids.severity')
    def _compute_l10n_ga_issue_counts(self):
        for run in self:
            severities = run.l10n_ga_issue_ids.mapped('severity')
            run.l10n_ga_blocking_count = severities.count(BLOCKING)
            run.l10n_ga_warning_count = len(severities) - run.l10n_ga_blocking_count

    @api.depends('company_id.country_id', 'structure_id.country_id', 'slip_ids.struct_id')
    def _compute_l10n_ga_is_ga(self):
        for run in self:
            run.l10n_ga_is_ga = bool(run.slip_ids.filtered('l10n_ga_is_ga')) or 'GA' in (
                run.structure_id.country_id.code,
                run.company_id.country_id.code,
            )

    def _l10n_ga_run_checks(self):
        """Contrôles avant paie (F8) : anomalies du lot recréées sur ses bulletins brouillons Gabon."""
        Issue = self.env['l10n_ga.check.issue'].sudo()
        for run in self:
            Issue.search([('payslip_run_id', '=', run.id)]).unlink()
            values = []
            for slip in run.slip_ids.filtered(lambda s: s.state == 'draft' and s.l10n_ga_is_ga):
                for severity, code, message, record in run_checks(slip):
                    values.append(
                        {
                            'company_id': run.company_id.id,
                            'scope': 'payslip_run',
                            'payslip_run_id': run.id,
                            'payslip_id': slip.id,
                            'employee_id': slip.employee_id.id,
                            'severity': severity,
                            'code': code,
                            'message': message,
                            'res_model': record._name,
                            'res_id': record.id,
                        }
                    )
            Issue.create(values)

    def _l10n_ga_blocked(self):
        """Lots qui ont encore une anomalie bloquante (RG26)."""
        return self.filtered(lambda run: run.l10n_ga_blocking_count)

    def action_l10n_ga_check(self):
        self._l10n_ga_run_checks()
        return True

    def action_confirm(self):
        # RG26 : « Calculer » refusé tant qu'il reste une anomalie bloquante (D-38).
        self._l10n_ga_run_checks()
        blocked = self._l10n_ga_blocked()
        if blocked:
            messages = blocked.l10n_ga_issue_ids.filtered(lambda i: i.severity == BLOCKING).mapped('message')
            raise UserError(
                self.env._('Le lot ne peut pas être calculé : anomalies bloquantes à corriger.')
                + '\n'
                + '\n'.join(messages)
            )
        return super().action_confirm()

    def action_l10n_ga_input_import(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Importer les variables du mois'),
            'res_model': 'l10n_ga.payslip.input.import',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_payslip_run_id': self.id},
        }

    def action_l10n_ga_issues(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Anomalies du lot %(run)s', run=self.name),
            'res_model': 'l10n_ga.check.issue',
            'view_mode': 'list,form',
            'domain': [('payslip_run_id', '=', self.id)],
        }
