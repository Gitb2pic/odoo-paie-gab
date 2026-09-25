from odoo import models

from ..res_partner import DAS_FEE_CATEGORIES


class L10nGaDeclarationGeneratorId23(models.AbstractModel):
    """ID23 : commissions et honoraires versés au Gabon (art. 189), salariés (A) et non-salariés (B)."""

    _name = 'l10n_ga.declaration.generator.id23'
    _inherit = 'l10n_ga.declaration.generator.fees'
    _description = 'ID23 — commissions et honoraires versés au Gabon'

    @property
    def _sections(self):
        return (
            ('employee', 'PAID_EMPLOYEE', self.env._('A) Bénéficiaires ayant la qualité de salarié')),
            ('other', 'PAID_OTHER', self.env._('B) Bénéficiaires n’ayant pas la qualité de salarié')),
        )

    def _partner_domain(self, declaration):
        return [('l10n_ga_is_resident', '=', True), ('l10n_ga_fee_category', 'in', DAS_FEE_CATEGORIES)]

    def _section(self, declaration, partner):
        return 'employee' if partner._l10n_ga_is_employee(declaration.company_id) else 'other'
