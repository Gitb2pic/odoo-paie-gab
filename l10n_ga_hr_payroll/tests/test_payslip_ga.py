from datetime import date
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from ..lib.ga_fiscal_core import engine
from .common import GaPayrollCase

SEPT = (date(2026, 9, 1), date(2026, 9, 30))
F16_INPUTS = {'GA_TRANSP': 35_000, 'GA_RESP': 105_000}
F16_LINES = [
    ('BASIC', 450_000, None, None),
    ('GA_TRANSP', 35_000, 'TRANSPORT_35K', 'TRANSPORT_DAILY'),
    ('GA_RESP', 105_000, None, 'EXEMPT'),
]


def month(year, number):
    start = date(year, number, 1)
    end = date(year + number // 12, number % 12 + 1, 1)
    return start, date.fromordinal(end.toordinal() - 1)


@tagged('post_install', '-at_install')
class TestPayslipGa(GaPayrollCase):
    """Adaptateur (patron 2), règles liées au noyau, bulletin figé (F7, F16), profils 06 §3."""

    # --- F16 de bout en bout ---------------------------------------------------------------------

    def _f16_slip(self, name='F16'):
        employee = self._employee(name, 450_000, l10n_ga_transport_trips='2')
        return self._payslip(employee, *SEPT, inputs=F16_INPUTS)

    def test_f16_net_514897_in_odoo(self):
        slip = self._f16_slip()
        totals = self._totals(slip)
        self.assertEqual(slip._l10n_ga_days_worked(), 22)
        self.assertEqual(totals['GROSS'], 590_000)
        self.assertEqual(totals['GA_CNSS_SAL'], -27_750)
        self.assertEqual(totals['GA_CNAMGS_SAL'], -11_100)
        self.assertEqual(totals['GA_TCS'], -13_058)
        self.assertEqual(totals['GA_IRPP'], -23_195)
        self.assertEqual(totals['NET'], 514_897)
        self.assertEqual(totals['GA_CNSS_PF'] + totals['GA_CNSS_AT'] + totals['GA_CNSS_AVID'], 99_900)
        self.assertEqual((totals['GA_CNAMGS_PAT'], totals['GA_FNH'], totals['GA_CFP']), (22_755, 16_650, 2_775))
        self.assertNotIn('GA_IRPP_REGUL', totals)
        self.assertNotIn('GA_FNH_SAL', totals)  # part salariale nulle (point 09-2)
        self.assertCoreParity(slip, self._expected(slip, F16_LINES, transport_trips=2))

    def test_f16_frozen_per_line_and_per_slip(self):
        slip = self._f16_slip()
        slip.action_payslip_done()
        self.assertEqual(slip.state, 'validated')
        self.assertTrue(slip.l10n_ga_frozen_date)
        self.assertEqual(
            (slip.l10n_ga_gross, slip.l10n_ga_social_base, slip.l10n_ga_taxable_gross),
            (590_000, 555_000, 450_000),
        )
        self.assertEqual((slip.l10n_ga_social_excluded, slip.l10n_ga_tax_exempt), (35_000, 140_000))
        self.assertEqual((slip.l10n_ga_tcs, slip.l10n_ga_irpp_withheld), (13_058, 23_195))
        self.assertEqual((slip.l10n_ga_tax_parts_used, slip.l10n_ga_marital_used), (1.0, 'single'))
        self.assertEqual((slip.l10n_ga_cnss_ceiling_used, slip.l10n_ga_cnamgs_ceiling_used), (1_500_000, 2_500_000))
        self.assertEqual((slip.l10n_ga_ytd_gross, slip.l10n_ga_ytd_irpp), (590_000, 23_195))
        per_line = {
            line.code: (line.l10n_ga_social_excluded, line.l10n_ga_tax_exempt)
            for line in slip.line_ids
            if line.code in ('BASIC', 'GA_TRANSP', 'GA_RESP')
        }
        self.assertEqual(per_line, {'BASIC': (0, 0), 'GA_TRANSP': (35_000, 35_000), 'GA_RESP': (0, 105_000)})

    def test_frozen_values_survive_parameter_change(self):
        slip = self._f16_slip()
        slip.action_payslip_done()
        draft = self._f16_slip('F16 brouillon')
        before = (slip.l10n_ga_social_base, slip.l10n_ga_irpp_withheld, self._totals(slip))
        parameter = self.env['hr.rule.parameter'].search([('code', '=', 'l10n_ga_cnss_employee_rate')])
        self.env['hr.rule.parameter.value'].create(
            {'rule_parameter_id': parameter.id, 'date_from': date(2026, 9, 1), 'parameter_value': '0.1'}
        )
        slip.invalidate_recordset()
        self.assertEqual((slip.l10n_ga_social_base, slip.l10n_ga_irpp_withheld, self._totals(slip)), before)
        with self.assertRaisesRegex(UserError, 'GA_CNSS_SAL'):
            draft.action_payslip_done()
        draft.compute_sheet()
        draft.action_payslip_done()
        self.assertEqual(draft.l10n_ga_cnss_employee, 55_500)  # 555 000 × 10 %

    # --- profils du fichier 06 §3 ----------------------------------------------------------------

    def test_single_below_tcs_threshold(self):
        employee = self._employee('Sous le seuil', 120_000)
        slip = self._payslip(employee, *SEPT)
        self.assertNotIn('GA_TCS', self._totals(slip))
        self.assertCoreParity(slip, self._expected(slip, [('BASIC', 120_000, None, None)]))

    def test_married_three_children_at_cnss_ceiling(self):
        employee = self._employee('Plafond', 2_000_000, marital='married', children=3)
        slip = self._payslip(employee, *SEPT)
        self.assertEqual(self._totals(slip)['GA_CNSS_SAL'], -75_000)  # 1 500 000 × 5 %
        self.assertEqual(self._totals(slip)['GA_CNAMGS_SAL'], -40_000)  # 2 000 000 × 2 %
        expected = self._expected(slip, [('BASIC', 2_000_000, None, None)], marital='married', children=3)
        self.assertCoreParity(slip, expected)
        slip.action_payslip_done()
        self.assertEqual((slip.l10n_ga_tax_parts_used, slip.l10n_ga_children_used), (3.5, 3))

    def test_executive_at_professional_expenses_cap(self):
        employee = self._employee('Cadre', 5_000_000)
        slip = self._payslip(employee, *SEPT)
        expected = self._expected(slip, [('BASIC', 5_000_000, None, None)])
        self.assertEqual(expected.abatement, self.company._l10n_ga_fiscal_params(SEPT[1]).fp_annual_cap)
        self.assertCoreParity(slip, expected)

    def test_hired_on_the_15th_prorated(self):
        employee = self._employee('Entré le 15', 300_000, start=date(2026, 9, 15))
        slip = self._payslip(employee, *SEPT, inputs={'GA_SURSAL': 40_000, 'GA_INTERIM': 10_000})
        ratio = slip._l10n_ga_paid_ratio()
        self.assertTrue(0 < ratio < 1)
        totals = self._totals(slip)
        self.assertEqual(totals['BASIC'], slip.paid_amount)
        self.assertAlmostEqual(totals['GA_SURSAL'], 40_000 * ratio, delta=0.5)  # proratisée, au franc
        self.assertEqual(totals['GA_INTERIM'], 10_000)  # non proratisée
        lines = [
            ('BASIC', totals['BASIC'], None, None),
            ('GA_SURSAL', totals['GA_SURSAL'], None, None),
            ('GA_INTERIM', 10_000, None, None),
        ]
        self.assertCoreParity(slip, self._expected(slip, lines, presence_ratio=ratio))

    def test_departure_with_irpp_regularisation(self):
        employee = self._employee('Départ', 400_000, start=date(2026, 1, 1))
        may = self._validated(employee, *month(2026, 5), inputs={'GA_INTERIM': 3_000_000})
        employee.version_id.contract_date_end = date(2026, 6, 30)
        june = self._payslip(employee, *month(2026, 6))
        self.assertTrue(june._l10n_ga_regularize())
        self.assertIn('GA_IRPP_REGUL', self._totals(june))
        expected = self._expected(
            june,
            [('BASIC', 400_000, None, None)],
            ytd_irpp_base=may.l10n_ga_irpp_base,
            ytd_irpp_withheld=may.l10n_ga_irpp_withheld,
            regularize=True,
        )
        self.assertNotEqual(expected.irpp_regularisation, 0)
        self.assertCoreParity(june, expected)
        june.action_payslip_done()
        self.assertEqual(june.l10n_ga_irpp_withheld, expected.irpp + expected.irpp_regularisation)
        self.assertEqual(june.l10n_ga_ytd_irpp, may.l10n_ga_irpp_withheld + june.l10n_ga_irpp_withheld)

    def test_thirteenth_month_beyond_4m_cumulative(self):
        employee = self._employee('Gratifications', 500_000, start=date(2026, 1, 1))
        january = self._validated(employee, *month(2026, 1), inputs={'GA_13M': 3_000_000})
        self.assertEqual(january.l10n_ga_bonus_exempted, 3_000_000)
        february = self._payslip(employee, *month(2026, 2), inputs={'GA_13M': 2_000_000})
        lines = [('BASIC', 500_000, None, None), ('GA_13M', 2_000_000, None, 'BONUS_4M')]
        expected = self._expected(february, lines, ytd_bonus_exempted=3_000_000)
        self.assertEqual(expected.bonus_exempted, 1_000_000)
        self.assertCoreParity(february, expected)
        february.action_payslip_done()
        self.assertEqual((february.l10n_ga_bonus_exempted, february.l10n_ga_ytd_bonus_exempt), (1_000_000, 4_000_000))

    def test_children_change_during_the_year(self):
        employee = self._employee('Naissance', 800_000, start=date(2026, 1, 1), marital='married')
        employee.create_version({'date_version': date(2026, 9, 1), 'children': 2})
        august = self._validated(employee, *month(2026, 8))
        september = self._validated(employee, *month(2026, 9))
        self.assertNotEqual(august.version_id, september.version_id)
        self.assertEqual((august.l10n_ga_tax_parts_used, september.l10n_ga_tax_parts_used), (2.0, 3.0))
        self.assertGreater(august.l10n_ga_irpp_withheld, september.l10n_ga_irpp_withheld)

    def test_dated_parameters_december_january_july(self):
        employee = self._employee('Paramètres datés', 1_000_000)
        slips = {key: self._payslip(employee, *month(*key)) for key in ((2025, 12), (2026, 1), (2026, 7))}
        cnss = {key: -self._totals(slip)['GA_CNSS_SAL'] for key, slip in slips.items()}
        fnh = {key: self._totals(slip)['GA_FNH'] for key, slip in slips.items()}
        self.assertEqual(cnss, {(2025, 12): 25_000, (2026, 1): 50_000, (2026, 7): 50_000})
        self.assertEqual(fnh, {(2025, 12): 20_000, (2026, 1): 20_000, (2026, 7): 30_000})
        self.assertTrue(slips[2025, 12]._l10n_ga_regularize())  # dernier bulletin de l'année
        self.assertFalse(slips[2026, 7]._l10n_ga_regularize())
        for key, slip in slips.items():
            with self.subTest(month=key):
                expected = self._expected(slip, [('BASIC', 1_000_000, None, None)], regularize=key == (2025, 12))
                self.assertCoreParity(slip, expected)

    def test_benefits_in_kind_valued_by_core(self):
        employee = self._employee('Logé nourri', 600_000, l10n_ga_benefit_housing=True, l10n_ga_benefit_food=True)
        slip = self._payslip(employee, *SEPT)
        totals = self._totals(slip)
        self.assertGreater(totals['GA_AN_LOGT'], 0)
        self.assertGreater(totals['GA_AN_NOUR'], 0)
        self.assertNotIn('GA_AN_DOM', totals)
        self.assertEqual(totals['GROSS'], 600_000 + totals['GA_AN_LOGT'] + totals['GA_AN_NOUR'])
        expected = self._expected(
            slip, [('BASIC', 600_000, None, None)], benefits=('housing', 'food'), main_salary=600_000
        )
        self.assertCoreParity(slip, expected)
        slip.action_payslip_done()
        self.assertEqual(slip.l10n_ga_benefits_in_kind, totals['GA_AN_LOGT'] + totals['GA_AN_NOUR'])
        self.assertEqual(self._line(slip, 'GA_AN_LOGT').l10n_ga_tax_exempt, 0)

    def test_deductions_outside_the_core_reduce_net(self):
        employee = self._employee('Avance', 450_000, l10n_ga_transport_trips='2')
        slip = self._payslip(employee, *SEPT, inputs={**F16_INPUTS, 'GA_ADVANCE': 50_000})
        self.assertEqual(self._totals(slip)['NET'], 514_897 - 50_000)
        self.assertCoreParity(slip, self._expected(slip, F16_LINES, transport_trips=2), other_deductions=50_000)

    # --- adaptateur ------------------------------------------------------------------------------

    def test_core_computed_once_per_payslip(self):
        employee = self._employee('Cache', 600_000, l10n_ga_benefit_housing=True)
        slip = self._payslip(employee, *SEPT, compute_sheet=False)
        with patch('odoo.addons.l10n_ga_hr_payroll.models.hr_payslip.compute', wraps=engine.compute) as spy:
            slip.compute_sheet()
        # un calcul pour les avantages en nature (gains en espèces seuls), réutilisé ensuite
        self.assertEqual(spy.call_count, 1)

    def test_payment_date_defaults_to_date_to(self):
        slip = self._f16_slip()
        self.assertEqual(slip.l10n_ga_payment_date, SEPT[1])
        slip.l10n_ga_payment_date = date(2026, 10, 5)
        self.assertEqual(slip.l10n_ga_payment_date, date(2026, 10, 5))

    def test_ytd_limited_to_the_civil_year(self):
        employee = self._employee('Cumuls', 300_000)
        self._validated(employee, *month(2025, 12))
        january = self._validated(employee, *month(2026, 1))
        self.assertEqual(january.l10n_ga_ytd_gross, january.l10n_ga_gross)

    def test_unknown_core_value_rejected(self):
        slip = self._f16_slip()
        with self.assertRaisesRegex(ValueError, 'inconnue'):
            slip._l10n_ga_compute('nope', {'BASIC': 0}, {})

    def test_foreign_structure_not_frozen(self):
        slip = self._f16_slip()
        slip.struct_id = self.env.ref('hr_payroll.default_structure')
        slip.compute_sheet()
        slip.action_payslip_done()
        self.assertFalse(slip.l10n_ga_is_ga)
        self.assertFalse(slip.l10n_ga_frozen_date)
