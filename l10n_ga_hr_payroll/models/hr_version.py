from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..lib.ga_fiscal_core.parts import tax_parts

GA_CODE = 'GA'
# Code nationalité de la DAS (base 06 : 1 Gabonais, 2 CEMAC, 3 autres africains, 4 non africains),
# déterminé par les groupes de pays de data/res_country_group_data.xml (décision D-20).
NATIONALITY_SELECTION = [
    ('1', '1 — Gabonais'),
    ('2', '2 — CEMAC'),
    ('3', '3 — Autres africains'),
    ('4', '4 — Non africains'),
]
TRANSPORT_TRIPS_SELECTION = [('2', '2 trajets par jour'), ('4', '4 trajets par jour')]
PAYMENT_MODE_SELECTION = [('transfer', 'Virement'), ('check', 'Chèque'), ('cash', 'Espèces')]
# Avantages en nature fournis (art. 93, décision D-18) : champ de version → nature du noyau.
BENEFIT_FIELDS = {
    'l10n_ga_benefit_housing': 'housing',
    'l10n_ga_benefit_domestic': 'domestic',
    'l10n_ga_benefit_utilities': 'utilities',
    'l10n_ga_benefit_food': 'food',
}


class HrVersion(models.Model):
    _inherit = 'hr.version'

    # Quotient familial (RG03)
    l10n_ga_disabled_children = fields.Integer(
        string='Enfants infirmes', groups='hr.group_hr_user', tracking=True, help='Parmi les enfants à charge.'
    )
    l10n_ga_extra_half_part = fields.Boolean(
        string='Parts majorées (personne seule)',
        groups='hr.group_hr_user',
        tracking=True,
        help='Personne seule sans enfant à charge ayant élevé des enfants, perdu un enfant de 16 ans ou plus, '
        'ou invalide (CGI art. 170-173).',
    )
    l10n_ga_tax_parts_forced = fields.Float(
        string='Parts forcées',
        digits=(3, 1),
        groups='hr.group_hr_user',
        tracking=True,
        help='0 = parts calculées. Sinon, de 1 à 6,5 par demi-part, avec un motif.',
    )
    l10n_ga_tax_parts_forced_reason = fields.Char(
        string='Motif du forçage des parts', groups='hr.group_hr_user', tracking=True
    )
    l10n_ga_tax_parts = fields.Float(
        string='Parts fiscales',
        digits=(3, 1),
        compute='_compute_l10n_ga_tax_parts',
        store=True,
        groups='hr.group_hr_user',
        help='Calculées avec les paramètres en vigueur à la date de la version ; '
        'le bulletin recalcule à sa date de fin et fige les parts utilisées.',
    )
    # Identifiants et déclarations
    l10n_ga_cnamgs_number = fields.Char(string='N° CNAMGS', groups='hr.group_hr_user', tracking=True)
    l10n_ga_nif = fields.Char(string='NIF', groups='hr.group_hr_user', tracking=True)
    l10n_ga_nationality_code = fields.Selection(
        NATIONALITY_SELECTION,
        string='Code nationalité (DAS)',
        compute='_compute_l10n_ga_nationality_code',
        store=True,
        groups='hr.group_hr_user',
    )
    l10n_ga_job_code = fields.Char(string='Code emploi (DGI)', groups='hr.group_hr_user')
    l10n_ga_level_code = fields.Char(string='Code niveau (DGI)', groups='hr.group_hr_user')
    # Exonérations et avantages en nature
    l10n_ga_transport_trips = fields.Selection(
        TRANSPORT_TRIPS_SELECTION,
        string='Trajets de transport',
        groups='hr.group_hr_user',
        help='Vide : pas d’exonération journalière de l’indemnité de transport (CGI art. 91 bis).',
    )
    l10n_ga_company_car = fields.Boolean(
        string='Véhicule de fonction',
        groups='hr.group_hr_user',
        help='Supprime l’exonération de l’indemnité de véhicule.',
    )
    l10n_ga_benefit_housing = fields.Boolean(string='Logement fourni', groups='hr.group_hr_user')
    l10n_ga_benefit_domestic = fields.Boolean(string='Domesticité fournie', groups='hr.group_hr_user')
    l10n_ga_benefit_utilities = fields.Boolean(string='Eau et électricité fournies', groups='hr.group_hr_user')
    l10n_ga_benefit_food = fields.Boolean(string='Nourriture fournie', groups='hr.group_hr_user')
    # Paiement (F2)
    l10n_ga_payment_mode = fields.Selection(
        PAYMENT_MODE_SELECTION, string='Mode de paiement', default='transfer', groups='hr.group_hr_user'
    )

    def _l10n_ga_benefit_kinds(self):
        """Natures d'avantages en nature fournis, dans l'ordre du noyau."""
        self.ensure_one()
        return tuple(kind for field, kind in BENEFIT_FIELDS.items() if self[field])

    def _l10n_ga_parts(self, params):
        self.ensure_one()
        return tax_parts(
            self.marital,
            self.children,
            self.l10n_ga_disabled_children,
            self.l10n_ga_extra_half_part,
            self.l10n_ga_tax_parts_forced or None,
            p=params,
        )

    @api.depends(
        'marital',
        'children',
        'date_version',
        'company_id',
        'l10n_ga_disabled_children',
        'l10n_ga_extra_half_part',
        'l10n_ga_tax_parts_forced',
    )
    def _compute_l10n_ga_tax_parts(self):
        for version in self:
            params = version.company_id._l10n_ga_fiscal_params(version.date_version or fields.Date.today())
            try:
                version.l10n_ga_tax_parts = version._l10n_ga_parts(params) if params else 0.0
            except ValueError:
                version.l10n_ga_tax_parts = 0.0  # saisie invalide : refusée par _check_l10n_ga_tax_parts

    @api.depends('country_id')
    def _compute_l10n_ga_nationality_code(self):
        cemac = self.env.ref('l10n_ga_hr_payroll.country_group_cemac', raise_if_not_found=False)
        africa = self.env.ref('l10n_ga_hr_payroll.country_group_africa', raise_if_not_found=False)
        for version in self:
            country = version.country_id
            if not country:
                version.l10n_ga_nationality_code = False
            elif country.code == GA_CODE:
                version.l10n_ga_nationality_code = '1'
            elif cemac and country in cemac.country_ids:
                version.l10n_ga_nationality_code = '2'
            elif africa and country in africa.country_ids:
                version.l10n_ga_nationality_code = '3'
            else:
                version.l10n_ga_nationality_code = '4'

    @api.constrains(
        'children',
        'marital',
        'l10n_ga_disabled_children',
        'l10n_ga_tax_parts_forced',
        'l10n_ga_tax_parts_forced_reason',
    )
    def _check_l10n_ga_tax_parts(self):
        for version in self:
            if not 0 <= version.l10n_ga_disabled_children <= version.children:
                raise ValidationError(
                    self.env._(
                        'Le nombre d’enfants infirmes doit être compris entre 0 et le nombre d’enfants à charge.'
                    )
                )
            if not version.l10n_ga_tax_parts_forced:
                continue
            if not (version.l10n_ga_tax_parts_forced_reason or '').strip():
                raise ValidationError(self.env._('Le forçage du nombre de parts fiscales exige un motif.'))
            params = version.company_id._l10n_ga_fiscal_params(version.date_version or fields.Date.today())
            if params:
                try:
                    version._l10n_ga_parts(params)
                except ValueError as error:
                    raise ValidationError(
                        self.env._('Nombre de parts forcé invalide : %(detail)s', detail=error)
                    ) from error
