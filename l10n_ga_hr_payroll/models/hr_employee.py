from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    # Champs de version à groupe exposés sur le salarié (C/addons/hr/models/hr_employee.py:180) :
    # related non stockés, aucune donnée fiscale stockée sur hr.employee (ADR-05, règle d'or 5).
    l10n_ga_disabled_children = fields.Integer(
        related='version_id.l10n_ga_disabled_children', readonly=False, inherited=True, groups='hr.group_hr_user'
    )
    l10n_ga_extra_half_part = fields.Boolean(
        related='version_id.l10n_ga_extra_half_part', readonly=False, inherited=True, groups='hr.group_hr_user'
    )
    l10n_ga_tax_parts_forced = fields.Float(
        related='version_id.l10n_ga_tax_parts_forced', readonly=False, inherited=True, groups='hr.group_hr_user'
    )
    l10n_ga_tax_parts_forced_reason = fields.Char(
        related='version_id.l10n_ga_tax_parts_forced_reason', readonly=False, inherited=True, groups='hr.group_hr_user'
    )
    l10n_ga_tax_parts = fields.Float(related='version_id.l10n_ga_tax_parts', inherited=True, groups='hr.group_hr_user')
    l10n_ga_cnamgs_number = fields.Char(
        related='version_id.l10n_ga_cnamgs_number', readonly=False, inherited=True, groups='hr.group_hr_user'
    )
    l10n_ga_nif = fields.Char(
        related='version_id.l10n_ga_nif', readonly=False, inherited=True, groups='hr.group_hr_user'
    )
    l10n_ga_nationality_code = fields.Selection(
        related='version_id.l10n_ga_nationality_code', inherited=True, groups='hr.group_hr_user'
    )
    l10n_ga_job_code = fields.Char(
        related='version_id.l10n_ga_job_code', readonly=False, inherited=True, groups='hr.group_hr_user'
    )
    l10n_ga_level_code = fields.Char(
        related='version_id.l10n_ga_level_code', readonly=False, inherited=True, groups='hr.group_hr_user'
    )
    l10n_ga_transport_trips = fields.Selection(
        related='version_id.l10n_ga_transport_trips', readonly=False, inherited=True, groups='hr.group_hr_user'
    )
    l10n_ga_company_car = fields.Boolean(
        related='version_id.l10n_ga_company_car', readonly=False, inherited=True, groups='hr.group_hr_user'
    )
    l10n_ga_benefit_housing = fields.Boolean(
        related='version_id.l10n_ga_benefit_housing', readonly=False, inherited=True, groups='hr.group_hr_user'
    )
    l10n_ga_benefit_domestic = fields.Boolean(
        related='version_id.l10n_ga_benefit_domestic', readonly=False, inherited=True, groups='hr.group_hr_user'
    )
    l10n_ga_benefit_utilities = fields.Boolean(
        related='version_id.l10n_ga_benefit_utilities', readonly=False, inherited=True, groups='hr.group_hr_user'
    )
    l10n_ga_benefit_food = fields.Boolean(
        related='version_id.l10n_ga_benefit_food', readonly=False, inherited=True, groups='hr.group_hr_user'
    )
    l10n_ga_payment_mode = fields.Selection(
        related='version_id.l10n_ga_payment_mode', readonly=False, inherited=True, groups='hr.group_hr_user'
    )
    l10n_ga_agreement_id = fields.Many2one(
        related='version_id.l10n_ga_agreement_id', readonly=False, inherited=True, groups='hr.group_hr_user'
    )
    l10n_ga_grade_id = fields.Many2one(
        related='version_id.l10n_ga_grade_id', readonly=False, inherited=True, groups='hr.group_hr_user'
    )
    l10n_ga_seniority_date = fields.Date(
        related='version_id.l10n_ga_seniority_date', readonly=False, inherited=True, groups='hr.group_hr_user'
    )
    # Boutons intelligents « Indemnités » (F15) et « Prêts » (F1) : compteurs non stockés.
    l10n_ga_allowance_count = fields.Integer(
        compute='_compute_l10n_ga_payroll_counts', groups='hr_payroll.group_hr_payroll_user'
    )
    l10n_ga_loan_count = fields.Integer(
        compute='_compute_l10n_ga_payroll_counts', groups='hr_payroll.group_hr_payroll_user'
    )
    l10n_ga_ytd_opening_count = fields.Integer(
        compute='_compute_l10n_ga_payroll_counts', groups='hr_payroll.group_hr_payroll_user'
    )

    def _compute_l10n_ga_payroll_counts(self):
        loans = dict(
            self.env['l10n_ga.employee.loan']._read_group(
                [('employee_id', 'in', self.ids)], ['employee_id'], ['__count']
            )
        )
        openings = dict(
            self.env['l10n_ga.ytd.opening']._read_group([('employee_id', 'in', self.ids)], ['employee_id'], ['__count'])
        )
        for employee in self:
            employee.l10n_ga_ytd_opening_count = openings.get(employee, 0)
            employee.l10n_ga_allowance_count = len(
                employee.salary_attachment_ids.filtered(lambda a: a.l10n_ga_is_allowance and a.state == 'open')
            )
            employee.l10n_ga_loan_count = loans.get(employee, 0)

    def action_l10n_ga_allowances(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Indemnités'),
            'res_model': 'hr.salary.attachment',
            'view_mode': 'list,form',
            'domain': [('employee_ids', 'in', self.ids), ('other_input_type_id.l10n_ga_is_allowance', '=', True)],
            'context': {'default_employee_ids': self.ids, 'default_duration_type': 'unlimited'},
        }

    def action_l10n_ga_loans(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Prêts'),
            'res_model': 'l10n_ga.employee.loan',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id, 'default_company_id': self.company_id.id},
        }

    def action_l10n_ga_ytd_openings(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Cumuls d’ouverture'),
            'res_model': 'l10n_ga.ytd.opening',
            'view_mode': 'list,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {'default_employee_id': self.id, 'default_company_id': self.company_id.id},
        }
