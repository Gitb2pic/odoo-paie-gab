from datetime import date, datetime

from psycopg2 import IntegrityError

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import GaPayrollCase

SEPT = (date(2026, 9, 1), date(2026, 9, 30))
SATURDAY = (datetime(2026, 9, 5, 8, 0), datetime(2026, 9, 5, 12, 0))  # 4 heures hors horaire


@tagged('post_install', '-at_install')
class TestAgreement(GaPayrollCase):
    """RG04, RG18, F5 : convention, grille, ancienneté, heures supplémentaires (point 09-11)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.agreement = cls.env['l10n_ga.collective.agreement'].create(
            {
                'name': 'Convention de test',
                'code': 'TEST',
                'company_id': cls.company.id,
                'seniority_start_years': 2,
                'seniority_start_rate': 0.02,
                'seniority_step_rate': 0.01,
                'seniority_max_rate': 0,
                'grade_ids': [
                    (0, 0, {'category': 'C1', 'date_from': date(2012, 1, 1), 'minimum_wage': 295_400}),
                    (0, 0, {'category': 'C2', 'date_from': date(2012, 1, 1), 'minimum_wage': 320_000}),
                ],
            }
        )
        cls.grade_c1 = cls.agreement.grade_ids.filtered(lambda g: g.category == 'C1')

    def _agreement_employee(self, name, wage=350_000, seniority=date(2020, 9, 1), **values):
        return self._employee(
            name,
            wage,
            l10n_ga_agreement_id=self.agreement.id,
            l10n_ga_grade_id=self.grade_c1.id,
            l10n_ga_seniority_date=seniority,
            **values,
        )

    # --- ancienneté ------------------------------------------------------------------------------

    def test_seniority_on_grade_minimum(self):
        slip = self._payslip(self._agreement_employee('Ancien'), *SEPT)
        self.assertEqual(self._totals(slip)['GA_ANC'], round(295_400 * 0.06))  # 6 ans : 2 % + 4 × 1 %

    def test_seniority_cap_and_wage_base(self):
        self.agreement.seniority_max_rate = 0.05
        slip = self._payslip(self._agreement_employee('Plafond'), *SEPT)
        self.assertEqual(self._totals(slip)['GA_ANC'], round(295_400 * 0.05))
        self.agreement.write({'seniority_base': 'wage', 'seniority_max_rate': 0})
        slip.compute_sheet()
        self.assertEqual(self._totals(slip)['GA_ANC'], round(350_000 * 0.06))

    def test_no_seniority_before_start(self):
        slip = self._payslip(self._agreement_employee('Récent', seniority=date(2025, 3, 1)), *SEPT)
        self.assertNotIn('GA_ANC', self._totals(slip))

    def test_seniority_defaults_to_first_contract(self):
        employee = self._agreement_employee('Sans date', seniority=False)
        employee.version_id.l10n_ga_seniority_date = False
        self.assertEqual(employee.version_id._l10n_ga_seniority_start(), date(2025, 1, 1))

    def test_invalid_seniority_rule(self):
        with self.assertRaisesRegex(ValidationError, 'négatives'):
            self.agreement.seniority_step_rate = -0.01

    # --- grille (RG18) ---------------------------------------------------------------------------

    def test_wage_below_grade_minimum_refused(self):
        with self.assertRaisesRegex(ValidationError, 'minimum'):
            self._agreement_employee('Sous le minimum', wage=250_000)

    def test_grade_must_belong_to_agreement(self):
        other = self.env['l10n_ga.collective.agreement'].create({'name': 'Autre', 'company_id': self.company.id})
        with self.assertRaisesRegex(ValidationError, 'convention'):
            self._employee('Autre grade', 350_000, l10n_ga_agreement_id=other.id, l10n_ga_grade_id=self.grade_c1.id)

    def test_grade_revalued_blocks_payslip(self):
        employee = self._agreement_employee('Revalorisé')
        self.env['l10n_ga.agreement.grade'].create(
            {
                'agreement_id': self.agreement.id,
                'category': 'C1',
                'date_from': date(2026, 9, 1),
                'minimum_wage': 400_000,
            }
        )
        self.assertEqual(employee.version_id._l10n_ga_grade_minimum(date(2026, 8, 31)), 295_400)
        self.assertEqual(employee.version_id._l10n_ga_grade_minimum(date(2026, 9, 30)), 400_000)
        slip = self._payslip(employee, *SEPT)
        self.assertIn('minimum', ' '.join(slip._l10n_ga_blocking_issues()))
        slip.invalidate_recordset(['issues', 'error_count'])
        slip._compute_issues()
        self.assertGreater(slip.error_count, 0)
        with self.assertRaises(UserError):
            slip.action_payslip_done()

    def test_grade_unique_per_date(self):
        with mute_logger('odoo.sql_db'), self.assertRaises(IntegrityError), self.cr.savepoint():
            self.env['l10n_ga.agreement.grade'].create(
                {'agreement_id': self.agreement.id, 'category': 'C1', 'date_from': date(2012, 1, 1), 'minimum_wage': 1}
            )

    # --- heures supplémentaires (point 09-11, D-24) ----------------------------------------------

    def test_overtime_by_tranche(self):
        self.agreement.overtime_rate_ids = [
            (0, 0, {'period': 'day', 'hours_from': 0, 'hours_to': 2, 'rate': 0.10}),
            (0, 0, {'period': 'day', 'hours_from': 2, 'hours_to': 0, 'rate': 0.25}),
        ]
        employee = self._agreement_employee('Heures sup.')
        self._extra_hours(employee, 'GA_HS_J', *SATURDAY)
        slip = self._payslip(employee, *SEPT)
        self.assertEqual(slip._l10n_ga_overtime_hours('day'), 4)
        hourly = 350_000 / slip._rule_parameter('l10n_ga_hours_month_ref')
        totals = self._totals(slip)
        self.assertEqual(totals['GA_HS_J'], round(hourly * (2 * 1.10 + 2 * 1.25)))
        self.assertEqual(totals['BASIC'], 350_000)  # heures sup. hors salaire de base
        self.assertEqual(totals['GROSS'], 350_000 + totals['GA_ANC'] + totals['GA_HS_J'])

    def test_overtime_without_rate_blocks(self):
        employee = self._agreement_employee('Nuit sans taux')
        self._extra_hours(employee, 'GA_HS_N', *SATURDAY)
        slip = self._payslip(employee, *SEPT, compute_sheet=False)
        self.assertIn('sans taux', ' '.join(slip._l10n_ga_blocking_issues()))
        with self.assertRaisesRegex(UserError, 'sans taux'):
            slip.compute_sheet()

    def test_overlapping_tranches_refused(self):
        with self.assertRaisesRegex(ValidationError, 'chevauchent'):
            self.agreement.overtime_rate_ids = [
                (0, 0, {'period': 'sunday', 'hours_from': 0, 'hours_to': 10, 'rate': 0.5}),
                (0, 0, {'period': 'sunday', 'hours_from': 8, 'hours_to': 0, 'rate': 1.0}),
            ]

    # --- données et sécurité ---------------------------------------------------------------------

    def test_example_agreement_marked_and_without_overtime_rates(self):
        example = self.env.ref('l10n_ga_hr_payroll.agreement_example_common')
        self.assertTrue(example.is_example)
        self.assertIn('EXEMPLE', example.name)
        self.assertFalse(example.overtime_rate_ids)
        self.assertEqual(len(example.grade_ids), 5)

    def test_multi_company_rule(self):
        other_company = self.env['res.company'].create(
            {'name': 'Autre société', 'country_id': self.env.ref('base.ga').id}
        )
        foreign = (
            self.env['l10n_ga.collective.agreement']
            .sudo()
            .create({'name': 'Étrangère', 'company_id': other_company.id})
        )
        user = self.env['res.users'].create(
            {
                'name': 'Gestionnaire paie',
                'login': 'paie_ga_test',
                'company_id': self.company.id,
                'company_ids': [(6, 0, [self.company.id])],
                'group_ids': [(6, 0, [self.env.ref('hr_payroll.group_hr_payroll_manager').id])],
            }
        )
        visible = self.env['l10n_ga.collective.agreement'].with_user(user).search([])
        self.assertIn(self.agreement, visible)
        self.assertNotIn(foreign, visible)
