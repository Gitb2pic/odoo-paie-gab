from odoo import fields, models


class HrWorkEntry(models.Model):
    _inherit = 'hr.work.entry'

    l10n_ga_imported = fields.Boolean(
        string='Importée', readonly=True, help='Heures créées par l’import Excel des variables (F3, D-43).'
    )
