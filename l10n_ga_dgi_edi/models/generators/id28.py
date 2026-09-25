from odoo import models

from ..declaration_generator import BLOCKING
from .id10 import cfp_rounding_check


class L10nGaDeclarationGeneratorId28(models.AbstractModel):
    """ID28 : CFP déclarée séparément (base 06 §2), seulement si la société a choisi cet imprimé (D-76)."""

    _name = 'l10n_ga.declaration.generator.id28'
    _inherit = 'l10n_ga.declaration.generator.payslip'
    _description = 'ID28 — contribution à la formation professionnelle'

    def _applies(self, company):
        return company.l10n_ga_cfp_declaration == 'id28'

    def _checks(self, declaration, facts):
        issues = super()._checks(declaration, facts) + cfp_rounding_check(self, declaration, facts)
        if not self._applies(declaration.company_id):
            message = declaration.env._(
                'La société déclare la CFP sur l’ID10 : l’ID28 la déclarerait une seconde fois.'
            )
            issues.append((BLOCKING, 'GA_ID28_CFP_ON_ID10', message, declaration.company_id))
        return issues
