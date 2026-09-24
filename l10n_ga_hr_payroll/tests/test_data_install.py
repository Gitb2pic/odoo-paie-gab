from datetime import date

from odoo.tests import TransactionCase, tagged

from ..lib.ga_fiscal_core.param_codes import PARAMETERS, params_from_values

ABSENCES = {
    'GA_CP': 'allowance',
    'GA_MAL': 'paid',
    'GA_MAL_NP': 'unpaid',
    'GA_MAT': 'cnss',
    'GA_AT': 'cnss',
    'GA_NAIS': 'paid',
    'GA_MARI': 'paid',
    'GA_DECES': 'paid',
    'GA_ABS_JNP': 'unpaid',
    'GA_ABS_INJ': 'unpaid',
    'GA_MAP': 'unpaid',
    'GA_SANC': 'unpaid',
}


@tagged('post_install', '-at_install')
class TestDataInstall(TransactionCase):
    """Données de l'étape 2.2 : paramètres datés (RG06, F14), structure, entrées (ADR-16), absences (F4)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.Parameter = cls.env['hr.rule.parameter']
        cls.structure = cls.env.ref('l10n_ga_hr_payroll.structure_ga_employee')
        cls.gabon = cls.env.ref('base.ga')

    def _value(self, code, on_date):
        return self.Parameter._get_parameter_from_code(code, on_date)

    def _values(self, on_date):
        return {spec.code: self._value(spec.code, on_date) for spec in PARAMETERS}

    def test_every_parameter_installed_for_gabon(self):
        params = self.Parameter.search([('code', '=like', 'l10n_ga_%')])
        self.assertEqual(sorted(params.mapped('code')), sorted(spec.code for spec in PARAMETERS))
        self.assertEqual(params.country_id, self.gabon)

    def test_dated_values_rg06(self):
        self.assertEqual(self._value('l10n_ga_cnss_employee_rate', date(2025, 12, 31)), 0.025)
        self.assertEqual(self._value('l10n_ga_cnss_employee_rate', date(2026, 1, 1)), 0.05)
        self.assertEqual(self._value('l10n_ga_fnh_rate', date(2026, 7, 16)), 0.02)
        self.assertEqual(self._value('l10n_ga_fnh_rate', date(2026, 7, 17)), 0.03)

    def test_f14_min_withholding_is_zero(self):
        self.assertEqual(self._value('l10n_ga_irpp_min_withholding', date(2026, 9, 30)), 0)

    def test_fiscal_params_built_from_installed_parameters(self):
        for on_date in (date(2025, 12, 31), date(2026, 1, 1), date(2026, 7, 16), date(2026, 7, 17)):
            params = params_from_values(self._values(on_date), cash_rounding=500)
            self.assertEqual(params.smig, 80000)
            self.assertEqual(params.irpp_brackets[-1][1], float('inf'))
        self.assertEqual(params.cnss_employee_rate, 0.05)
        self.assertEqual(params.fnh_rate, 0.03)
        self.assertEqual(params.benefit_rates['housing'], 0.06)

    def test_structure_and_type(self):
        structure_type = self.env.ref('l10n_ga_hr_payroll.structure_type_ga_employee')
        self.assertEqual(self.structure.type_id, structure_type)
        self.assertEqual(structure_type.default_struct_id, self.structure)
        self.assertEqual((structure_type.country_id, self.structure.country_id), (self.gabon, self.gabon))

    def test_input_types(self):
        InputType = self.env['hr.payslip.input.type']
        loan = InputType.search([('code', '=', 'GA_LOAN')])
        self.assertEqual(len(loan), 1)
        self.assertFalse(loan.available_in_attachments)  # sprint 0 point 6
        self.assertTrue(InputType.search([('code', '=', 'GA_SURSAL')]).available_in_attachments)  # ADR-16
        ga_types = InputType.search([('code', '=like', 'GA_%')])
        self.assertTrue(all(self.structure in t.struct_ids for t in ga_types))
        input_rules = self.structure.rule_ids.filtered(
            lambda r: r.condition_select == 'python' and not r.l10n_ga_core_value
        )
        self.assertEqual(set(ga_types.mapped('code')), set(input_rules.mapped('code')))
        self.assertFalse(ga_types.filtered(lambda t: t.code.startswith('GA_AN_')))  # D-18 : valorisés par le noyau

    def test_twelve_absences_with_pay_indicator(self):
        for code, mode in ABSENCES.items():
            entry_type = self.env['hr.work.entry.type'].search([('code', '=', code)])
            self.assertEqual(len(entry_type), 1, code)
            self.assertTrue(entry_type.is_leave, code)
            self.assertEqual(entry_type.l10n_ga_pay_mode, mode, code)
            self.assertEqual(
                self.structure in entry_type.unpaid_structure_ids, mode in ('unpaid', 'allowance'), code
            )  # congé payé : GA_CONGE
            leave_type = self.env['hr.leave.type'].search([('work_entry_type_id', '=', entry_type.id)])
            self.assertEqual(len(leave_type), 1, code)
            self.assertEqual(leave_type.unpaid, mode == 'unpaid', code)
            self.assertEqual(leave_type.country_id, self.gabon, code)
        paid_leave = self.env.ref('l10n_ga_hr_payroll.leave_type_ga_cp')
        self.assertTrue(paid_leave.requires_allocation)

    def test_overtime_work_entry_types_without_rate(self):
        for code in ('GA_HS_J', 'GA_HS_N', 'GA_HS_DIM', 'GA_HS_FER'):
            entry_type = self.env['hr.work.entry.type'].search([('code', '=', code)])
            self.assertEqual(len(entry_type), 1, code)
            self.assertFalse(entry_type.is_leave, code)
            # hors salaire de base ; payées par GA_HS_* selon la convention (point 09-11, étape 2.4)
            self.assertTrue(entry_type.is_extra_hours, code)
            self.assertEqual(entry_type.amount_rate, 0, code)
            self.assertTrue(entry_type.l10n_ga_overtime_period, code)

    def test_loan_sequence(self):
        sequence = self.env.ref('l10n_ga_hr_payroll.sequence_employee_loan')
        self.assertEqual(sequence.code, 'l10n_ga.employee.loan')
