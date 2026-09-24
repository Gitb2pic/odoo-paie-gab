from calendar import monthrange
from datetime import date

from odoo.tests import tagged

from .common import GaPayrollCase


def _month(month, year=2026):
    return date(year, month, 1), date(year, month, monthrange(year, month)[1])


@tagged('post_install', '-at_install')
class TestCashRounding(GaPayrollCase):
    """F2, RG23, patron 15, D-44 : arrondi espèces après le NET unique, reliquat figé et reporté."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.l10n_ga_cash_rounding = 500

    def _cash_employee(self, name, wage=401_237, **values):
        employee = self._employee(name, wage, start=date(2020, 1, 1), **values)
        employee.version_id.l10n_ga_payment_mode = 'cash'
        return employee

    def test_twelve_consecutive_cash_payslips(self):
        employee = self._cash_employee('Espèces 12 mois')
        paid = nets = 0
        carry = 0
        for month in range(1, 13):
            inputs = {'GA_ASSID': 1_111 * month} if month % 3 == 0 else None
            slip = self._validated(employee, *_month(month), inputs=inputs)
            totals = self._totals(slip)
            self.assertEqual(totals.get('GA_ROUND_PREV', 0), carry, f'mois {month}')
            self.assertEqual(totals['GA_NET_PAY'] % 500, 0)
            self.assertEqual(
                totals['GA_NET_PAY'], totals['NET'] + totals.get('GA_ROUND_PREV', 0) + totals.get('GA_ROUND', 0)
            )
            carry = slip.l10n_ga_rounding_carry
            self.assertTrue(0 <= carry < 500)
            self.assertEqual(carry, -totals.get('GA_ROUND', 0))
            self.assertEqual(len(self._line(slip, 'NET')), 1, 'NET reste unique (règle d’or 3)')
            paid += totals['GA_NET_PAY']
            nets += totals['NET']
        self.assertEqual(paid + carry, nets, 'rien n’est perdu ni surpayé sur 12 mois')

    def test_net_is_not_modified_by_rounding(self):
        cash = self._payslip(self._cash_employee('Espèces'), *_month(9))
        transfer = self._payslip(self._employee('Virement', 401_237, start=date(2020, 1, 1)), *_month(9))
        self.assertEqual(self._totals(cash)['NET'], self._totals(transfer)['NET'])

    def test_transfer_pays_net(self):
        slip = self._payslip(self._employee('Virement', 401_237, start=date(2020, 1, 1)), *_month(9))
        totals = self._totals(slip)
        self.assertEqual(totals['GA_NET_PAY'], totals['NET'])
        self.assertNotIn('GA_ROUND', totals)
        self.assertNotIn('GA_ROUND_PREV', totals)

    def test_switch_to_transfer_pays_previous_carry(self):
        employee = self._cash_employee('Changement de mode')
        first = self._validated(employee, *_month(8))
        carry = first.l10n_ga_rounding_carry
        self.assertTrue(carry)
        employee.version_id.l10n_ga_payment_mode = 'transfer'
        second = self._validated(employee, *_month(9))
        totals = self._totals(second)
        self.assertEqual(totals['GA_ROUND_PREV'], carry)
        self.assertEqual(totals['GA_NET_PAY'], totals['NET'] + carry)
        self.assertEqual(second.l10n_ga_rounding_carry, 0)

    def test_final_settlement_pays_whole_carry(self):
        employee = self._cash_employee('Départ')
        first = self._validated(employee, *_month(8))
        carry = first.l10n_ga_rounding_carry
        employee.version_id.contract_date_end = date(2026, 9, 30)
        last = self._validated(employee, *_month(9))
        totals = self._totals(last)
        self.assertEqual(totals['GA_NET_PAY'], totals['NET'] + carry)
        self.assertEqual(last.l10n_ga_rounding_carry, 0)

    def test_no_rounding_step(self):
        self.company.l10n_ga_cash_rounding = 0
        slip = self._payslip(self._cash_employee('Pas nul'), *_month(9))
        totals = self._totals(slip)
        self.assertEqual(totals['GA_NET_PAY'], totals['NET'])

    def test_carry_frozen_after_validation(self):
        employee = self._cash_employee('Figé')
        first = self._validated(employee, *_month(8))
        carry = first.l10n_ga_rounding_carry
        self.company.l10n_ga_cash_rounding = 1_000
        self.assertEqual(first.l10n_ga_rounding_carry, carry)
        second = self._payslip(employee, *_month(9))
        totals = self._totals(second)
        self.assertEqual(totals['GA_ROUND_PREV'], carry)
        self.assertEqual(totals['GA_NET_PAY'] % 1_000, 0)

    def test_cancelled_payslip_carry_ignored(self):
        employee = self._cash_employee('Annulé')
        first = self._validated(employee, *_month(8))
        first.action_payslip_cancel()
        second = self._payslip(employee, *_month(9))
        self.assertNotIn('GA_ROUND_PREV', self._totals(second))
