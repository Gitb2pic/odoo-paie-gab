from odoo import api, fields, models

FEE_CATEGORIES = [
    ('A', 'A - Administrateurs, commissaires aux comptes'),
    ('B', 'B - Courtiers, autres intermédiaires'),
    ('C', 'C - Avocats, notaires, huissiers, experts-comptables (honoraires)'),
    ('service', 'Prestations de services'),
    ('rent', 'Loyers'),
]
WITHHELD_CATEGORIES = ('A', 'B', 'C', 'service')  # 9,5 % : loyers exclus (ID09, V2.0) — D-101
DAS_FEE_CATEGORIES = ('A', 'B', 'C')  # ID23 : commissions et honoraires (art. 189)
CEMAC = 'l10n_ga_hr_payroll.country_group_cemac'


class ResPartner(models.Model):
    """Classement des bénéficiaires (RG27, F9) : résidence, zone, assujettissement, catégorie."""

    _inherit = 'res.partner'

    l10n_ga_fee_category = fields.Selection(FEE_CATEGORIES, string='Catégorie de bénéficiaire (DGI)')
    l10n_ga_is_resident = fields.Boolean(string='Résident au Gabon', default=True)
    l10n_ga_zone = fields.Selection(
        [('cemac', 'CEMAC'), ('other', 'Hors CEMAC')],
        string='Zone',
        compute='_compute_l10n_ga_zone',
        store=True,
        readonly=False,
        help='Non-résidents (ID24) : déduite du pays, modifiable.',
    )
    l10n_ga_vat_subject = fields.Boolean(string='Assujetti à la TVA', default=True)
    l10n_ga_withholding_kind = fields.Selection(
        [('ras_095', 'RAS 9,5 %'), ('ras_20', 'RAS 20 %')],
        string='Retenue à la source',
        compute='_compute_l10n_ga_withholding_kind',
        store=True,
        help='Non-résident : 20 % seulement ; résident non assujetti à la TVA classé : 9,5 %.',
    )

    @api.depends('country_id', 'l10n_ga_is_resident')
    def _compute_l10n_ga_zone(self):
        cemac = self.env.ref(CEMAC, raise_if_not_found=False)
        for partner in self:
            if partner.l10n_ga_is_resident or not partner.country_id:
                partner.l10n_ga_zone = False
            else:
                partner.l10n_ga_zone = 'cemac' if cemac and partner.country_id in cemac.country_ids else 'other'

    @api.depends('l10n_ga_is_resident', 'l10n_ga_vat_subject', 'l10n_ga_fee_category')
    def _compute_l10n_ga_withholding_kind(self):
        for partner in self:
            if not partner.l10n_ga_is_resident:
                partner.l10n_ga_withholding_kind = 'ras_20'  # jamais cumulée avec le 9,5 % (RG27)
            elif not partner.l10n_ga_vat_subject and partner.l10n_ga_fee_category in WITHHELD_CATEGORIES:
                partner.l10n_ga_withholding_kind = 'ras_095'
            else:
                partner.l10n_ga_withholding_kind = False

    @api.model_create_multi
    def create(self, vals_list):
        partners = super().create(vals_list)
        partners._l10n_ga_apply_withholding_position()
        return partners

    def write(self, vals):
        result = super().write(vals)
        if {'l10n_ga_is_resident', 'l10n_ga_vat_subject', 'l10n_ga_fee_category'} & set(vals):
            self._l10n_ga_apply_withholding_position()
        return result

    def _l10n_ga_apply_withholding_position(self):
        """Position fiscale automatique (D-96) dans chaque société qui a les positions « RAS »."""
        positions = self.env['account.fiscal.position'].sudo().search([('l10n_ga_withholding_kind', '!=', False)])
        for company in positions.company_id:
            company_positions = positions.filtered(lambda p, c=company: p.company_id == c)
            for partner in self.with_company(company).sudo():
                current = partner.property_account_position_id
                wanted = company_positions.filtered(
                    lambda p, k=partner.l10n_ga_withholding_kind: p.l10n_ga_withholding_kind == k
                )[:1]
                if wanted and current != wanted:
                    partner.property_account_position_id = wanted
                elif not wanted and current in company_positions:
                    partner.property_account_position_id = False

    def _l10n_ga_is_employee(self, company):
        """Bénéficiaire de « qualité de salarié » (ID23, D-98) : contact de travail d'un salarié de la société."""
        self.ensure_one()
        return bool(
            self.env['hr.employee']
            .sudo()
            .with_context(active_test=False)
            .search_count([('work_contact_id', '=', self.id), ('company_id', '=', company.id)], limit=1)
        )
