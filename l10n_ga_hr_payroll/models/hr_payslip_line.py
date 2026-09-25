from odoo import fields, models


class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    # F16 : traitement de la ligne figé à la validation (lu par le bulletin imprimé et la DAS).
    l10n_ga_social_excluded = fields.Monetary(string='Exclu de l’assiette sociale', readonly=True, copy=False)
    l10n_ga_tax_exempt = fields.Monetary(string='Exonéré d’impôt', readonly=True, copy=False)
    # Bulletin imprimé (plan 2.7 b, E3) : base et taux figés à la validation (paramètres du bulletin).
    l10n_ga_base = fields.Float(string='Base imprimée', digits=(16, 2), readonly=True, copy=False)
    l10n_ga_rate = fields.Float(string='Taux imprimé (%)', digits=(6, 3), readonly=True, copy=False)
