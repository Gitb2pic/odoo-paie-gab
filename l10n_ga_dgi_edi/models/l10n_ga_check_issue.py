from odoo import fields, models


class L10nGaCheckIssue(models.Model):
    """Périmètre « déclaration » ajouté au modèle unique d'anomalies (ADR-18, RG15, RG26)."""

    _inherit = 'l10n_ga.check.issue'

    scope = fields.Selection(selection_add=[('declaration', 'Déclaration')], ondelete={'declaration': 'cascade'})
    declaration_id = fields.Many2one(
        'l10n_ga.declaration',
        string='Déclaration',
        ondelete='cascade',
        index='btree_not_null',
        readonly=True,
        check_company=True,
    )
