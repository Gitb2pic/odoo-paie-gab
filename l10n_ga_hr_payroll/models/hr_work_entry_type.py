from odoo import fields, models

from .l10n_ga_overtime_rate import OVERTIME_PERIOD_SELECTION


class HrWorkEntryType(models.Model):
    _inherit = 'hr.work.entry.type'

    # F4 : indicateur des absences gabonaises. « Non rémunéré » est en outre porté par le
    # mécanisme standard unpaid_structure_ids (E/hr_payroll/models/hr_work_entry_type.py:29).
    l10n_ga_pay_mode = fields.Selection(
        [
            ('paid', 'Rémunéré'),
            ('allowance', 'Payé par l’allocation de congé'),
            ('unpaid', 'Non rémunéré'),
            ('cnss', 'Pris en charge par la CNSS'),
        ],
        string='Rémunération (Gabon)',
        help='Congé payé : hors salaire de base, payé par l’allocation de congé. Maternité et accident du '
        'travail : indemnités journalières CNSS ; salaire maintenu si la société pratique la subrogation.',
    )
    # Heures supplémentaires : période de la table de majoration de la convention (D-24).
    l10n_ga_overtime_period = fields.Selection(OVERTIME_PERIOD_SELECTION, string='Période d’heures supplémentaires')
