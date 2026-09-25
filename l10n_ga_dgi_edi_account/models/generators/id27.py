from odoo import models


class L10nGaDeclarationGeneratorId27(models.AbstractModel):
    """ID27 : retenue à la source sur les sommes versées aux non-résidents (art. 206 CGI)."""

    _name = 'l10n_ga.declaration.generator.id27'
    _inherit = 'l10n_ga.declaration.generator.withholding'
    _description = 'ID27 — retenue à la source 20 % sur non-résidents'

    _kind = 'ras_20'
    _nif_required = False
    _layout = (('Bordereau 1', 33, 10, ('A', 'E', 'J', 'O'), 43),)

    def _row(self, detail):
        payload = detail.payload or {}
        return [payload.get('name'), payload.get('country'), payload.get('base'), payload.get('withheld')]
