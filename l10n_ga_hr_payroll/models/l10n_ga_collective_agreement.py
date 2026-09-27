from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..lib.ga_fiscal_core.labour import completed_years, seniority_rate

TEMPLATE_XMLID = 'l10n_ga_hr_payroll.agreement_example_common'


class L10nGaCollectiveAgreement(models.Model):
    """Convention collective (RG04, F5) : règle d'ancienneté, grille, taux d'heures supplémentaires."""

    _name = 'l10n_ga.collective.agreement'
    _description = 'Convention collective (Gabon)'
    _order = 'name'
    _check_company_auto = True

    name = fields.Char(string='Convention', required=True)
    code = fields.Char()
    company_id = fields.Many2one('res.company', string='Société', required=True, default=lambda self: self.env.company)
    active = fields.Boolean(default=True)
    is_example = fields.Boolean(
        string='Exemple', help='Données d’exemple livrées avec le module : à remplacer par la convention du client.'
    )
    # Ancienneté (base 05 §4, décision D-25)
    seniority_start_years = fields.Integer(string='Ancienneté : début (années)')
    seniority_start_rate = fields.Float(string='Ancienneté : taux de début', digits=(5, 4))
    seniority_step_rate = fields.Float(string='Ancienneté : pas annuel', digits=(5, 4))
    seniority_max_rate = fields.Float(string='Ancienneté : plafond', digits=(5, 4), help='0 = pas de plafond.')
    seniority_base = fields.Selection(
        [('grade_minimum', 'Minimum du grade'), ('wage', 'Salaire')],
        string='Base de la prime d’ancienneté',
        default='grade_minimum',
        required=True,
        help='Minimum du grade : « salaire de base conventionnel » (tronc commun). Sans grade, le salaire est retenu.',
    )
    grade_ids = fields.One2many('l10n_ga.agreement.grade', 'agreement_id', string='Grille')
    overtime_rate_ids = fields.One2many('l10n_ga.overtime.rate', 'agreement_id', string='Heures supplémentaires')

    _code_company_unique = models.Constraint(
        'UNIQUE(code, company_id)', 'Le code de la convention est unique par société.'
    )

    @api.constrains('seniority_start_years', 'seniority_start_rate', 'seniority_step_rate', 'seniority_max_rate')
    def _check_seniority(self):
        for agreement in self:
            try:
                agreement._seniority_rate(0)
            except ValueError as error:
                raise ValidationError(self.env._('%(name)s : %(detail)s', name=agreement.name, detail=error)) from error

    def _seniority_rate(self, years):
        self.ensure_one()
        return seniority_rate(
            years,
            start_years=self.seniority_start_years,
            start_rate=self.seniority_start_rate,
            step_rate=self.seniority_step_rate,
            max_rate=self.seniority_max_rate,
        )

    def _seniority_rate_at(self, start, on_date):
        """Taux d'ancienneté à ``on_date`` pour une date d'ancienneté ``start``."""
        return self._seniority_rate(completed_years(start, on_date))

    # --- convention par défaut (D-111) ---------------------------------------------------------------

    @api.model
    def _l10n_ga_template(self):
        """Convention « Tronc commun » livrée par le module (données, modifiables par l'utilisateur)."""
        return self.env.ref(TEMPLATE_XMLID, raise_if_not_found=False) or self.browse()

    @api.model
    def _l10n_ga_default_for(self, company):
        """Convention « Tronc commun » de ``company`` : le modèle livré, sinon sa copie pour la société."""
        template = self._l10n_ga_template().sudo()
        if not template or template.company_id == company:
            return template
        existing = self.sudo().search([('company_id', '=', company.id), ('code', '=', template.code)], limit=1)
        if existing:
            return existing
        agreement = template.copy({'company_id': company.id, 'name': template.name})
        for grade in template.grade_ids:
            grade.copy({'agreement_id': agreement.id})
        return agreement

    def _l10n_ga_grade_for_wage(self, wage, on_date):
        """Grade suggéré : le plus élevé de la grille en vigueur à ``on_date`` dont le minimum ≤ ``wage``.

        Aucun grade si le salaire est sous le plus bas minimum (le contrôle RG18 le refuserait).
        """
        self.ensure_one()
        current = {}
        for grade in self.grade_ids.filtered(lambda g: g.date_from <= on_date).sorted('date_from'):
            current[grade.category, grade.echelon or ''] = grade  # dernière valeur en vigueur
        eligible = [grade for grade in current.values() if grade.minimum_wage <= wage]
        return max(eligible, key=lambda g: g.minimum_wage) if eligible else self.env['l10n_ga.agreement.grade']

    def _overtime_tranches(self, period):
        """Tranches ``((de, a, majoration), ...)`` d'une période, triées (``a`` = None sans limite)."""
        self.ensure_one()
        rates = self.overtime_rate_ids.filtered(lambda r: r.period == period).sorted('hours_from')
        return tuple((r.hours_from, r.hours_to or None, r.rate) for r in rates)
