from odoo import fields, models


class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    # F16 : traitement de la ligne figé à la validation (lu par le bulletin imprimé et la DAS).
    l10n_ga_social_excluded = fields.Monetary(string='Exclu de l’assiette sociale', readonly=True, copy=False)
    l10n_ga_tax_exempt = fields.Monetary(string='Exonéré d’impôt', readonly=True, copy=False)
