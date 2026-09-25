from odoo import fields, models

AUTO_VALUES = [
    ('company_name', 'Raison sociale'),
    ('company_nif', 'NIF de la société'),
    ('company_cnss', 'N° employeur CNSS'),
    ('company_cnamgs', 'N° employeur CNAMGS'),
    ('period_month', 'Mois de la période'),
    ('period_year', 'Année de la période'),
    ('date_from', 'Début de période'),
    ('date_to', 'Fin de période'),
]


class L10nGaDeclarationBox(models.Model):
    """Case d'un imprimé (RG10) : où et comment une valeur s'inscrit dans le gabarit."""

    _name = 'l10n_ga.declaration.box'
    _description = 'Case de déclaration (Gabon)'
    _order = 'type_id, sequence, id'

    type_id = fields.Many2one(
        'l10n_ga.declaration.type', string='Imprimé', required=True, ondelete='cascade', index=True
    )
    code = fields.Char(required=True)
    name = fields.Char(string='Libellé', required=True, translate=True)
    sequence = fields.Integer(default=10)
    cell_ref = fields.Char(string='Cellule', help='Cellule du gabarit : « P40 » (1re feuille) ou « Feuille!P40 ».')
    value_kind = fields.Selection(
        [('amount', 'Montant'), ('number', 'Nombre'), ('rate', 'Taux'), ('text', 'Texte'), ('date', 'Date')],
        string='Nature',
        required=True,
        default='amount',
    )
    is_total = fields.Boolean(string='Total dû', help='Additionnée dans le total de la déclaration.')
    auto_value = fields.Selection(
        AUTO_VALUES, string='Valeur automatique', help='Case d’en-tête remplie par le moteur (identité, période).'
    )
    source_codes = fields.Char(
        string='Rubriques sources',
        help='Codes de rubriques de paie additionnés par le générateur générique, séparés par des virgules.',
    )
    negate = fields.Boolean(
        string='Inverser le signe',
        help='Retenues : les lignes de bulletin sont négatives, la case déclare le montant positif.',
    )

    _code_unique = models.Constraint('unique (type_id, code)', 'Une case a un code unique par type de déclaration.')

    def _source_codes(self):
        self.ensure_one()
        return [code.strip() for code in (self.source_codes or '').split(',') if code.strip()]
