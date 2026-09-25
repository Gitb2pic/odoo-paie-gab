from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_ga_declarant_id = fields.Many2one(
        'res.users',
        string='Déclarant fiscal',
        help='Destinataire des activités d’échéance et de correction des déclarations (D-72). '
        'À défaut : premier membre du groupe « Déclarant fiscal » de la société.',
    )
    # Point 09-6 (base 06 §3.1) : hypothèses par défaut documentées, modifiables par société (règle d'or 13).
    l10n_ga_das_presence_net = fields.Boolean(
        string='DAS : salaire de présence net des cotisations',
        default=True,
        help='Colonne (1) de l’ID21 après déduction des cotisations salariales CNSS et CNAMGS (remarque DGI de '
        'l’ID19). Décocher pour déclarer le brut.',
    )
    l10n_ga_das_average_basis = fields.Selection(
        [('taxable', 'Rémunérations imposables'), ('all', 'Imposables et non imposables')],
        string='DAS : base de la moyenne mensuelle',
        default='taxable',
        help='Moyenne servant au classement ID20 (< / ≥ 1 000 000) et au seuil de l’ID19.',
    )
