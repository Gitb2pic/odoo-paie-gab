from datetime import date

from odoo.tests import tagged

from .common import GaPayrollCase

SEPT = (date(2026, 9, 1), date(2026, 9, 30))  # 22 jours ouvrés, 176 heures
ABSENCE = (date(2026, 9, 7), date(2026, 9, 8))  # lundi et mardi : 2 jours, 16 heures
WAGE = 440_000
H_REF = 173.33  # mois de référence légal (arrêté 016/MTEPS art. 5), paramètre l10n_ga_hours_month_ref
FULL, REDUCED = WAGE, WAGE * (H_REF - 16) / H_REF  # FIX 01 : 16 h retirées des 173,33 h (≈ 399 384)

# Effet de chaque absence F4 sur le salaire de base (avec subrogation CNSS, défaut D-26).
EXPECTED_BASIC = {
    'GA_CP': REDUCED,  # payé par l'allocation de congé
    'GA_MAL': FULL,
    'GA_MAL_NP': REDUCED,
    'GA_MAT': FULL,
    'GA_AT': FULL,
    'GA_NAIS': FULL,
    'GA_MARI': FULL,
    'GA_DECES': FULL,
    'GA_ABS_JNP': REDUCED,
    'GA_ABS_INJ': REDUCED,
    'GA_MAP': REDUCED,
    'GA_SANC': REDUCED,
}


@tagged('post_install', '-at_install')
class TestAbsences(GaPayrollCase):
    """F4 : 12 absences gabonaises ; BASIC = heures de référence − heures non payées (FIX 01), jamais une
    retenue (B2)."""

    def _slip_with_absence(self, code, name=None, **employee_values):
        employee = self._employee(name or f'Absence {code}', WAGE, **employee_values)
        self._absence(employee, code, *ABSENCE)
        return self._payslip(employee, *SEPT)

    def test_each_absence_effect_on_basic_and_leave_allowance(self):
        for code, basic in EXPECTED_BASIC.items():
            with self.subTest(absence=code):
                slip = self._slip_with_absence(code)
                totals = self._totals(slip)
                self.assertIn(code, slip.worked_days_line_ids.mapped('code'))
                self.assertAlmostEqual(totals['BASIC'], basic, delta=1)
                if code == 'GA_CP':
                    self.assertAlmostEqual(totals['GA_CONGE'], WAGE - REDUCED, delta=1)  # maintien, sans historique
                else:
                    self.assertNotIn('GA_CONGE', totals)
                # B2 : aucune retenue pour absence, aucun gain négatif
                gains = slip.line_ids.filtered(lambda line: line.category_id.code in ('BASIC', 'ALW'))
                self.assertTrue(all(line.total >= 0 for line in gains))

    def test_maternity_and_work_accident_without_subrogation(self):
        self.company.l10n_ga_cnss_subrogation = False
        for code in ('GA_MAT', 'GA_AT'):
            with self.subTest(absence=code):
                slip = self._slip_with_absence(code, f'Sans subrogation {code}')
                self.assertAlmostEqual(self._totals(slip)['BASIC'], REDUCED, delta=1)

    def test_leave_allowance_twelfth_more_favourable(self):
        employee = self._employee('Congé 1/12', WAGE, start=date(2026, 1, 1))
        august = self._validated(employee, date(2026, 8, 1), date(2026, 8, 31), inputs={'GA_RECALL': 6_000_000})
        reference = august.line_ids.filtered(lambda line: line.salary_rule_id.l10n_ga_leave_base)
        self.assertEqual(sum(reference.mapped('total')), WAGE + 6_000_000)
        self._absence(employee, 'GA_CP', *ABSENCE)
        slip = self._payslip(employee, *SEPT)
        # 6 440 000 × 1/12 × (2 jours ouvrés × 6/5 = 2,4 jours ouvrables) / 24 jours = 53 667
        # > maintien 40 617 (16 h sur 173,33, FIX 01)
        self.assertEqual(self._totals(slip)['GA_CONGE'], 53_667)

    def test_leave_allowance_minor(self):
        employee = self._employee('Congé mineur', WAGE, start=date(2026, 1, 1), birthday=date(2010, 1, 1))
        self._validated(employee, date(2026, 8, 1), date(2026, 8, 31), inputs={'GA_RECALL': 6_000_000})
        self._absence(employee, 'GA_CP', *ABSENCE)
        slip = self._payslip(employee, *SEPT)
        self.assertTrue(slip._l10n_ga_is_minor())
        # 6 440 000 × 5/48 × 2,4 / 30 jours ouvrables
        self.assertEqual(self._totals(slip)['GA_CONGE'], round(6_440_000 * 5 / 48 * 2.4 / 30))

    def test_leave_types_linked_to_work_entry_types(self):
        for code in EXPECTED_BASIC:
            leave_type = self.env.ref(f'l10n_ga_hr_payroll.leave_type_ga_{code.removeprefix("GA_").lower()}')
            self.assertEqual(leave_type.work_entry_type_id.code, code)
