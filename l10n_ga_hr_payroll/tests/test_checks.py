from datetime import date

from odoo.exceptions import UserError
from odoo.tests import tagged

from ..models.l10n_ga_payroll_check import PAYROLL_CHECKS, CheckRule, run_checks
from .common import GaPayrollCase

AUG = (date(2026, 8, 1), date(2026, 8, 31))
SEPT = (date(2026, 9, 1), date(2026, 9, 30))


@tagged('post_install', '-at_install')
class TestPayrollChecks(GaPayrollCase):
    """F8, RG26, ADR-18, D-38 à D-40 : chaîne de contrôles du lot, blocage du calcul, pont natif."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.agreement = cls.env['l10n_ga.collective.agreement'].create(
            {
                'name': 'Convention contrôles',
                'code': 'CHK',
                'company_id': cls.company.id,
                'grade_ids': [(0, 0, {'category': 'C1', 'date_from': date(2012, 1, 1), 'minimum_wage': 295_400})],
            }
        )

    def _complete(self, name, start=date(2020, 1, 1), **values):
        """Salarié sans anomalie : n° CNSS, NIF, compte bancaire pour le virement."""
        employee = self._employee(name, 400_000, start=start, ssnid='CNSS-1', l10n_ga_nif='NIF-1', **values)
        bank = self.env['res.partner.bank'].create(
            {'acc_number': f'GA-{employee.id}', 'partner_id': employee.work_contact_id.id}
        )
        employee.bank_account_ids = [(4, bank.id)]
        return employee

    def _run(self, *employees, period=SEPT):
        run = self.env['hr.payslip.run'].create(
            {
                'name': 'Lot de test',
                'company_id': self.company.id,
                'date_start': period[0],
                'date_end': period[1],
                'structure_id': self.structure.id,
            }
        )
        for employee in employees:
            self.env['hr.payslip'].create(
                {
                    'name': f'{employee.name} {period[0]:%m/%Y}',
                    'employee_id': employee.id,
                    'date_from': period[0],
                    'date_to': period[1],
                    'payslip_run_id': run.id,
                }
            )
        return run

    def _set_sql(self, record, **values):
        """Données incohérentes introduites hors ORM (reprise SQL, étape 6) : les contraintes ne jouent pas."""
        assignments = ', '.join(f'{column} = %s' for column in values)
        self.env.cr.execute(
            f'UPDATE {record._table} SET {assignments} WHERE id = %s',
            (*values.values(), record.id),
        )
        record.invalidate_recordset()

    @staticmethod
    def _codes(run, severity=None):
        issues = run.l10n_ga_issue_ids
        if severity:
            issues = issues.filtered(lambda i: i.severity == severity)
        return sorted(issues.mapped('code'))

    # --- chaîne ----------------------------------------------------------------------------------

    def test_chain_is_the_documented_sequence(self):
        self.assertEqual(
            [check.code for check in PAYROLL_CHECKS],
            [
                'GA_NO_VERSION',
                'GA_NO_HIRE_DATE',
                'GA_NO_MARITAL',
                'GA_FORCED_PARTS_NO_REASON',
                'GA_BELOW_GRADE',
                'GA_ALLOWANCE_FORCED_NO_REASON',
                'GA_NO_CNSS',
                'GA_NO_NIF',
                'GA_NO_BANK',
                'GA_LOAN_OVER_RATIO',
            ],
        )
        blocking = {check.code for check in PAYROLL_CHECKS if check.severity == 'blocking'}
        self.assertEqual(
            blocking,
            {
                'GA_NO_VERSION',
                'GA_NO_HIRE_DATE',
                'GA_NO_MARITAL',
                'GA_FORCED_PARTS_NO_REASON',
                'GA_BELOW_GRADE',
                'GA_ALLOWANCE_FORCED_NO_REASON',
            },
        )

    def test_abstract_rule_and_custom_chain(self):
        slip = self._run(self._complete('Abstrait')).slip_ids
        with self.assertRaises(NotImplementedError):
            CheckRule().run(slip)
        self.assertTrue(CheckRule().applies(slip))
        self.assertEqual(run_checks(slip, checks=()), [])
        # préfixe : les modules supérieurs ajoutent leurs contrôles (GA_NO_ACCOUNT, étape 3)
        self.assertEqual(slip._l10n_ga_payroll_checks()[: len(PAYROLL_CHECKS)], PAYROLL_CHECKS)

    def test_complete_employee_has_no_issue_and_is_computed(self):
        run = self._run(self._complete('Complet'))
        run.action_l10n_ga_check()
        self.assertEqual(self._codes(run), [])
        run.action_confirm()
        self.assertTrue(run.slip_ids.line_ids)
        self.assertEqual(run.slip_ids.l10n_ga_payment_date, SEPT[1])

    def test_each_warning(self):
        employee = self._employee('Incomplet', 400_000, start=date(2020, 1, 1))  # ni CNSS, ni NIF, ni banque
        run = self._run(employee)
        run.action_l10n_ga_check()
        self.assertEqual(self._codes(run, 'warning'), ['GA_NO_BANK', 'GA_NO_CNSS', 'GA_NO_NIF'])
        self.assertEqual(self._codes(run, 'blocking'), [])
        self.assertEqual(run.l10n_ga_warning_count, 3)
        issue = run.l10n_ga_issue_ids.filtered(lambda i: i.code == 'GA_NO_CNSS')
        self.assertEqual((issue.res_model, issue.res_id), ('hr.version', employee.version_id.id))
        self.assertEqual(issue.action_open_record()['res_id'], employee.version_id.id)

    def test_no_bank_only_for_transfer(self):
        employee = self._employee('Espèces', 400_000, start=date(2020, 1, 1), ssnid='C', l10n_ga_nif='N')
        employee.version_id.l10n_ga_payment_mode = 'cash'
        run = self._run(employee)
        run.action_l10n_ga_check()
        self.assertEqual(self._codes(run), [])

    def test_warnings_do_not_block(self):
        run = self._run(self._employee('Avertissements', 400_000, start=date(2020, 1, 1)))
        run.action_confirm()
        slip = run.slip_ids
        self.assertTrue(slip.line_ids)
        slip._compute_issues()
        self.assertEqual(slip.error_count, 0)
        self.assertGreaterEqual(slip.warning_count, 3)
        slip.action_payslip_done()
        self.assertEqual(slip.state, 'validated')

    def test_missing_hire_date(self):
        employee = self._complete('Sans embauche')
        self._set_sql(employee.version_id, contract_date_start=None)
        run = self._run(employee)
        run.action_l10n_ga_check()
        self.assertIn('GA_NO_HIRE_DATE', self._codes(run, 'blocking'))

    def test_missing_marital(self):
        employee = self._complete('Sans situation')
        self._set_sql(employee.version_id, marital='union_libre')
        run = self._run(employee)
        run.action_l10n_ga_check()
        self.assertEqual(self._codes(run, 'blocking'), ['GA_NO_MARITAL'])

    def test_forced_parts_without_reason(self):
        employee = self._complete('Parts forcées')
        self._set_sql(employee.version_id, l10n_ga_tax_parts_forced=2, l10n_ga_tax_parts_forced_reason=None)
        run = self._run(employee)
        run.action_l10n_ga_check()
        self.assertEqual(self._codes(run, 'blocking'), ['GA_FORCED_PARTS_NO_REASON'])
        employee.version_id.l10n_ga_tax_parts_forced_reason = 'Attestation'
        run.action_l10n_ga_check()
        self.assertEqual(self._codes(run, 'blocking'), [])

    def test_wage_below_grade_minimum(self):
        grade = self.agreement.grade_ids
        employee = self._complete('Sous la grille', l10n_ga_agreement_id=self.agreement.id, l10n_ga_grade_id=grade.id)
        self.env['l10n_ga.agreement.grade'].create(
            {'agreement_id': self.agreement.id, 'category': 'C1', 'date_from': SEPT[0], 'minimum_wage': 450_000}
        )
        run = self._run(employee)
        run.action_l10n_ga_check()
        self.assertEqual(self._codes(run, 'blocking'), ['GA_BELOW_GRADE'])
        august = self._run(employee, period=AUG)
        august.action_l10n_ga_check()
        self.assertEqual(self._codes(august, 'blocking'), [])

    def test_allowance_forced_without_reason(self):
        employee = self._complete('Indemnité forcée')
        allowance = self.env['hr.salary.attachment'].create(
            {
                'employee_ids': [(4, employee.id)],
                'other_input_type_id': self._input_type('GA_TRANSP').id,
                'monthly_amount': 20_000,
                'date_start': date(2026, 1, 1),
                'duration_type': 'unlimited',
                'description': 'Transport',
            }
        )
        self._set_sql(allowance, l10n_ga_forced_taxable=True, l10n_ga_forced_reason=None)
        run = self._run(employee)
        run.action_l10n_ga_check()
        self.assertEqual(self._codes(run, 'blocking'), ['GA_ALLOWANCE_FORCED_NO_REASON'])
        issue = run.l10n_ga_issue_ids
        self.assertEqual((issue.res_model, issue.res_id), ('hr.salary.attachment', allowance.id))

    def test_no_version_on_period(self):
        employee = self._complete('Futur', start=date(2026, 10, 1))
        run = self._run(employee)
        run.action_l10n_ga_check()
        self.assertIn('GA_NO_VERSION', self._codes(run, 'blocking'))

    def test_loan_installment_over_ratio(self):
        employee = self._complete('Emprunteur')
        august = self._validated(employee, *AUG)
        net = self._totals(august)['NET']
        loan = self.env['l10n_ga.employee.loan'].create(
            {
                'employee_id': employee.id,
                'company_id': self.company.id,
                'date': SEPT[0],
                'amount': round(net * 0.5) * 2,
                'installment_count': 2,
                'first_due_date': SEPT[0],
                'derogation': True,
                'derogation_reason': 'Accord de la direction',
            }
        )
        loan.action_compute_schedule()
        loan.action_approve()
        run = self._run(employee)
        run.action_l10n_ga_check()
        self.assertEqual(self._codes(run, 'warning'), ['GA_LOAN_OVER_RATIO'])
        self.assertEqual(run.l10n_ga_issue_ids.res_id, loan.id)

    def test_loan_within_ratio_no_issue(self):
        employee = self._complete('Emprunteur sage')
        self._validated(employee, *AUG)
        loan = self.env['l10n_ga.employee.loan'].create(
            {
                'employee_id': employee.id,
                'company_id': self.company.id,
                'date': SEPT[0],
                'amount': 20_000,
                'installment_count': 2,
                'first_due_date': SEPT[0],
            }
        )
        loan.action_compute_schedule()
        loan.action_approve()
        run = self._run(employee)
        run.action_l10n_ga_check()
        self.assertEqual(self._codes(run), [])

    # --- blocage RG26 et pont natif --------------------------------------------------------------

    def test_checks_are_idempotent(self):
        run = self._run(self._employee('Deux fois', 400_000, start=date(2020, 1, 1)))
        run.action_l10n_ga_check()
        first = run.l10n_ga_issue_ids
        run.action_l10n_ga_check()
        self.assertEqual(len(run.l10n_ga_issue_ids), len(first))
        self.assertFalse(first.exists())

    def test_blocking_issue_prevents_run_computation(self):
        blocked = self._complete('Bloquant')
        other = self._complete('Correct')
        self._set_sql(blocked.version_id, marital='union_libre')
        run = self._run(blocked, other)
        with self.assertRaisesRegex(UserError, 'situation familiale'):
            run.action_confirm()
        run.slip_ids.compute_sheet()  # calcul direct des bulletins : même blocage, sans erreur
        self.assertFalse(run.slip_ids.line_ids, 'aucun bulletin du lot n’est calculé (RG26)')
        self.assertEqual(run.l10n_ga_blocking_count, 1)
        blocked.version_id.marital = 'single'
        run.action_confirm()
        self.assertEqual(run.l10n_ga_blocking_count, 0)
        self.assertEqual(len(run.slip_ids.filtered('line_ids')), 2)

    def test_generate_payslips_creates_but_does_not_compute_blocked_run(self):
        blocked = self._complete('Généré bloqué')
        self._set_sql(blocked.version_id, l10n_ga_tax_parts_forced=3, l10n_ga_tax_parts_forced_reason=None)
        run = self._run(period=SEPT)
        run.generate_payslips(employee_ids=blocked.ids)
        self.assertEqual(len(run.slip_ids), 1)
        self.assertFalse(run.slip_ids.line_ids)
        self.assertEqual(self._codes(run, 'blocking'), ['GA_FORCED_PARTS_NO_REASON'])

    def test_native_bridge_blocks_validation(self):
        employee = self._complete('Pont natif')
        self._set_sql(employee.version_id, marital='union_libre')
        run = self._run(employee)
        run.action_l10n_ga_check()
        slip = run.slip_ids
        slip._compute_issues()
        self.assertGreater(slip.error_count, 0)
        self.assertIn('situation familiale', str(slip.issues))
        with self.assertRaises(UserError):
            slip.action_payslip_done()

    def test_payment_date_of_run_goes_to_slips(self):
        run = self._run(self._complete('Payé le 5'))
        self.assertEqual(run.l10n_ga_payment_date, SEPT[1])
        run.l10n_ga_payment_date = date(2026, 10, 5)
        self.assertEqual(run.slip_ids.l10n_ga_payment_date, date(2026, 10, 5))

    def test_issue_company_and_record_rule(self):
        run = self._run(self._employee('Société', 400_000, start=date(2020, 1, 1)))
        run.action_l10n_ga_check()
        self.assertEqual(run.l10n_ga_issue_ids.company_id, self.company)
        other = self.env['res.company'].create({'name': 'Autre société'})
        user = self.env['res.users'].create(
            {
                'name': 'Gestionnaire autre société',
                'login': 'ga_other_company_payroll',
                'company_id': other.id,
                'company_ids': [(6, 0, other.ids)],
                'group_ids': [(6, 0, self.env.ref('hr_payroll.group_hr_payroll_user').ids)],
            }
        )
        issues = (
            self.env['l10n_ga.check.issue']
            .with_user(user)
            .with_context(allowed_company_ids=other.ids)
            .search([('payslip_run_id', '=', run.id)])
        )
        self.assertFalse(issues)
        own = self.env['l10n_ga.check.issue'].search([('payslip_run_id', '=', run.id)])
        self.assertEqual(own, run.l10n_ga_issue_ids)

    def test_run_actions(self):
        run = self._run(self._complete('Actions'))
        self.assertTrue(run.l10n_ga_is_ga)
        self.assertEqual(run.action_l10n_ga_input_import()['context'], {'default_payslip_run_id': run.id})
        self.assertEqual(run.action_l10n_ga_issues()['domain'], [('payslip_run_id', '=', run.id)])
