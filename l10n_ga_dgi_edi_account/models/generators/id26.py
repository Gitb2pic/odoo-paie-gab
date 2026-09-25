from odoo import models


class L10nGaDeclarationGeneratorId26(models.AbstractModel):
    """ID26 : sommes versées aux prestataires non assujettis à la TVA et retenues de 9,5 % (art. 182, 189)."""

    _name = 'l10n_ga.declaration.generator.id26'
    _inherit = 'l10n_ga.declaration.generator.fees'
    _description = 'ID26 — prestataires non assujettis à la TVA'

    _kind = 'ras_095'
    _monthly_type = 'ID18'

    @property
    def _sections(self):
        return (('provider', 'PAID_PROVIDER', self.env._('Prestataires de services non assujettis à la TVA')),)

    def _partner_domain(self, declaration):
        return [('l10n_ga_withholding_kind', '=', 'ras_095')]

    def _columns(self):
        env = self.env
        return [
            ('name', env._('Nom, prénom ou raison sociale du prestataire')),
            ('nif', env._('NIF du prestataire')),
            ('paid', env._('Montant versé')),
            ('withheld', env._('Montant de la retenue effectuée')),
        ]
