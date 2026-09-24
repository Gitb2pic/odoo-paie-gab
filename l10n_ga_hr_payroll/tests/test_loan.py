from datetime import date

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from ..lib.ga_fiscal_core.loans import seizable_portion
from .common import GaPayrollCase

AUG = (date(2026, 8, 1), date(2026, 8, 31))
SEPT = (date(2026, 9, 1), date(2026, 9, 30))
OCT = (date(2026, 10, 1), date(2026, 10, 31))


@tagged('post_install', '-at_install')
class TestLoan(GaPayrollCase):
    """F1, RG19-RG21 : octroi (patron 12), dérogation, échéancier, retenue, report, anticipé, départ."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.employee = cls._employee('Prêt ancien', 500_000, start=date(2020, 1, 1))
        cls.august = cls._validated(cls.employee, *AUG)
        cls.reference_net = cls._totals(cls.august)['NET']

    def _loan(self, employee=None, amount=300_000, count=3, **values):
        loan = self.env['l10n_ga.employee.loan'].create(
            {
                'employee_id': (employee or self.employee).id,
                'company_id': self.company.id,
                'date': date(2026, 9, 1),
                'amount': amount,
                'installment_count': count,
                'first_due_date': date(2026, 9, 1),
                **values,
            }
        )
        loan.action_compute_schedule()
        return loan

    def _approved(self, **values):
        loan = self._loan(**values)
        loan.action_approve()
        return loan

    @staticmethod
    def _loan_inputs(slip):
        return slip.input_line_ids.filtered('l10n_ga_loan_line_id')

    # --- échéancier et octroi --------------------------------------------------------------------

    def test_sequence_and_schedule(self):
        loan = self._loan(amount=100_000, count=3)
        self.assertTrue(loan.name.startswith('PRET/'))
        self.assertEqual(loan.line_ids.mapped('amount'), [33_333, 33_333, 33_334])
        self.assertEqual(loan.line_ids.mapped('due_date'), [date(2026, 9, 1), date(2026, 10, 1), date(2026, 11, 1)])
        self.assertEqual((loan.installment_amount, loan.remaining_amount), (33_334, 100_000))

    def test_approve_when_eligible(self):
        loan = self._approved()
        self.assertEqual(loan.state, 'approved')
        self.assertFalse(loan.eligibility_issues)
        self.assertFalse(loan.derogation_user_id)

    def test_refused_seniority(self):
        recent = self._employee('Prêt récent', 500_000, start=date(2025, 6, 1))
        self._validated(recent, *AUG)
        loan = self._loan(employee=recent)
        self.assertIn('Ancienneté', loan.eligibility_issues)
        with self.assertRaises(UserError) as error:
            loan.action_approve()
        self.assertIn('Ancienneté', str(error.exception))
        self.assertEqual(loan.state, 'draft')

    def test_refused_installment_over_40_percent(self):
        installment = int(self.reference_net * 0.4) + 10
        loan = self._loan(amount=installment * 2, count=2)
        with self.assertRaises(UserError) as error:
            loan.action_approve()
        self.assertIn('Mensualité', str(error.exception))

    def test_refused_without_reference_payslip(self):
        newcomer = self._employee('Prêt sans bulletin', 500_000, start=date(2020, 1, 1))
        loan = self._loan(employee=newcomer)
        with self.assertRaises(UserError) as error:
            loan.action_approve()
        self.assertIn('Mensualité', str(error.exception))

    def test_refused_outstanding_over_company_cap(self):
        self.company.l10n_ga_loan_outstanding_cap = 500_000
        self._approved(amount=300_000)
        loan = self._loan(amount=300_000)
        with self.assertRaises(UserError) as error:
            loan.action_approve()
        self.assertIn('Encours', str(error.exception))
        self.company.l10n_ga_loan_outstanding_cap = 0
        loan.action_approve()  # 0 = pas de plafond

    def test_derogation_requires_reason_and_is_traced(self):
        recent = self._employee('Prêt dérogation', 500_000, start=date(2025, 6, 1))
        self._validated(recent, *AUG)
        loan = self._loan(employee=recent)
        with self.assertRaises(ValidationError):
            loan.write({'derogation': True, 'derogation_reason': '  '})
        loan.write({'derogation': True, 'derogation_reason': 'Frais médicaux urgents'})
        loan.action_approve()
        self.assertEqual(loan.state, 'approved')
        self.assertEqual(loan.derogation_user_id, self.env.user)
        self.assertTrue(loan.derogation_date)
        self.assertTrue(any('Frais médicaux urgents' in message.body for message in loan.message_ids))

    def test_only_payroll_manager_approves(self):
        user = self.env['res.users'].create(
            {
                'name': 'Gestionnaire paie',
                'login': 'ga_payroll_user_loan',
                'company_id': self.company.id,
                'company_ids': [self.company.id],
                'group_ids': [(6, 0, [self.env.ref('hr_payroll.group_hr_payroll_user').id])],
            }
        )
        loan = self._loan()
        with self.assertRaises(UserError) as error:
            loan.with_user(user).action_approve()
        self.assertIn('responsable', str(error.exception))

    # --- paie : entrée GA_LOAN et retenue (RG21, D-30) ------------------------------------------

    def test_installment_on_payslip_of_the_period_only(self):
        loan = self._approved()
        slip = self._payslip(self.employee, *SEPT)
        inputs = self._loan_inputs(slip)
        self.assertEqual(inputs.l10n_ga_loan_line_id, loan.line_ids[0])
        self.assertEqual(self._totals(slip)['GA_LOAN'], -100_000)
        self.assertEqual(slip.input_line_ids.filtered(lambda line: line.code == 'GA_LOAN'), inputs)

    def test_withheld_at_validation_released_on_cancel(self):
        loan = self._approved()
        slip = self._payslip(self.employee, *SEPT)
        net_before = self._totals(slip)['NET']
        slip.action_payslip_done()
        first = loan.line_ids[0]
        self.assertEqual((first.state, first.payslip_id), ('withheld', slip))
        self.assertEqual((loan.state, loan.remaining_amount, loan.withheld_amount), ('running', 200_000, 100_000))
        self.assertEqual(net_before, self._totals(slip)['NET'])
        slip.action_payslip_cancel()
        self.assertEqual((first.state, first.payslip_id.id), ('to_pay', False))
        self.assertEqual(loan.state, 'approved')

    def test_released_when_back_to_draft(self):
        loan = self._approved()
        slip = self._payslip(self.employee, *SEPT)
        slip.action_payslip_done()
        slip.action_payslip_draft()
        self.assertEqual(loan.line_ids[0].state, 'to_pay')

    def test_installment_taken_by_one_payslip_only(self):
        self._approved()
        first = self._payslip(self.employee, *SEPT)
        second = self._payslip(self.employee, *SEPT)
        self.assertTrue(self._loan_inputs(first))
        self.assertFalse(self._loan_inputs(second))

    def test_modified_loan_input_refused_at_validation(self):
        self._approved()
        slip = self._payslip(self.employee, *SEPT)
        self._loan_inputs(slip).amount = 1_000  # sans recalcul du bulletin
        with self.assertRaises(UserError) as error:
            slip.action_payslip_done()
        self.assertIn('modifié', str(error.exception))

    def test_loan_paid_after_last_installment(self):
        loan = self._approved(amount=100_000, count=1)
        self._validated(self.employee, *SEPT)
        self.assertEqual((loan.state, loan.remaining_amount), ('paid', 0))

    def test_cancel_refused_after_withholding(self):
        loan = self._approved()
        self._validated(self.employee, *SEPT)
        with self.assertRaises(UserError):
            loan.action_cancel()

    def test_cancel_and_back_to_draft(self):
        loan = self._approved()
        loan.action_cancel()
        self.assertEqual(loan.state, 'cancelled')
        self.assertFalse(self._loan_inputs(self._payslip(self.employee, *SEPT)))
        loan.action_draft()
        self.assertEqual(loan.state, 'draft')
        with self.assertRaises(UserError):
            loan.action_draft()

    def test_schedule_only_in_draft(self):
        loan = self._approved()
        with self.assertRaises(UserError):
            loan.action_compute_schedule()

    # --- report et remboursement anticipé (D-33, D-34) ------------------------------------------

    def test_postpone(self):
        loan = self._approved()
        loan.line_ids[0].action_postpone()
        self.assertEqual(loan.line_ids[0].state, 'postponed')
        self.assertEqual(loan.line_ids[-1].due_date, date(2026, 12, 1))
        self.assertEqual(loan.remaining_amount, 300_000)
        self.assertFalse(self._loan_inputs(self._payslip(self.employee, *SEPT)))
        with self.assertRaises(UserError):
            loan.line_ids[0].action_postpone()

    def _early(self, loan, amount, mode, day=date(2026, 9, 15)):
        wizard = self.env['l10n_ga.loan.early.repayment'].create(
            {'loan_id': loan.id, 'amount': amount, 'mode': mode, 'date': day}
        )
        wizard.action_confirm()

    def test_early_repayment_outside_payroll(self):
        loan = self._approved()
        self._early(loan, 150_000, 'outside')
        to_pay = loan.line_ids.filtered(lambda line: line.state == 'to_pay')
        self.assertEqual(to_pay.mapped('amount'), [100_000, 50_000])
        self.assertEqual((loan.remaining_amount, loan.withheld_amount, loan.state), (150_000, 150_000, 'running'))

    def test_early_repayment_on_payslip(self):
        loan = self._approved()
        self._early(loan, 200_000, 'payslip')
        slip = self._payslip(self.employee, *SEPT)
        self.assertEqual(self._totals(slip)['GA_LOAN'], -300_000)
        slip.action_payslip_done()
        self.assertEqual((loan.state, loan.remaining_amount), ('paid', 0))

    def test_early_repayment_over_remaining_refused(self):
        loan = self._approved()
        with self.assertRaises(UserError):
            self._early(loan, 400_000, 'outside')
        self.assertEqual(loan.action_early_repayment()['res_model'], 'l10n_ga.loan.early.repayment')

    # --- départ : solde de tout compte, quotité saisissable (D-32) ------------------------------

    def test_departure_takes_whole_remaining(self):
        loan = self._approved()
        self.employee.version_id.contract_date_end = date(2026, 9, 30)
        slip = self._payslip(self.employee, *SEPT)
        self.assertEqual(self._totals(slip)['GA_LOAN'], -300_000)
        slip.action_payslip_done()
        self.assertEqual(loan.state, 'paid')

    def test_departure_capped_by_seizable_portion(self):
        employee = self._employee('Prêt départ', 150_000, start=date(2020, 1, 1))
        self._validated(employee, *AUG)
        loan = self._loan(employee=employee, amount=300_000, count=6)
        loan.write({'derogation': True, 'derogation_reason': 'Solde de tout compte (test)'})
        loan.action_approve()
        employee.version_id.contract_date_end = date(2026, 9, 30)
        slip = self._payslip(employee, *SEPT)
        withheld = -self._totals(slip)['GA_LOAN']
        net_before_loan = self._totals(slip)['NET'] + withheld
        brackets = slip._rule_parameter('l10n_ga_seizable_brackets')
        self.assertEqual(withheld, seizable_portion(net_before_loan, brackets))
        self.assertLess(withheld, 300_000)
        slip.action_payslip_done()
        self.assertEqual(loan.remaining_amount, 300_000 - withheld)
        self.assertEqual(loan.state, 'running')
        self.assertTrue(loan.activity_ids)

    # --- multi-société et bouton intelligent -----------------------------------------------------

    def test_multi_company_rule(self):
        other = self.env['res.company'].create({'name': 'Autre société', 'country_id': self.env.ref('base.ga').id})
        other_employee = self.env['hr.employee'].create({'name': 'Autre', 'company_id': other.id})
        foreign = self.env['l10n_ga.employee.loan'].create(
            {'employee_id': other_employee.id, 'company_id': other.id, 'amount': 1_000, 'installment_count': 1}
        )
        user = self.env['res.users'].create(
            {
                'name': 'Paie société 1',
                'login': 'ga_payroll_user_mc',
                'company_id': self.company.id,
                'company_ids': [self.company.id],
                'group_ids': [(6, 0, [self.env.ref('hr_payroll.group_hr_payroll_user').id])],
            }
        )
        with self.assertRaises(AccessError):
            foreign.with_user(user).read(['amount'])

    def test_employee_smart_button(self):
        self._approved()
        self.assertEqual(self.employee.l10n_ga_loan_count, 1)
        action = self.employee.action_l10n_ga_loans()
        self.assertEqual(self.env['l10n_ga.employee.loan'].search(action['domain']).employee_id, self.employee)
