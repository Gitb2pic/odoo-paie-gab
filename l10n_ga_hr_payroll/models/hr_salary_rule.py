from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools import float_round

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
    # Bulletin imprimé (plan 2.7 b, D-54) : code numérique (ordre et section), libellé de la ligne d'organisme.
    l10n_ga_print_code = fields.Char(
        string='Code imprimé', help='Parts salariale et patronales d’un organisme : même code.'
    )
    l10n_ga_print_name = fields.Char(string='Libellé imprimé', help='Libellé de la ligne (vide : nom de la rubrique).')
    l10n_ga_core_value = fields.Char(
        string='Valeur du noyau',
        help='Montant de PayResult lu par la règle (ex. irpp, benefit:housing) : contrôlé à la validation du bulletin.',
    )

    def _l10n_ga_sign(self):
        """-1 pour une retenue (catégorie DED ou descendante), 1 sinon : signe de la ligne."""
        self.ensure_one()
        deduction = self.env.ref('hr_payroll.DED')
        category = self.category_id
        while category:
            if category == deduction:
                return -1
            category = category.parent_id
        return 1

    def _compute_rule(self, localdict):
        """Proratisation par la présence payée (sprint 0 point 12, décision D-21), arrondie au franc."""
        amount, qty, rate = super()._compute_rule(localdict)
        if self.l10n_ga_prorate and amount:
            ratio = localdict['payslip']._l10n_ga_paid_ratio()
            amount = float_round(amount * ratio, precision_digits=0)
        return amount, qty, rate

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
