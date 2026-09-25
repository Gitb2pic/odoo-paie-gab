from odoo.tests import tagged

from ..models.account_chart_template import NO_ENTRY_RULES
from .common import AUG, SEPT, GaPayrollAccountCase


@tagged('post_install', '-at_install')
class TestPayrollMove(GaPayrollAccountCase):
    """Étape 3, RG09, RG17 : pièce de paie d'un lot (virement, chèque, espèces), prêt, avance, arrondi."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.transfer = cls._complete('Virement', wage=500_000)
        cls.check = cls._complete('Chèque', mode='check')
        cls.check.version_id.l10n_ga_benefit_housing = True
        cls.cash = cls._complete('Espèces', mode='cash', wage=333_333)
        cls.august = cls._validated(cls.transfer, *AUG)
        cls.loan = cls.env['l10n_ga.employee.loan'].create(
            {
                'employee_id': cls.transfer.id,
                'company_id': cls.company.id,
                'date': SEPT[0],
                'amount': 90_000,
                'installment_count': 3,
                'first_due_date': SEPT[0],
            }
        )
        cls.loan.action_compute_schedule()
        cls.loan.action_approve()
        cls.batch = cls._run(cls.transfer | cls.check | cls.cash, validate=False)
        cls.check_slip = cls.batch.slip_ids.filtered(lambda s: s.employee_id == cls.check)
        cls.check_slip.input_line_ids = [(0, 0, {'input_type_id': cls._input_type('GA_ADVANCE').id, 'amount': 25_000})]
        cls.batch.slip_ids.compute_sheet()
        cls.batch.action_validate()
        cls.slips = cls.batch.slip_ids
        cls.moves = cls.slips.move_id

    def _slip(self, employee):
        return self.slips.filtered(lambda s: s.employee_id == employee)

    def _move_lines(self, employee, code):
        account = self._account(code)
        return self._slip(employee).move_id.line_ids.filtered(lambda line: line.account_id == account)

    def test_one_balanced_move_per_payslip_without_adjustment(self):
        self.assertEqual(len(self.moves), 3, 'une pièce par bulletin (regroupement désactivé par défaut)')
        journal = self.env['account.chart.template'].with_company(self.company).ref('hr_payroll_account_journal')
        for move in self.moves:
            self.assertEqual(move.journal_id, journal)
            self.assertAlmostEqual(sum(move.line_ids.mapped('debit')), sum(move.line_ids.mapped('credit')), places=2)
            self.assertFalse(move.line_ids.filtered(lambda line: line.name == 'Adjustment Entry'))

    def test_each_rule_on_its_account(self):
        for slip in self.slips:
            self.assertEqual(
                {account.code: round(balance, 2) for account, balance in self._balances(slip.move_id).items()},
                {account.code: round(balance, 2) for account, balance in self._expected_balances(slip).items()},
                slip.employee_id.name,
            )

    def test_net_credited_to_422_per_employee(self):
        net = sum(self.slips.line_ids.filtered(lambda line: line.code == 'NET').mapped('total'))
        lines = self.moves.line_ids.filtered(lambda line: line.account_id == self._account('422'))
        self.assertAlmostEqual(sum(lines.mapped('credit')) - sum(lines.mapped('debit')), net, places=2)
        for slip in self.slips:
            self.assertEqual(
                slip.move_id.line_ids.filtered(lambda line: line.account_id == self._account('422')).partner_id,
                slip.employee_id.work_contact_id,
            )

    def test_cash_rounding_has_no_entry(self):
        slip = self._slip(self.cash)
        totals = self._totals(slip)
        self.assertTrue(totals.get('GA_ROUND'), 'le net du salarié payé en espèces est arrondi')
        rule_names = slip.line_ids.filtered(lambda line: line.code in NO_ENTRY_RULES).salary_rule_id.mapped('name')
        self.assertFalse(slip.move_id.line_ids.filtered(lambda line: line.name in rule_names))
        net_line = self._move_lines(self.cash, '422')
        self.assertAlmostEqual(net_line.credit, totals['NET'], places=2, msg='le reliquat reste dans 422')

    def test_loan_installment_credits_4211(self):
        installment = -self._totals(self._slip(self.transfer))['GA_LOAN']
        self.assertEqual(installment, 30_000)
        line = self._move_lines(self.transfer, '4211')
        self.assertEqual((line.credit, line.debit), (30_000, 0))
        self.assertEqual(line.partner_id, self.transfer.work_contact_id)

    def test_advance_credits_4212(self):
        line = self._move_lines(self.check, '4212')
        self.assertEqual((line.credit, line.partner_id), (25_000, self.check.work_contact_id))

    def test_employer_charges(self):
        totals = self._totals(self._slip(self.transfer))
        employer = totals['GA_CNSS_PF'] + totals['GA_CNSS_AT'] + totals['GA_CNSS_AVID'] + totals['GA_CNAMGS_PAT']
        self.assertAlmostEqual(sum(self._move_lines(self.transfer, '6641').mapped('debit')), employer, places=2)
        self.assertAlmostEqual(self._move_lines(self.transfer, '4311').credit, totals['GA_CNSS_PF'], places=2)
        self.assertAlmostEqual(self._move_lines(self.transfer, '4312').credit, totals['GA_CNSS_AT'], places=2)
        self.assertAlmostEqual(
            sum(self._move_lines(self.transfer, '4313').mapped('credit')),
            totals['GA_CNSS_AVID'] - totals['GA_CNSS_SAL'],
            places=2,
            msg='4313 : pension patronale et part salariale CNSS',
        )
        self.assertAlmostEqual(
            sum(self._move_lines(self.transfer, '4472').mapped('credit')),
            totals['GA_FNH'] + totals['GA_CFP'] - totals['GA_TCS'] - totals.get('GA_FNH_SAL', 0),
            places=2,
        )
        self.assertAlmostEqual(self._move_lines(self.transfer, '4471').credit, -totals['GA_IRPP'], places=2)

    def test_benefit_in_kind_transfers_charges(self):
        benefits = sum(
            self._slip(self.check).line_ids.filtered(lambda line: line.code.startswith('GA_AN_')).mapped('total')
        )
        self.assertTrue(benefits)
        self.assertAlmostEqual(sum(self._move_lines(self.check, '6617').mapped('debit')), benefits, places=2)
        self.assertAlmostEqual(sum(self._move_lines(self.check, '781').mapped('credit')), benefits, places=2)

    def test_negative_gain_is_credited(self):
        employee = self._complete('Rappel négatif')
        slip = self._validated(employee, *SEPT, inputs={'GA_RECALL': -10_000})
        recall = slip.line_ids.filtered(lambda line: line.code == 'GA_RECALL')
        line = slip.move_id.line_ids.filtered(lambda line: line.name == recall.salary_rule_id.name)
        self.assertEqual((line.account_id, line.credit, line.debit), (self._account('6611'), 10_000, 0))

    def test_register_payment_on_422(self):
        self.assertTrue(self._account('422').reconcile)
        slip = self._slip(self.transfer)
        slip.move_id.action_post()
        action = slip.action_register_payment()
        self.assertEqual(action['res_model'], 'account.payment.register')
