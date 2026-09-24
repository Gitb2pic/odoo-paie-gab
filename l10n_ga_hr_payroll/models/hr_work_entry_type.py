from odoo import fields, models


class HrWorkEntryType(models.Model):
    _inherit = 'hr.work.entry.type'

    # F4 : indicateur des absences gabonaises. « Non rémunéré » est en outre porté par le
    # mécanisme standard unpaid_structure_ids (E/hr_payroll/models/hr_work_entry_type.py:29).
    l10n_ga_pay_mode = fields.Selection(
        [
            ('paid', 'Rémunéré'),
            ('unpaid', 'Non rémunéré'),
            ('cnss', 'Pris en charge par la CNSS'),
        ],
        string='Rémunération (Gabon)',
        help='Maternité et accident du travail : indemnités journalières CNSS (subrogation possible).',
    )
