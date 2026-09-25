from calendar import monthrange
from datetime import date

from psycopg2 import IntegrityError  # pylint: disable=import-error

from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from ..models.hr_payslip import YTD_FIELDS
from .common import GaPayrollCase

# Rémunération variable : régularisation IRPP de décembre non nulle ; gratifications plafonnées.
BONUSES = {3: 900_000, 6: 2_500_000, 9: 400_000, 12: 1_800_000}


def _month(month, year=2026):
    return date(year, month, 1), date(year, month, monthrange(year, month)[1])


@tagged('post_install', '-at_install')
class TestYtdOpening(GaPayrollCase):
    """F12, RG25, D-45 : cumuls d'ouverture dans la régularisation IRPP, le plafond et les cumuls figés."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Témoin : toute l'année payée dans Odoo.
        cls.witness = cls._employee('Témoin', 750_000, start=date(2020, 1, 1), marital='married', children=2)
        cls.witness_slips = {
            month: cls._validated(cls.witness, *_month(month), inputs=cls._inputs(month)) for month in range(1, 13)
        }

    @staticmethod
    def _inputs(month):
        return {'GA_GRATIF': BONUSES[month]} if month in BONUSES else None

    def _opening(self, employee, june, **values):
        """Cumuls d'ouverture = cumuls figés du témoin à fin juin (janvier à juin payés ailleurs)."""
        return self.env['l10n_ga.ytd.opening'].create(
            {
                'employee_id': employee.id,
                'company_id': self.company.id,
                'year': 2026,
                'date_from': date(2026, 1, 1),
                'date_to': date(2026, 6, 30),
                'gross': june.l10n_ga_ytd_gross,
                'taxable': june.l10n_ga_ytd_taxable,
                'irpp_base': june.l10n_ga_ytd_irpp_base,
                'irpp': june.l10n_ga_ytd_irpp,
                'tcs': june.l10n_ga_ytd_tcs,
                'cnss': june.l10n_ga_ytd_cnss,
                'bonus_exempt': june.l10n_ga_ytd_bonus_exempt,
                'contributions': june.l10n_ga_ytd_contributions,
                'benefits': june.l10n_ga_ytd_benefits,
                'fnh': june.l10n_ga_ytd_fnh,
                'tax_exempt': june.l10n_ga_ytd_tax_exempt,
                **values,
            }
        )

    def test_switch_in_july_gives_same_year_end_as_full_year(self):
        employee = self._employee('Bascule', 750_000, start=date(2020, 1, 1), marital='married', children=2)
        self._opening(employee, self.witness_slips[6])
        for month in range(7, 13):
            slip = self._validated(employee, *_month(month), inputs=self._inputs(month))
            witness = self.witness_slips[month]
            for code in ('GA_IRPP', 'GA_IRPP_REGUL', 'NET'):
                self.assertAlmostEqual(
                    self._totals(slip).get(code, 0), self._totals(witness).get(code, 0), delta=1, msg=f'{code} {month}'
                )
            for ytd_field in YTD_FIELDS:
                self.assertAlmostEqual(slip[ytd_field], witness[ytd_field], delta=1, msg=f'{ytd_field} {month}')
        december = self.witness_slips[12]
        self.assertTrue(self._totals(december).get('GA_IRPP_REGUL'), 'régularisation non triviale')

    def test_bonus_cap_counter_includes_opening(self):
        employee = self._employee('Plafond entamé', 750_000, start=date(2020, 1, 1))
        opening = self._opening(employee, self.witness_slips[6])  # 3 400 000 déjà exonérés
        slip = self._validated(employee, *_month(9), inputs={'GA_GRATIF': 1_500_000})
        self.assertEqual(slip._l10n_ga_ytd('l10n_ga_irpp_base'), opening.irpp_base)
        self.assertEqual(slip.l10n_ga_ytd_bonus_exempt, opening.bonus_exempt + slip.l10n_ga_bonus_exempted)
        cap = slip._rule_parameter('l10n_ga_exempt_bonus_cap')
        self.assertEqual(slip.l10n_ga_bonus_exempted, cap - opening.bonus_exempt)
        fresh = self._validated(self._employee('Sans ouverture', 750_000), *_month(9), inputs={'GA_GRATIF': 1_500_000})
        self.assertEqual(fresh.l10n_ga_bonus_exempted, 1_500_000)

    def test_opening_ignored_for_payslip_in_covered_period(self):
        employee = self._employee('Rétroactif', 750_000, start=date(2020, 1, 1))
        self._opening(employee, self.witness_slips[6])
        march = self._payslip(employee, *_month(3))
        self.assertFalse(march._l10n_ga_ytd_opening())
        self.assertEqual(march._l10n_ga_ytd('l10n_ga_irpp_base'), 0)

    def test_one_opening_per_employee_and_year(self):
        employee = self._employee('Unique', 750_000)
        self._opening(employee, self.witness_slips[6])
        with mute_logger('odoo.sql_db'), self.assertRaises(IntegrityError), self.cr.savepoint():
            self._opening(employee, self.witness_slips[6], date_to=date(2026, 5, 31))

    def test_period_within_year(self):
        employee = self._employee('Période', 750_000)
        for date_from in (date(2025, 12, 1), date(2026, 7, 1)):
            with self.assertRaisesRegex(ValidationError, 'comprise dans l’année'), self.cr.savepoint():
                self._opening(employee, self.witness_slips[6], date_from=date_from)

    def test_locked_once_used_by_validated_payslip(self):
        employee = self._employee('Verrou', 750_000, start=date(2020, 1, 1))
        opening = self._opening(employee, self.witness_slips[6])
        opening.note = 'Reprise du logiciel précédent'  # modifiable avant usage
        july = self._validated(employee, *_month(7))
        with self.assertRaisesRegex(UserError, 'déjà repris'):
            opening.gross = 1
        with self.assertRaisesRegex(UserError, 'déjà repris'):
            opening.unlink()
        july.action_payslip_cancel()
        opening.gross = 1
        self.assertEqual(opening.gross, 1)

    def test_employee_button(self):
        employee = self._employee('Bouton', 750_000)
        self.assertEqual(employee.l10n_ga_ytd_opening_count, 0)
        opening = self._opening(employee, self.witness_slips[6])
        employee.invalidate_recordset(['l10n_ga_ytd_opening_count'])
        self.assertEqual(employee.l10n_ga_ytd_opening_count, 1)
        action = employee.action_l10n_ga_ytd_openings()
        self.assertEqual(self.env[action['res_model']].search(action['domain']), opening)
        self.assertEqual(opening.display_name, 'Bouton — 2026')
