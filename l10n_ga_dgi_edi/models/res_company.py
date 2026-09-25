from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_ga_declarant_id = fields.Many2one(
        'res.users',
        string='Déclarant fiscal',
        help='Destinataire des activités d’échéance et de correction des déclarations (D-72). '
        'À défaut : premier membre du groupe « Déclarant fiscal » de la société.',
    )
