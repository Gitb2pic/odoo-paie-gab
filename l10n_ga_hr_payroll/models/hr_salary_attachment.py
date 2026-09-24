"""Indemnités récurrentes (F15, ADR-16, D-29) : extension de l'ajustement de salaire standard.

S'applique aux types d'entrée Gabon marqués ``l10n_ga_is_allowance`` (gains) : mode de calcul,
prorata des jours de validité (D-35), forcée imposable motivée, non-chevauchement (RG28).
Les retenues Gabon (cessions, saisies) gardent le comportement standard.
"""

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..lib.ga_fiscal_core.allowances import FIXED, QUANTITY_RATE, WAGE_PERCENT, allowance_amount, validity_ratio
from ..lib.ga_fiscal_core.rounding import round_fcfa


class HrSalaryAttachment(models.Model):
    _inherit = 'hr.salary.attachment'

    l10n_ga_is_allowance = fields.Boolean(related='other_input_type_id.l10n_ga_is_allowance')
    l10n_ga_mode = fields.Selection(
        [(FIXED, 'Montant fixe'), (WAGE_PERCENT, '% du salaire'), (QUANTITY_RATE, 'Quantité × taux')],
        string='Mode de calcul',
        default=FIXED,
        required=True,
        tracking=True,
    )
    l10n_ga_rate = fields.Float(
        string='Taux', tracking=True, help='Pourcentage du salaire de la version du bulletin, ou taux unitaire.'
    )
    l10n_ga_quantity = fields.Float(string='Quantité', tracking=True)
    l10n_ga_forced_taxable = fields.Boolean(
        string='Forcée imposable', tracking=True, help='Aucune exonération fiscale pour cette indemnité (F15).'
    )
    l10n_ga_forced_reason = fields.Char(string='Motif (forcée imposable)', tracking=True)
    # Montant indicatif en mode calculé (contrainte standard monthly_amount > 0) ; le bulletin recalcule.
    monthly_amount = fields.Monetary(compute='_compute_monthly_amount', store=True, readonly=False, precompute=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('l10n_ga_mode', FIXED) != FIXED:
                vals.pop('monthly_amount', None)  # montant calculé par le mode
        return super().create(vals_list)

    @api.depends('l10n_ga_mode', 'l10n_ga_rate', 'l10n_ga_quantity', 'employee_ids.version_id.wage')
    def _compute_monthly_amount(self):
        for attachment in self:
            if attachment.l10n_ga_mode == FIXED or not attachment.l10n_ga_is_allowance:
                attachment.monthly_amount = attachment.monthly_amount
            else:
                wage = attachment.employee_ids[:1].version_id.wage
                attachment.monthly_amount = allowance_amount(
                    attachment.l10n_ga_mode, attachment.l10n_ga_rate, attachment.l10n_ga_quantity, wage
                )

    def _l10n_ga_amount(self, payslip):
        """Montant de l'indemnité sur ``payslip`` : mode × jours de validité dans la période."""
        self.ensure_one()
        if self.l10n_ga_mode == FIXED:
            amount = self.monthly_amount
        else:
            amount = allowance_amount(
                self.l10n_ga_mode, self.l10n_ga_rate, self.l10n_ga_quantity, payslip.version_id.wage
            )
        ratio = validity_ratio(self.date_start, self.date_end, payslip.date_from, payslip.date_to)
        sign = -1 if self.is_refund != bool(payslip.credit_note) else 1
        return sign * round_fcfa(amount * ratio)

    @api.constrains('l10n_ga_forced_taxable', 'l10n_ga_forced_reason')
    def _check_l10n_ga_forced_reason(self):
        for attachment in self:
            if attachment.l10n_ga_forced_taxable and not (attachment.l10n_ga_forced_reason or '').strip():
                raise ValidationError(self.env._('Une indemnité forcée imposable doit être motivée.'))

    @api.constrains('employee_ids', 'other_input_type_id', 'date_start', 'date_end', 'state')
    def _check_l10n_ga_overlap(self):
        """RG28 : deux indemnités ouvertes d'un même type ne se chevauchent pas pour un salarié."""
        for attachment in self.filtered(lambda a: a.l10n_ga_is_allowance and a.state == 'open'):
            domain = [
                ('id', '!=', attachment.id),
                ('state', '=', 'open'),
                ('other_input_type_id', '=', attachment.other_input_type_id.id),
                ('employee_ids', 'in', attachment.employee_ids.ids),
                '|',
                ('date_end', '=', False),
                ('date_end', '>=', attachment.date_start),
            ]
            if attachment.date_end:
                domain.append(('date_start', '<=', attachment.date_end))
            other = self.search(domain, limit=1)
            if other:
                raise ValidationError(
                    self.env._(
                        '%(type)s : cette indemnité chevauche celle du %(start)s. Clôturez-la avant d’en créer '
                        'une nouvelle (revalorisation = nouvelle ligne datée).',
                        type=attachment.other_input_type_id.name,
                        start=other.date_start,
                    )
                )

    def record_payment(self, total_amount):
        # ADR-16 : une indemnité n'a pas de total à solder ; seules les retenues sont suivies.
        return super(HrSalaryAttachment, self.filtered(lambda a: not a.l10n_ga_is_allowance)).record_payment(
            total_amount
        )
