from datetime import date, datetime

from psycopg2 import IntegrityError  # pylint: disable=import-error

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

    def test_seniority_from_company_default_agreement(self):
        """D-106 : sans convention sur la version, la convention par défaut de la société s'applique."""
        employee = self._employee('Défaut société', 350_000, l10n_ga_seniority_date=date(2020, 9, 1))
        slip = self._payslip(employee, *SEPT)
        self.assertNotIn('GA_ANC', self._totals(slip))
        self.company.l10n_ga_default_agreement_id = self.agreement
        slip.compute_sheet()
        self.assertEqual(self._totals(slip)['GA_ANC'], round(350_000 * 0.06))  # base : salaire (pas de grade)

    # --- convention et grade par défaut (D-111) ------------------------------------------------

    def test_new_company_gets_its_own_default_agreement(self):
        default = self.default_agreement
        self.assertEqual(default.company_id, self.company)
        self.assertEqual(default.code, 'TRONC_COMMUN')
        self.assertEqual(len(default.grade_ids), 5)
        self.assertNotEqual(default, self.env.ref('l10n_ga_hr_payroll.agreement_example_common'))
        other = self.env['res.company'].create({'name': 'Hors Gabon', 'country_id': self.env.ref('base.fr').id})
        self.assertFalse(other.l10n_ga_default_agreement_id)
        # idempotent : pas de seconde copie
        self.company.l10n_ga_default_agreement_id = False
        self.company._l10n_ga_ensure_default_agreement()
        self.assertEqual(self.company.l10n_ga_default_agreement_id, default)

    def test_new_employee_gets_default_agreement_and_grade(self):
        self.company.l10n_ga_default_agreement_id = self.default_agreement
        employee = self._employee('Nouveau', 300_000, start=date(2020, 9, 1))
        version = employee.version_id
        self.assertEqual(version.l10n_ga_agreement_id, self.default_agreement)
        self.assertEqual(version.l10n_ga_grade_id.category, 'C1')  # plus haut minimum ≤ 300 000
        slip = self._payslip(employee, *SEPT)
        self.assertEqual(self._totals(slip)['GA_ANC'], round(295_400 * 0.06))  # 6 ans, base conventionnelle
        # modifiable : le grade choisi n'est jamais écrasé
        cat7 = self.default_agreement.grade_ids.filtered(lambda g: g.category == '7')
        version.l10n_ga_grade_id = cat7
        version.wage = 310_000
        self.assertEqual(version.l10n_ga_grade_id, cat7)

    def test_grade_follows_wage_when_empty(self):
        self.company.l10n_ga_default_agreement_id = self.default_agreement
        employee = self._employee('Sous la grille', 90_000)
        version = employee.version_id
        self.assertEqual(version.l10n_ga_agreement_id, self.default_agreement)
        self.assertFalse(version.l10n_ga_grade_id)  # sous le plus bas minimum (105 000)
        version.wage = 160_000
        self.assertEqual(version.l10n_ga_grade_id.category, '7')

    def test_explicit_agreement_kept(self):
        self.company.l10n_ga_default_agreement_id = self.default_agreement
        employee = self._employee('Autre convention', 350_000, l10n_ga_agreement_id=self.agreement.id)
        self.assertEqual(employee.version_id.l10n_ga_agreement_id, self.agreement)
        self.assertEqual(employee.version_id.l10n_ga_grade_id.category, 'C2')  # grille de la convention choisie

    def test_changing_agreement_resets_grade(self):
        self.company.l10n_ga_default_agreement_id = self.default_agreement
        version = self._employee('Changement', 300_000).version_id
        self.assertEqual(version.l10n_ga_grade_id.agreement_id, self.default_agreement)
        version.l10n_ga_agreement_id = self.agreement
        self.assertEqual(version.l10n_ga_grade_id, self.grade_c1)  # grade de la nouvelle convention
        version.l10n_ga_agreement_id = False
        self.assertFalse(version.l10n_ga_grade_id)

    def test_grade_for_wage_uses_dated_values(self):
        agreement = self.default_agreement
        c1 = agreement.grade_ids.filtered(lambda g: g.category == 'C1')
        self.env['l10n_ga.agreement.grade'].create(
            {'agreement_id': agreement.id, 'category': 'C1', 'date_from': date(2026, 1, 1), 'minimum_wage': 350_000}
        )
        self.assertEqual(agreement._l10n_ga_grade_for_wage(300_000, date(2025, 6, 30)), c1)
        self.assertEqual(agreement._l10n_ga_grade_for_wage(300_000, date(2026, 6, 30)).category, 'AM1')
        self.assertFalse(agreement._l10n_ga_grade_for_wage(50_000, date(2026, 6, 30)))

    def test_apply_default_agreement_to_existing_employees(self):
        employee = self._employee('Ancien sans convention', 200_000, start=date(2020, 1, 1))
        self.assertFalse(employee.version_id.l10n_ga_agreement_id)
        self.company.l10n_ga_default_agreement_id = self.default_agreement
        action = employee.action_l10n_ga_apply_default_agreement()
        self.assertEqual(action['params']['type'], 'success')
        self.assertEqual(employee.version_id.l10n_ga_agreement_id, self.default_agreement)
        self.assertEqual(employee.version_id.l10n_ga_grade_id.category, 'AM1')
        server_action = self.env.ref('l10n_ga_hr_payroll.action_server_l10n_ga_apply_default_agreement')
        self.assertEqual(server_action.binding_model_id.model, 'hr.employee')

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

    def test_default_agreement_data(self):
        """D-111 : « Tronc commun » livré (2 % après 2 ans, +1 % par an, grille Commerce 2012), sans heures sup."""
        template = self.env.ref('l10n_ga_hr_payroll.agreement_example_common')
        self.assertEqual(template.code, 'TRONC_COMMUN')
        self.assertFalse(template.is_example)
        self.assertEqual(
            (template.seniority_start_years, template.seniority_start_rate, template.seniority_step_rate),
            (2, 0.02, 0.01),
        )
        self.assertEqual(template.seniority_base, 'grade_minimum')
        self.assertEqual(
            sorted(template.grade_ids.mapped('minimum_wage')), [105_000, 153_500, 194_600, 295_400, 592_600]
        )
        self.assertFalse(template.overtime_rate_ids)

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
