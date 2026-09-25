from datetime import date

from odoo import fields, models


class L10nGaDasWizard(models.TransientModel):
    """Préparer la DAS d'une année (ID19 à ID22) et ouvrir ses anomalies (écran « Contrôle DAS »)."""

    _name = 'l10n_ga.das.wizard'
    _description = 'Préparation de la DAS (Gabon)'

    company_id = fields.Many2one('res.company', string='Société', required=True, default=lambda self: self.env.company)
    year = fields.Integer(string='Année', required=True, default=lambda self: fields.Date.context_today(self).year - 1)

    def _declaration(self):
        self.ensure_one()
        return self.env['l10n_ga.declaration']._l10n_ga_prepare(
            self.company_id,
            self.env.ref('l10n_ga_dgi_edi.declaration_type_das'),
            date(self.year, 1, 1),
            date(self.year, 12, 31),
        )

    def action_prepare(self):
        """Crée ou recalcule la DAS (une DAS validée n'est jamais recalculée) et l'ouvre."""
        declaration = self._declaration()
        return declaration.with_env(self.env)._get_records_action(name=declaration.name)

    def action_open_checks(self):
        declaration = self._declaration()
        return {
            'type': 'ir.actions.act_window',
            'name': self.env._('Contrôle DAS %(year)s', year=self.year),
            'res_model': 'l10n_ga.check.issue',
            'view_mode': 'list,form',
            'views': [
                (self.env.ref('l10n_ga_dgi_edi.l10n_ga_check_issue_view_list_declaration').id, 'list'),
                (False, 'form'),
            ],
            'domain': [('declaration_id', '=', declaration.id)],
        }
