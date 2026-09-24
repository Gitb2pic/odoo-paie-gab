from odoo import fields, models


class L10nGaCheckIssue(models.Model):
    """Anomalie de contrôle (F8, ADR-18) : modèle unique, périmètre lot de paie ici.

    ``l10n_ga_dgi_edi`` ajoute le périmètre « déclaration » par ``_inherit``. Les anomalies d'un
    lot sont recréées à chaque contrôle (RG26) ; elles ne se saisissent pas.
    """

    _name = 'l10n_ga.check.issue'
    _description = 'Anomalie de contrôle (Gabon)'
    _order = 'severity, code, id'
    _check_company_auto = True

    company_id = fields.Many2one('res.company', string='Société', required=True, index=True, readonly=True)
    scope = fields.Selection([('payslip_run', 'Lot de paie')], string='Périmètre', required=True, readonly=True)
    payslip_run_id = fields.Many2one(
        'hr.payslip.run',
        string='Lot de paie',
        ondelete='cascade',
        index='btree_not_null',
        readonly=True,
        check_company=True,
    )
    payslip_id = fields.Many2one(
        'hr.payslip', string='Bulletin', ondelete='cascade', index='btree_not_null', readonly=True, check_company=True
    )
    employee_id = fields.Many2one('hr.employee', string='Salarié', readonly=True, check_company=True)
    severity = fields.Selection(
        [('blocking', 'Bloquante'), ('warning', 'Avertissement')], string='Gravité', required=True, readonly=True
    )
    code = fields.Char(required=True, readonly=True)
    message = fields.Text(required=True, readonly=True)
    res_model = fields.Char(string='Modèle concerné', readonly=True)
    res_id = fields.Many2oneReference(string='Enregistrement concerné', model_field='res_model', readonly=True)

    def action_open_record(self):
        """Ouvre l'enregistrement à corriger (salarié, version, indemnité…)."""
        self.ensure_one()
        return self.env[self.res_model].browse(self.res_id)._get_records_action(target='new')
