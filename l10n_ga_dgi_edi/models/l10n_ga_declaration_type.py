import calendar
from datetime import date

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.misc import file_open

PERIOD_MONTHS = {'monthly': 1, 'quarterly': 3, 'yearly': 12}


class L10nGaDeclarationType(models.Model):
    """Type d'imprimé (RG10, ADR-07) : donnée partagée par toutes les sociétés, comme une structure de paie.

    Ajouter un imprimé = un enregistrement de type + ses cases + un générateur (clé du registre),
    sans modifier le moteur.
    """

    _name = 'l10n_ga.declaration.type'
    _description = 'Type de déclaration (Gabon)'
    _order = 'sequence, code'

    code = fields.Char(required=True)
    name = fields.Char(string='Libellé', required=True, translate=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    authority = fields.Selection(
        [('dgi', 'DGI'), ('cnss', 'CNSS'), ('cnamgs', 'CNAMGS')], string='Organisme', required=True, default='dgi'
    )
    periodicity = fields.Selection(
        [('monthly', 'Mensuelle'), ('quarterly', 'Trimestrielle'), ('yearly', 'Annuelle')],
        string='Périodicité',
        required=True,
        default='monthly',
    )
    period_basis = fields.Selection(
        [('payment_date', 'Date de paiement'), ('period', 'Période de paie')],
        string='Base de période',
        required=True,
        default='payment_date',
        help='Rattachement des bulletins : date de paiement (ID10, base 02 §3) ou date de fin de période.',
    )
    due_months = fields.Integer(
        string='Échéance : mois après la période',
        default=1,
        help='Échéance = fin de période + N mois, au jour indiqué (ID10 : 1 mois, le 15 ; DAS : 4 mois, le 30).',
    )
    due_day = fields.Integer(string='Échéance : jour du mois', default=15)
    lead_days = fields.Integer(
        string='Préparation (jours avant échéance)', default=10, help='Le cron prépare la déclaration J-N.'
    )
    auto_create = fields.Boolean(
        string='Préparation automatique',
        default=True,
        help='Créée et recalculée à la validation des bulletins et par le cron des échéances (ADR-10).',
    )
    prepare_on_payslip = fields.Boolean(
        string='Préparée à chaque bulletin',
        default=True,
        help='Sinon, préparée seulement par le cron des échéances ou à la demande (DAS annuelle).',
    )
    generator_key = fields.Char(string='Générateur', required=True, help='Clé du registre des générateurs.')
    template_path = fields.Char(
        string='Gabarit Excel',
        help='Chemin du gabarit dans un module (ex. l10n_ga_dgi_edi/static/templates/ID10.xlsx). '
        'Sans gabarit, un classeur neuf est produit.',
    )
    report_id = fields.Many2one(
        'ir.actions.report', string='Rapport PDF', domain=[('model', '=', 'l10n_ga.declaration')]
    )
    active_from = fields.Date(string='Valide du')
    active_to = fields.Date(string='Valide au')
    box_ids = fields.One2many('l10n_ga.declaration.box', 'type_id', string='Cases', copy=True)

    _code_unique = models.Constraint('unique (code)', 'Le code du type de déclaration doit être unique.')
    _dates_check = models.Constraint(
        'CHECK (active_to IS NULL OR active_from IS NULL OR active_to >= active_from)',
        'La fin de validité doit suivre le début.',
    )
    _due_day_check = models.Constraint(
        'CHECK (due_day BETWEEN 1 AND 31)', 'Le jour d’échéance doit être compris entre 1 et 31.'
    )

    @api.constrains('generator_key')
    def _check_generator_key(self):
        registry = self.env['l10n_ga.declaration.generator']
        for decl_type in self:
            if not registry._has(decl_type.generator_key):
                raise ValidationError(
                    self.env._('Générateur « %(key)s » inconnu du registre.', key=decl_type.generator_key)
                )

    def _is_active_on(self, day):
        self.ensure_one()
        return (not self.active_from or self.active_from <= day) and (not self.active_to or self.active_to >= day)

    def _period_bounds(self, day):
        """Période (début, fin) de la périodicité du type qui contient ``day``."""
        self.ensure_one()
        months = PERIOD_MONTHS[self.periodicity]
        first_month = (day.month - 1) // months * months + 1
        start = date(day.year, first_month, 1)
        end = start + relativedelta(months=months, days=-1)
        return start, end

    def _due_date(self, date_to):
        """Échéance : fin de période + ``due_months`` mois, jour borné au dernier jour du mois (D-67)."""
        self.ensure_one()
        target = date_to + relativedelta(day=1, months=self.due_months)
        last_day = calendar.monthrange(target.year, target.month)[1]
        return target.replace(day=min(self.due_day, last_day))

    def _template_bytes(self):
        self.ensure_one()
        if not self.template_path:
            return None
        with file_open(self.template_path, 'rb', env=self.env) as template:
            return template.read()
