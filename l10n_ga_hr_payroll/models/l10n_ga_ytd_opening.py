from datetime import date

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

VALIDATED_STATES = ('validated', 'paid')  # sprint 0 point 3
# Champ figé mensuel du bulletin → champ du cumul d'ouverture (F12, D-45).
OPENING_FIELDS = {
    'l10n_ga_gross': 'gross',
    'l10n_ga_taxable_gross': 'taxable',
    'l10n_ga_irpp_base': 'irpp_base',
    'l10n_ga_irpp_withheld': 'irpp',
    'l10n_ga_tcs': 'tcs',
    'l10n_ga_cnss_employee': 'cnss',
    'l10n_ga_bonus_exempted': 'bonus_exempt',
    'l10n_ga_employee_contributions': 'contributions',
    'l10n_ga_benefits_in_kind': 'benefits',
    'l10n_ga_fnh_employer': 'fnh',
    'l10n_ga_tax_exempt': 'tax_exempt',
}


class L10nGaYtdOpening(models.Model):
    """Cumuls d'ouverture de l'année de bascule (F12, RG25).

    Ils complètent les cumuls des bulletins de l'année postérieurs à la période couverte :
    régularisation IRPP, plafond des gratifications exonérées, cumuls figés du bulletin et DAS.
    """

    _name = 'l10n_ga.ytd.opening'
    _description = 'Cumuls d’ouverture de paie (Gabon)'
    _order = 'year desc, employee_id'
    _check_company_auto = True

    employee_id = fields.Many2one('hr.employee', string='Salarié', required=True, index=True, check_company=True)
    company_id = fields.Many2one(
        'res.company', string='Société', required=True, index=True, default=lambda self: self.env.company
    )
    currency_id = fields.Many2one(related='company_id.currency_id')
    year = fields.Integer(string='Année', required=True, default=lambda self: fields.Date.today().year)
    date_from = fields.Date(string='Période couverte du', required=True)
    date_to = fields.Date(string='au', required=True)
    gross = fields.Monetary(string='Brut')
    taxable = fields.Monetary(string='Brut imposable')
    irpp_base = fields.Monetary(
        string='Base IRPP cumulée', help='Somme des bases IRPP mensuelles de la période (régularisation annuelle).'
    )
    irpp = fields.Monetary(string='IRPP retenu')
    tcs = fields.Monetary(string='TCS')
    cnss = fields.Monetary(string='CNSS salariale')
    bonus_exempt = fields.Monetary(string='Gratifications exonérées')
    # Colonnes des cumuls du bulletin imprimé (plan 2.7 b) : facultatives, 0 si inconnues.
    contributions = fields.Monetary(string='Cotisations salariales')
    benefits = fields.Monetary(string='Avantages en nature')
    fnh = fields.Monetary(string='FNH patronal')
    tax_exempt = fields.Monetary(string='Indemnités non imposables')
    note = fields.Text(string='Origine des cumuls')

    _employee_year_unique = models.Constraint(
        'UNIQUE(employee_id, year)',
        'Un salarié a au plus un cumul d’ouverture par année (RG25).',
    )

    @api.depends('employee_id', 'year')
    def _compute_display_name(self):
        for opening in self:
            opening.display_name = f'{opening.employee_id.name or ""} — {opening.year}'

    @api.constrains('year', 'date_from', 'date_to')
    def _check_period(self):
        for opening in self:
            first, last = date(opening.year, 1, 1), date(opening.year, 12, 31)
            if not first <= opening.date_from <= opening.date_to <= last:
                raise ValidationError(
                    self.env._(
                        'Cumuls d’ouverture %(name)s : la période couverte doit être comprise dans l’année %(year)s.',
                        name=opening.display_name,
                        year=opening.year,
                    )
                )

    def _used_by_slips(self):
        """Bulletins validés qui ont repris ces cumuls (postérieurs à la période couverte)."""
        self.ensure_one()
        return self.env['hr.payslip'].search(
            [
                ('employee_id', '=', self.employee_id.id),
                ('company_id', '=', self.company_id.id),
                ('state', 'in', VALIDATED_STATES),
                ('date_from', '>', self.date_to),
                ('date_to', '<=', date(self.year, 12, 31)),
            ],
            limit=1,
        )

    def _check_unlocked(self):
        for opening in self:
            if opening._used_by_slips():
                raise UserError(
                    self.env._(
                        'Cumuls d’ouverture %(name)s : déjà repris par un bulletin validé. '
                        'Annulez les bulletins concernés avant de les corriger.',
                        name=opening.display_name,
                    )
                )

    def write(self, vals):
        self._check_unlocked()
        return super().write(vals)

    @api.ondelete(at_uninstall=False)
    def _unlink_if_unused(self):
        self._check_unlocked()

    def _value(self, slip_field):
        """Valeur d'ouverture correspondant à un champ figé du bulletin (0 si non suivi)."""
        self.ensure_one()
        opening_field = OPENING_FIELDS.get(slip_field)
        return self[opening_field] if opening_field else 0.0
