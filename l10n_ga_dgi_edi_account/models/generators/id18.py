from odoo import models


class L10nGaDeclarationGeneratorId18(models.AbstractModel):
    """ID18 : précomptes de 9,5 % sur les prestations des non-assujettis à la TVA (art. 182 CGI)."""

    _name = 'l10n_ga.declaration.generator.id18'
    _inherit = 'l10n_ga.declaration.generator.withholding'
    _description = 'ID18 — précompte IRPP 9,5 % sur prestations'

    _kind = 'ras_095'
    _layout = (
        ('Bordereau', 32, 10, ('A', 'B', 'M', 'O'), None),
        ('2- Listes ', 12, 39, ('A', 'B', 'F', 'G'), 51),
        ('2 - Listes suite 1', 10, 40, ('A', 'B', 'F', 'G'), 50),
    )
