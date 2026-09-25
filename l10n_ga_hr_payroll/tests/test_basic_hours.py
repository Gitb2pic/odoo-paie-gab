"""FIX 01 : salaire de base sur le mois de référence de 173,33 h (arrêté 016/MTEPS art. 5, base 05 §2)."""

import re
from datetime import date, datetime
from pathlib import Path

from odoo.tests import tagged

from .common import GaPayrollCase

JAN = (date(2025, 1, 1), date(2025, 1, 31))  # 23 jours ouvrés : 184 h au calendrier
FEB = (date(2025, 2, 1), date(2025, 2, 28))  # 20 jours ouvrés : 160 h au calendrier
WAGE = 130_000
INPUTS = {'GA_RESP': 200_000, 'GA_REPR': 100_000, 'GA_REND': 62_000, 'GA_TRANSP': 35_000}
MODULE_DIR = Path(__file__).resolve().parents[1]


@tagged('post_install', '-at_install')
class TestBasicHours(GaPayrollCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.agreement = cls.env['l10n_ga.collective.agreement'].create(
            {
                'name': 'Convention heures sup.',
                'code': 'HS',
                'company_id': cls.company.id,
                'overtime_rate_ids': [(0, 0, {'period': 'day', 'hours_from': 0, 'hours_to': 0, 'rate': 0.10})],
            }
        )

    @classmethod
    def _salaried(cls, name, start=date(2024, 7, 1), **values):
        return cls._employee(
            name,
            WAGE,
            start=start,
            marital='single',
            children=2,
            l10n_ga_transport_trips='2',
            ssnid=f'CNSS-{name}',
            l10n_ga_nif=f'NIF-{name}',
            **values,
        )

    def _slip(self, employee, period=JAN, validate=False):
        slip = self._payslip(employee, *period, inputs=INPUTS)
        if validate:
            slip.action_payslip_done()
        return slip

    @staticmethod
    def _basic(slip):
        return sum(slip.line_ids.filtered(lambda line: line.code == 'BASIC').mapped('total'))

    def _reference_hours(self, slip):
        return slip._rule_parameter('l10n_ga_hours_month_ref')

    def test_t1_t2_full_months_same_rate(self):
        employee = self._salaried('Complet')
        january, february = self._slip(employee, JAN), self._slip(employee, FEB)
        for slip, calendar_hours in ((january, 184), (february, 160)):
            with self.subTest(month=slip.date_from.month):
                month_hours = sum(slip._l10n_ga_month_lines().mapped('number_of_hours'))
                self.assertEqual(month_hours, calendar_hours, 'le calendrier reste la source des heures réelles')
                self.assertEqual(slip._l10n_ga_basic_hours(), self._reference_hours(slip))
                self.assertEqual(round(slip._l10n_ga_hourly_rate(), 2), 750.01)
                self.assertEqual(self._basic(slip), WAGE)

    def test_t3_one_unpaid_day(self):
        employee = self._salaried('Un jour')
        self._absence(employee, 'GA_ABS_JNP', date(2025, 1, 7), date(2025, 1, 7))
        slip = self._slip(employee)
        self.assertAlmostEqual(slip._l10n_ga_basic_hours(), 165.33, places=2)
        self.assertEqual(self._basic(slip), 124_000)

    def test_t4_whole_month_unpaid(self):
        employee = self._salaried('Absent')
        self._absence(employee, 'GA_ABS_JNP', *JAN)
        slip = self._slip(employee)
        self.assertEqual(slip._l10n_ga_basic_hours(), 0)
        self.assertEqual(self._basic(slip), 0)
        self.assertTrue(all(line.total >= 0 for line in slip.line_ids if line.category_id.code in ('BASIC', 'ALW')))

    def test_t5_overtime_uses_the_same_rate(self):
        employee = self._salaried('Heures sup.', l10n_ga_agreement_id=self.agreement.id)
        self._extra_hours(employee, 'GA_HS_J', datetime(2025, 1, 4, 8, 0), datetime(2025, 1, 4, 18, 0))
        self._extra_hours(employee, 'GA_HS_J', datetime(2025, 2, 1, 8, 0), datetime(2025, 2, 1, 18, 0))
        january, february = self._slip(employee, JAN), self._slip(employee, FEB)
        self.assertEqual(january._l10n_ga_hourly_rate(), february._l10n_ga_hourly_rate())
        expected = round(WAGE / self._reference_hours(january) * 10 * 1.10)
        for slip in (january, february):
            with self.subTest(month=slip.date_from.month):
                self.assertEqual(self._totals(slip)['GA_HS_J'], expected)
                self.assertEqual(self._basic(slip), WAGE)

    def test_t6_paid_leave_hours_move_to_leave_allowance(self):
        employee = self._salaried('Congé payé')
        self._absence(employee, 'GA_CP', date(2025, 1, 6), date(2025, 1, 7))
        slip = self._slip(employee)
        h_ref = self._reference_hours(slip)
        self.assertAlmostEqual(slip._l10n_ga_basic_hours(), h_ref - 16, places=2)
        self.assertEqual(self._basic(slip), 118_000)
        # Maintien (sans historique) : salaire et indemnités « base congés » proratisées, 16 h sur la même base.
        prorated = slip.struct_id.rule_ids.filtered(lambda r: r.l10n_ga_prorate and r.l10n_ga_leave_base)
        monthly = WAGE + sum(amount for code, amount in INPUTS.items() if code in prorated.mapped('code'))
        self.assertAlmostEqual(self._totals(slip)['GA_CONGE'], monthly * 16 / h_ref, delta=1)

    def test_t7_entry_during_month(self):
        employee = self._salaried('Entrée', start=date(2025, 1, 16))
        slip = self._slip(employee)
        out_hours = sum(slip.worked_days_line_ids.filtered(lambda wd: wd.code == 'OUT').mapped('number_of_hours'))
        self.assertEqual(out_hours, 88)  # 11 jours ouvrés du 1er au 15 janvier
        self.assertEqual(self.company.l10n_ga_entry_exit_hours, 'deduct')  # (a) par défaut (D-104)
        self.assertAlmostEqual(slip._l10n_ga_basic_hours(), 85.33, places=2)
        self.assertEqual(self._basic(slip), 63_999)  # 85,33 × 130 000 / 173,33 = 63 998,96
        self.company.l10n_ga_entry_exit_hours = 'prorata'  # (b)
        slip.compute_sheet()
        self.assertAlmostEqual(slip._l10n_ga_basic_hours(), self._reference_hours(slip) * 96 / 184, places=2)
        self.assertEqual(self._basic(slip), round(WAGE * 96 / 184))

    def test_t8_printed_hours_are_frozen(self):
        employee = self._salaried('Imprimé')
        slip = self._slip(employee, validate=True)
        data = slip._l10n_ga_report_data()
        self.assertAlmostEqual(data['month_hours'], 173.33, places=2)
        basic_row = next(row for row in slip._l10n_ga_report_rows(data) if row['code'] == '10000')
        self.assertAlmostEqual(basic_row['base'], 173.33, places=2)
        self.assertEqual(round(basic_row['rate'], 2), 750.01)
        self.assertEqual(basic_row['amount'], WAGE)
        employee.version_id.wage = 200_000  # contrat modifié après validation
        data = slip._l10n_ga_report_data()
        self.assertAlmostEqual(data['month_hours'], 173.33, places=2)
        again = next(row for row in slip._l10n_ga_report_rows(data) if row['code'] == '10000')
        self.assertEqual((round(again['rate'], 2), again['amount']), (750.01, WAGE))
        report = 'l10n_ga_hr_payroll.action_report_payslip_ga'
        html = self.env['ir.actions.report']._render_qweb_html(report, slip.ids)[0]
        self.assertIn('173,33', html.decode())

    def test_t9_full_payslip_non_regression(self):
        slip = self._slip(self._salaried('Complet T9'))
        totals = self._totals(slip)
        self.assertEqual(totals['BASIC'], WAGE)
        self.assertEqual((totals['GA_CNSS_SAL'], totals['GA_CNAMGS_SAL']), (-12_300, -9_840))
        self.assertNotIn('GA_TCS', totals)
        self.assertNotIn('GA_IRPP', totals)
        self.assertEqual(totals['NET'], 504_860)
        result = slip._l10n_ga_result(slip._l10n_ga_main_salary(), slip._l10n_ga_line_totals())
        self.assertEqual(result.social_base, 492_000)
        self.assertEqual((result.taxable_gross, result.tcs_base), (130_000, 107_860))
        self.assertEqual(result.gains - result.taxable_gross, 397_000)

    def test_t10_single_hourly_rate(self):
        sources = [*MODULE_DIR.glob('models/*.py'), MODULE_DIR / 'data' / 'hr_salary_rule_data.xml']
        sources += [*MODULE_DIR.glob('lib/ga_fiscal_core/*.py'), *MODULE_DIR.glob('report/*.xml')]
        literal = re.compile(r'173[.,]33')
        division = re.compile(r'wage\s*/(?!\s*(?:self\._rule_parameter|reference_hours))')
        for path in sources:
            text = path.read_text(encoding='utf-8')
            with self.subTest(path=path.name):
                self.assertFalse(literal.search(text), 'heures de référence en dur')
                offenders = [line.strip() for line in text.splitlines() if division.search(line)]
                self.assertEqual(offenders, [], 'taux horaire calculé hors de _l10n_ga_hourly_rate / hourly_rate')
