from odoo import fields, models

AUTO_VALUES = [
    ('company_name', 'Raison sociale'),
    ('company_nif', 'NIF de la société'),
    ('company_cnss', 'N° employeur CNSS'),
    ('company_cnamgs', 'N° employeur CNAMGS'),
    ('company_street', 'Adresse / boîte postale'),
    ('company_city', 'Ville'),
    ('company_phone', 'Téléphone'),
    ('company_email', 'Adresse e-mail'),
    ('company_website', 'Site Internet'),
    ('company_tax_center', 'Code résidence (centre des impôts)'),
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
        help='Codes de rubriques additionnés par le générateur générique, séparés par des virgules ; '
        '« -CODE » inverse le signe (retenue négative sur le bulletin, déclarée en positif).',
    )
    source_categories = fields.Char(
        string='Catégories sources',
        help='Codes de catégories de rubriques additionnées (ex. ALW, GA_AIK), même syntaxe que les rubriques.',
    )
    source_measure = fields.Selection(
        [
            ('total', 'Montant de la ligne'),
            ('base', 'Base figée de la ligne'),
            ('cfp', 'Part retenue dans l’assiette CFP'),
        ],
        string='Mesure',
        default='total',
        required=True,
        help='Base figée : base imprimée à la validation (base plafonnée). Part CFP : montant moins la part '
        'exclue de l’assiette sociale, ou montant entier si la société a choisi l’assiette « brut ».',
    )
    sum_box_codes = fields.Char(
        string='Somme des cases', help='Case égale à la somme d’autres cases (codes séparés par des virgules).'
    )
    parameter_code = fields.Char(
        string='Paramètre daté', help='Case égale à la valeur du paramètre de paie à la fin de période (ex. taux).'
    )
    section = fields.Char(string='Cadre', help='Groupe de cases qu’un imprimé peut laisser vide (ex. cfp).')

    _code_unique = models.Constraint('unique (type_id, code)', 'Une case a un code unique par type de déclaration.')

    @staticmethod
    def _signed(text):
        """« A, -B » → [('A', 1), ('B', -1)]."""
        items = []
        for raw in (text or '').split(','):
            item = raw.strip()
            if item:
                items.append((item[1:].strip(), -1) if item.startswith('-') else (item, 1))
        return items

    def _source_codes(self):
        self.ensure_one()
        return self._signed(self.source_codes)

    def _source_categories(self):
        self.ensure_one()
        return self._signed(self.source_categories)

    def _sum_box_codes(self):
        self.ensure_one()
        return self._signed(self.sum_box_codes)

    def _has_source(self):
        self.ensure_one()
        return bool(self._source_codes() or self._source_categories())
