"""Fabrique des tests Odoo de la paie gabonaise : société, salariés, bulletins (aucune donnée de démo)."""

from datetime import date, datetime, time

from odoo.tests import TransactionCase

from ..lib.ga_fiscal_core.engine import PayslipFacts, compute
from ..lib.ga_fiscal_core.exemptions import GainLine
from ..lib.ga_fiscal_core.labour import GAIN_VALUES

MODULE = 'l10n_ga_hr_payroll'


class GaPayrollCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.ref('base.XAF').active = True
        cls.company = cls.env['res.company'].create(
            {
                'name': 'Société de test Gabon',
                'country_id': cls.env.ref('base.ga').id,
                'currency_id': cls.env.ref('base.XAF').id,
            }
        )
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=[cls.company.id]))
        cls.structure_type = cls.env.ref(f'{MODULE}.structure_type_ga_employee')
        cls.structure = cls.env.ref(f'{MODULE}.structure_ga_employee')

    @classmethod
    def _employee(cls, name, wage, start=date(2025, 1, 1), **values):
        return cls.env['hr.employee'].create(
            {
                'name': name,
                'company_id': cls.company.id,
                'date_version': start,
                'contract_date_start': start,
                'wage': wage,
                'structure_type_id': cls.structure_type.id,
                **values,
            }
        )

    @classmethod
    def _input_type(cls, code):
        return cls.env.ref(f'{MODULE}.input_type_ga_{code.removeprefix("GA_").lower()}')

    @classmethod
    def _payslip(cls, employee, date_from, date_to, inputs=None, compute_sheet=True):
        slip = cls.env['hr.payslip'].create(
            {
                'name': f'{employee.name} {date_from:%m/%Y}',
                'employee_id': employee.id,
                'date_from': date_from,
                'date_to': date_to,
                'input_line_ids': [
                    (0, 0, {'input_type_id': cls._input_type(code).id, 'amount': amount})
                    for code, amount in (inputs or {}).items()
                ],
            }
        )
        if compute_sheet:
            slip.compute_sheet()
        return slip

    @classmethod
    def _validated(cls, employee, date_from, date_to, inputs=None):
        slip = cls._payslip(employee, date_from, date_to, inputs)
        slip.action_payslip_done()
        return slip

    @classmethod
    def _work_entry_type(cls, code):
        return cls.env['hr.work.entry.type'].search([('code', '=', code)])

    @classmethod
    def _absence(cls, employee, code, first_day, last_day):
        """Absence en jours entiers (congé du calendrier du salarié) reprise par les prestations."""
        return cls.env['resource.calendar.leaves'].create(
            {
                'name': f'{code} {employee.name}',
                'date_from': datetime.combine(first_day, time.min),
                'date_to': datetime.combine(last_day, time(23, 59)),
                'resource_id': employee.resource_id.id,
                'calendar_id': employee.resource_calendar_id.id,
                'work_entry_type_id': cls._work_entry_type(code).id,
                'time_type': 'leave',
            }
        )

    @classmethod
    def _extra_hours(cls, employee, code, start, stop):
        """Prestation d'heures supplémentaires (hors horaire, ex. un samedi)."""
        values = cls.env['hr.version']._generate_work_entries_postprocess(
            [
                {
                    'name': f'{code} {employee.name}',
                    'version_id': employee.version_id.id,
                    'employee_id': employee.id,
                    'date_start': start,
                    'date_stop': stop,
                    'work_entry_type_id': cls._work_entry_type(code).id,
                }
            ]
        )
        return cls.env['hr.work.entry'].create(values)

    # --- lecture ---------------------------------------------------------------------------------

    @staticmethod
    def _totals(slip):
        return {line.code: line.total for line in slip.line_ids}

    @staticmethod
    def _line(slip, code):
        return slip.line_ids.filtered(lambda line: line.code == code)

    def _expected(self, slip, lines, **facts):
        """Résultat du noyau pour des faits écrits à la main (indépendants de l'adaptateur)."""
        params = slip.company_id._l10n_ga_fiscal_params(slip.date_to, raise_if_not_found=True)
        gain_lines = tuple(GainLine(*line) for line in lines)
        facts.setdefault('presence_days', slip._l10n_ga_days_worked())
        return compute(PayslipFacts(lines=gain_lines, **facts), params)

    def assertCoreParity(self, slip, result, other_deductions=0):
        """Chaque règle liée au noyau = valeur du noyau au franc près ; brut et net cohérents."""
        totals = self._totals(slip)
        for rule in slip.struct_id.rule_ids.filtered(lambda r: r.l10n_ga_core_value not in (False, *GAIN_VALUES)):
            expected = rule._l10n_ga_sign() * slip._l10n_ga_value(result, rule.l10n_ga_core_value)
            self.assertAlmostEqual(totals.get(rule.code, 0.0), expected, delta=1, msg=rule.code)
            if not expected:
                self.assertNotIn(rule.code, totals, 'une ligne nulle n’est pas imprimée')
        self.assertAlmostEqual(totals['GROSS'], result.gains, delta=1)
        self.assertAlmostEqual(totals['NET'], result.net - other_deductions, delta=1)
