from odoo import fields, models


class L10nGaDeclarationLine(models.Model):
    """Valeur d'une case (RG12) : une par case et par déclaration."""

    _name = 'l10n_ga.declaration.line'
    _inherit = 'l10n_ga.declaration.frozen.mixin'
    _description = 'Valeur de case de déclaration (Gabon)'
    _order = 'declaration_id, sequence, id'

    declaration_id = fields.Many2one(
        'l10n_ga.declaration', string='Déclaration', required=True, ondelete='cascade', index=True
    )
    company_id = fields.Many2one(related='declaration_id.company_id', store=True, index=True)
    currency_id = fields.Many2one(related='declaration_id.currency_id')
    box_id = fields.Many2one('l10n_ga.declaration.box', string='Case', required=True, ondelete='restrict')
    sequence = fields.Integer(related='box_id.sequence', store=True)
    code = fields.Char(related='box_id.code', store=True)
    name = fields.Char(related='box_id.name')
    value_kind = fields.Selection(related='box_id.value_kind')
    is_total = fields.Boolean(related='box_id.is_total', store=True)
    value_amount = fields.Monetary(string='Montant', readonly=True)
    value_number = fields.Float(string='Nombre / taux', digits=(16, 6), readonly=True)
    value_text = fields.Char(string='Texte', readonly=True)
    value_date = fields.Date(string='Date', readonly=True)
    value_blank = fields.Boolean(string='Non renseignée', readonly=True, help='Case laissée vide sur l’imprimé.')

    _box_unique = models.Constraint(
        'unique (declaration_id, box_id)', 'Une case n’a qu’une valeur par déclaration (RG12).'
    )

    def _value(self):
        """Valeur typée de la case, lue sur les champs stockés (rendus Excel et PDF)."""
        self.ensure_one()
        if self.value_blank:
            return None
        kind = self.box_id.value_kind
        if kind == 'amount':
            return self.value_amount
        if kind in ('number', 'rate'):
            return self.value_number
        if kind == 'date':
            return self.value_date
        return self.value_text or ''
