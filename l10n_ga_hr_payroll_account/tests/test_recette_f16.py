from odoo.addons.l10n_ga_hr_payroll.tests.test_payslip_ga import F16_INPUTS
from odoo.tests import tagged

from .common import SEPT, GaPayrollAccountCase


@tagged('post_install', '-at_install')
class TestRecetteF16(GaPayrollAccountCase):
    """C5 : cas F16 (590 000 → net 514 897) payé en espèces, pièce chiffrée compte par compte."""

    def test_f16_move(self):
        employee = self._employee('F16', 450_000, l10n_ga_transport_trips='2')
        employee.version_id.l10n_ga_payment_mode = 'cash'
        slip = self._validated(employee, *SEPT, inputs=F16_INPUTS)
        self.assertEqual(self._totals(slip)['GA_NET_PAY'], 514_500)
        balances = {account.code[:4].rstrip('0'): balance for account, balance in self._balances(slip.move_id).items()}
        cnss = sum(balances.pop(code) for code in ('4311', '4312', '4313'))
        self.assertEqual(
            cnss, -(99_900 + 27_750), 'CNSS patronale (PF + AT + AVID) + salariale ; branches : test_payroll_move'
        )
        self.assertEqual(
            balances,
            {
                '6611': 450_000,  # salaire de base
                '6634': 35_000,  # transport
                '6638': 105_000,  # responsabilité
                '6641': 99_900 + 22_755,  # CNSS patronale + CNAMGS patronale
                '6413': 16_650,  # FNH
                '6415': 2_775,  # CFP
                '4471': -23_195,  # IRPP
                '4472': -(13_058 + 16_650 + 2_775),  # TCS + FNH + CFP
                '4318': -(11_100 + 22_755),  # CNAMGS salariale + patronale
                '422': -514_897,  # net ; le reliquat d'arrondi 397 reste dans 422
            },
        )
