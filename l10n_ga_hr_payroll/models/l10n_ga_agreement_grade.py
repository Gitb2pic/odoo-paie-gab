from odoo import api, fields, models


class L10nGaAgreementGrade(models.Model):
    """Grille conventionnelle (F5, RG18) : une ligne par catégorie, échelon et date d'effet."""

    _name = 'l10n_ga.agreement.grade'
    _description = 'Grade de convention (Gabon)'
    _order = 'agreement_id, category, echelon, date_from desc'
    _check_company_auto = True

    agreement_id = fields.Many2one(
        'l10n_ga.collective.agreement', string='Convention', required=True, ondelete='cascade', index=True
    )
    company_id = fields.Many2one(related='agreement_id.company_id', store=True, index=True)
    category = fields.Char(string='Catégorie', required=True)
    echelon = fields.Char(string='Échelon')
    date_from = fields.Date(string='Date d’effet', required=True)
    currency_id = fields.Many2one(related='company_id.currency_id')
    minimum_wage = fields.Monetary(string='Salaire minimum mensuel', required=True)
    hourly_rate = fields.Monetary(string='Taux horaire')

    _grade_unique = models.Constraint(
        'UNIQUE(agreement_id, category, echelon, date_from)',
        'Un grade (catégorie, échelon) n’a qu’une valeur par date d’effet.',
    )

    @api.depends('category', 'echelon', 'date_from')
    def _compute_display_name(self):
        for grade in self:
            label = ' / '.join(filter(None, (grade.category, grade.echelon)))
            grade.display_name = f'{label} ({grade.date_from:%d/%m/%Y})' if grade.date_from else label

    def _applicable(self, on_date):
        """Valeur du même grade (convention, catégorie, échelon) en vigueur à ``on_date`` (RG06)."""
        self.ensure_one()
        return self.search(
            [
                ('agreement_id', '=', self.agreement_id.id),
                ('category', '=', self.category),
                ('echelon', '=', self.echelon),
                ('date_from', '<=', on_date),
            ],
            order='date_from desc',
            limit=1,
        )
