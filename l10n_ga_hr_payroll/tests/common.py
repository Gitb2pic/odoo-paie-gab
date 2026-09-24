"""Fabrique des tests Odoo de la paie gabonaise : société, salariés, bulletins (aucune donnée de démo)."""

from datetime import date

from odoo.tests import TransactionCase

from ..lib.ga_fiscal_core.engine import PayslipFacts, compute
from ..lib.ga_fiscal_core.exemptions import GainLine

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
        for rule in slip.struct_id.rule_ids.filtered('l10n_ga_core_value'):
            expected = rule._l10n_ga_sign() * slip._l10n_ga_value(result, rule.l10n_ga_core_value)
            self.assertAlmostEqual(totals.get(rule.code, 0.0), expected, delta=1, msg=rule.code)
            if not expected:
                self.assertNotIn(rule.code, totals, 'une ligne nulle n’est pas imprimée')
        self.assertAlmostEqual(totals['GROSS'], result.gains, delta=1)
        self.assertAlmostEqual(totals['NET'], result.net - other_deductions, delta=1)
