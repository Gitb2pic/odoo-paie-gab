from odoo import api, fields, models
from odoo.exceptions import ValidationError

from ..lib.ga_fiscal_core.treatment import check_treatment

# Clés = vocabulaire du noyau (ga_fiscal_core.treatment), vérifié par test_rule_codes_unique.
SOCIAL_BASE_SELECTION = [
    ('subject', 'Soumise'),
    ('excluded', 'Exclue'),
    ('capped', 'Exclue dans la limite d’un plafond'),
    ('none', 'Hors assiette'),
]
TAX_BASE_SELECTION = [
    ('taxable', 'Imposable'),
    ('exempt', 'Exonérée'),
    ('capped', 'Exonérée dans la limite d’un plafond'),
    ('none', 'Hors assiette'),
]
DAS_COLUMN_SELECTION = [
    ('presence', '(1) Salaire brut de présence'),
    ('benefit', '(2) Avantages en nature'),
    ('food', '(3) Nourriture'),
    ('taxable_allowance', '(4) Indemnités imposables'),
    ('leave', '(5) Salaire brut de congé'),
    ('nt_housing', 'Non imposable : logement'),
    ('nt_transport', 'Non imposable : transport'),
    ('nt_domestic', 'Non imposable : domesticité, gaz'),
    ('nt_other', 'Non imposable : autres'),
    ('none', 'Hors DAS'),
]


class HrSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    # Traitement social et fiscal de la rubrique (ADR-17, catalogue F6, décision D-16)
    l10n_ga_social_base = fields.Selection(SOCIAL_BASE_SELECTION, string='Assiette sociale (Gabon)')
    l10n_ga_social_cap_group = fields.Char(
        string='Groupe de plafond social',
        help='Code d’un groupe du registre SOCIAL_CAPS du noyau (ex. TRANSPORT_35K).',
    )
    l10n_ga_tax_base = fields.Selection(TAX_BASE_SELECTION, string='Assiette fiscale (Gabon)')
    l10n_ga_tax_cap_group = fields.Char(
        string='Groupe de plafond fiscal',
        help='Code d’un groupe du registre TAX_CAPS du noyau (ex. BONUS_4M).',
    )
    l10n_ga_prorate = fields.Boolean(string='Proratisée par la présence')
    l10n_ga_leave_base = fields.Boolean(string='Base de l’allocation de congé')
    l10n_ga_severance_base = fields.Boolean(string='Base des indemnités de rupture')
    l10n_ga_das_column = fields.Selection(DAS_COLUMN_SELECTION, string='Colonne DAS (part imposable)')
    l10n_ga_das_exempt_column = fields.Selection(DAS_COLUMN_SELECTION, string='Colonne DAS (part exonérée)')

    @api.constrains('l10n_ga_social_base', 'l10n_ga_social_cap_group', 'l10n_ga_tax_base', 'l10n_ga_tax_cap_group')
    def _check_l10n_ga_treatment(self):
        for rule in self:
            values = (
                rule.l10n_ga_social_base,
                rule.l10n_ga_social_cap_group,
                rule.l10n_ga_tax_base,
                rule.l10n_ga_tax_cap_group,
            )
            if not any(values):
                continue  # règle hors localisation gabonaise
            try:
                check_treatment(rule.code, *values)
            except ValueError as error:
                raise ValidationError(
                    self.env._('Traitement social ou fiscal incohérent : %(detail)s', detail=error)
                ) from error
