from odoo import fields, models


class L10nGaDeclarationDetail(models.Model):
    """Justification comptable d'un détail (RG13, D-73) : lignes d'écriture des paiements et factures."""

    _inherit = 'l10n_ga.declaration.detail'

    move_line_ids = fields.Many2many(
        'account.move.line',
        'l10n_ga_declaration_detail_move_line_rel',
        'detail_id',
        'move_line_id',
        string='Lignes d’écriture',
        readonly=True,
    )
