from odoo import fields, models


class L10nGaDeclarationDetail(models.Model):
    """Justification d'une case (RG13) : un salarié ou un tiers, et les lignes de bulletin qui la composent.

    ``move_line_ids`` (lignes d'écriture) est ajouté par ``l10n_ga_dgi_edi_account`` (D-73).
    """

    _name = 'l10n_ga.declaration.detail'
    _inherit = 'l10n_ga.declaration.frozen.mixin'
    _description = 'Détail de déclaration (Gabon)'
    _order = 'declaration_id, box_id, label, id'
    _check_company_auto = True

    declaration_id = fields.Many2one(
        'l10n_ga.declaration', string='Déclaration', required=True, ondelete='cascade', index=True
    )
    company_id = fields.Many2one(related='declaration_id.company_id', store=True, index=True)
    currency_id = fields.Many2one(related='declaration_id.currency_id')
    box_id = fields.Many2one('l10n_ga.declaration.box', string='Case', ondelete='restrict')
    employee_id = fields.Many2one('hr.employee', string='Salarié', readonly=True, check_company=True)
    partner_id = fields.Many2one('res.partner', string='Tiers', readonly=True)
    label = fields.Char(string='Libellé', readonly=True, help='Nom figé au calcul.')
    amount = fields.Monetary(string='Montant', readonly=True)
    payload = fields.Json(string='Colonnes', readonly=True)
    payslip_line_ids = fields.Many2many(
        'hr.payslip.line',
        'l10n_ga_declaration_detail_payslip_line_rel',
        'detail_id',
        'payslip_line_id',
        string='Lignes de bulletin',
        readonly=True,
    )
