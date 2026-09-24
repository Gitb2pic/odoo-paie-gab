from itertools import pairwise

from odoo import api, fields, models
from odoo.exceptions import ValidationError

OVERTIME_PERIOD_SELECTION = [
    ('day', 'Jour'),
    ('night', 'Nuit'),
    ('sunday', 'Dimanche'),
    ('holiday', 'Jour férié'),
]


class L10nGaOvertimeRate(models.Model):
    """Majoration d'heures supplémentaires par tranche mensuelle (base 05 §3, point 09-11, D-24).

    Aucune valeur par défaut : les taux viennent de la convention du client.
    """

    _name = 'l10n_ga.overtime.rate'
    _description = 'Taux d’heures supplémentaires (Gabon)'
    _order = 'agreement_id, period, hours_from'
    _check_company_auto = True

    agreement_id = fields.Many2one(
        'l10n_ga.collective.agreement', string='Convention', required=True, ondelete='cascade', index=True
    )
    company_id = fields.Many2one(related='agreement_id.company_id', store=True, index=True)
    period = fields.Selection(OVERTIME_PERIOD_SELECTION, string='Période', required=True)
    hours_from = fields.Float(string='De (heures du mois)', required=True)
    hours_to = fields.Float(string='À (heures du mois)', help='0 = sans limite.')
    rate = fields.Float(string='Majoration', digits=(5, 4), required=True, help='0,25 = +25 %.')

    _hours_positive = models.Constraint(
        'CHECK(hours_from >= 0 AND hours_to >= 0 AND rate >= 0)', 'Heures et majoration positives.'
    )

    @api.constrains('agreement_id', 'period', 'hours_from', 'hours_to')
    def _check_tranches(self):
        for agreement in self.agreement_id:
            for period, _label in OVERTIME_PERIOD_SELECTION:
                tranches = agreement._overtime_tranches(period)
                for (_start, end, _rate), (next_start, _end, _next) in pairwise(tranches):
                    if end is None or end > next_start:
                        raise ValidationError(
                            self.env._(
                                '%(name)s : tranches d’heures supplémentaires qui se chevauchent.', name=agreement.name
                            )
                        )
                for start, end, _rate in tranches:
                    if end is not None and end <= start:
                        raise ValidationError(self.env._('Une tranche doit finir après son début.'))
