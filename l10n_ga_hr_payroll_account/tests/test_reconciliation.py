from odoo.tests import tagged

from .common import SEPT, GaPayrollAccountCase


@tagged('post_install', '-at_install')
class TestLiabilityBalance(GaPayrollAccountCase):
    """Rapprochements (étape 3) : soldes 447x (ID10) et 431x (DTS) après paie et paiement."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.batch = cls._run(cls._complete('Salarié 1') | cls._complete('Salarié 2', wage=900_000))
        cls.batch.slip_ids.move_id.action_post()
        cls.totals = {}
        for line in cls.batch.slip_ids.line_ids:
            cls.totals[line.code] = cls.totals.get(line.code, 0.0) + line.total

    def _bank_account(self):
        bank = self.env['account.journal'].search(
            [('company_id', '=', self.company.id), ('type', '=', 'bank')], limit=1
        )
        return bank.default_account_id

    def _code(self, number):
        return self._account(number).code

    def test_tax_balance_equals_payslips(self):
        balance = self.company.l10n_ga_payroll_liability_balance('tax', SEPT[1])
        t = self.totals
        self.assertAlmostEqual(balance[self._code('4471')], -t['GA_IRPP'] - t.get('GA_IRPP_REGUL', 0), places=2)
        self.assertAlmostEqual(
            balance[self._code('4472')], -t['GA_TCS'] - t.get('GA_FNH_SAL', 0) + t['GA_FNH'] + t['GA_CFP'], places=2
        )

    def test_social_balance_equals_payslips(self):
        balance = self.company.l10n_ga_payroll_liability_balance('social', SEPT[1], SEPT[0])
        t = self.totals
        self.assertAlmostEqual(balance[self._code('4311')], t['GA_CNSS_PF'], places=2)
        self.assertAlmostEqual(balance[self._code('4312')], t['GA_CNSS_AT'], places=2)
        self.assertAlmostEqual(balance[self._code('4313')], t['GA_CNSS_AVID'] - t['GA_CNSS_SAL'], places=2)
        self.assertAlmostEqual(balance[self._code('4318')], t['GA_CNAMGS_PAT'] - t['GA_CNAMGS_SAL'], places=2)

    def test_payment_settles_balance_and_period_filter(self):
        irpp = self.company.l10n_ga_payroll_liability_balance('tax', SEPT[1])[self._code('4471')]
        payment = self.env['account.move'].create(
            {
                'journal_id': self.batch.slip_ids.move_id.journal_id[:1].id,
                'date': SEPT[1].replace(month=10, day=15),
                'line_ids': [
                    (0, 0, {'account_id': self._account('4471').id, 'debit': irpp}),
                    (0, 0, {'account_id': self._bank_account().id, 'credit': irpp}),
                ],
            }
        )
        payment.action_post()
        after = SEPT[1].replace(month=10, day=31)
        self.assertEqual(self.company.l10n_ga_payroll_liability_balance('tax', after)[self._code('4471')], 0)
        october = self.company.l10n_ga_payroll_liability_balance('tax', after, date_from=payment.date)
        self.assertAlmostEqual(october[self._code('4471')], -irpp, places=2)
        self.assertEqual(self.company.l10n_ga_payroll_liability_balance('tax', SEPT[0])[self._code('4471')], 0)

    def test_draft_moves_are_ignored(self):
        self.batch.slip_ids.move_id.button_draft()
        self.assertEqual(self.company.l10n_ga_payroll_liability_balance('social', SEPT[1])[self._code('4311')], 0)
