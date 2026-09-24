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
