from odoo import models


class L10nGaDeclarationGeneratorId24(models.AbstractModel):
    """ID24 : commissions et honoraires versés hors du Gabon (art. 189), CEMAC / hors CEMAC, retenue 20 %."""

    _name = 'l10n_ga.declaration.generator.id24'
    _inherit = 'l10n_ga.declaration.generator.fees'
    _description = 'ID24 — sommes versées hors du Gabon'

    _kind = 'ras_20'
    _monthly_type = 'ID27'
    _nif_required = False

    @property
    def _sections(self):
        return (
            ('cemac', 'PAID_CEMAC', self.env._('A) Bénéficiaires de la CEMAC')),
            ('other', 'PAID_OTHER', self.env._('B) Bénéficiaires hors CEMAC')),
        )

    def _partner_domain(self, declaration):
        return [('l10n_ga_is_resident', '=', False), ('l10n_ga_fee_category', '!=', False)]

    def _section(self, declaration, partner):
        return 'cemac' if partner.l10n_ga_zone == 'cemac' else 'other'

    def _columns(self):
        env = self.env
        return [
            ('name', env._('Nom, prénom ou raison sociale')),
            ('address', env._('Adresse du bénéficiaire')),
            ('paid', env._('Montant versé')),
            ('withheld', env._('Retenue à la source effectuée')),
        ]
