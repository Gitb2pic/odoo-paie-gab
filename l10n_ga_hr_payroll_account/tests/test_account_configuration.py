import csv

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools.misc import file_path

from ..models.account_chart_template import JOURNAL, NO_ENTRY_RULES, RULE_ACCOUNTS
from ..models.l10n_ga_payroll_check import MissingRuleAccounts
from .common import SEPT, GaPayrollAccountCase


@tagged('post_install', '-at_install')
class TestAccountConfiguration(GaPayrollAccountCase):
    """Étape 3, RG17, D-58 à D-62 : table d'imputation, comptes par société, contrôle GA_NO_ACCOUNT."""

    def _assert_configured(self, company):
        chart = self.env['account.chart.template'].with_company(company)
        self.assertEqual(self.structure.with_company(company).journal_id, chart.ref(JOURNAL))
        for rule in self.structure.rule_ids.with_company(company):
            for key, template_xmlid in RULE_ACCOUNTS.get(rule.code, {}).items():
                self.assertEqual(rule[f'account_{key}'], chart.ref(template_xmlid), f'{rule.code} {key}')
        self.assertTrue(chart.ref('pcg_422').reconcile, 'D-59 : 422 lettrable')

    # --- table -----------------------------------------------------------------------------------

    def test_table_covers_every_rule(self):
        codes = set(self.structure.rule_ids.mapped('code'))
        self.assertEqual(codes, set(RULE_ACCOUNTS) | set(NO_ENTRY_RULES))
        self.assertFalse(set(RULE_ACCOUNTS) & set(NO_ENTRY_RULES))

    def test_table_matches_catalogue(self):
        with open(file_path('l10n_ga_hr_payroll/data/catalogue_rubriques_ga.csv'), encoding='utf-8-sig') as catalogue:
            rows = list(csv.DictReader(catalogue))
        self.assertEqual(len(rows), len(RULE_ACCOUNTS) + len(NO_ENTRY_RULES))
        for row in rows:
            if not row['account']:
                self.assertIn(row['code'], NO_ENTRY_RULES)
                continue
            key = 'credit' if row['code'] == 'NET' else 'debit'
            self.assertEqual(RULE_ACCOUNTS[row['code']][key], row['account'], row['code'])

    def test_every_template_account_exists(self):
        for accounts in RULE_ACCOUNTS.values():
            for template_xmlid in accounts.values():
                self.assertTrue(self._account(template_xmlid.removeprefix('pcg_')), template_xmlid)

    # --- configuration par société ---------------------------------------------------------------

    def test_company_configured_at_chart_load(self):
        self._assert_configured(self.company)

    def test_new_company_configured_when_chart_loaded(self):
        company = self._new_company('Nouvelle société Gabon')
        self.assertFalse(
            self.structure.rule_ids.filtered(lambda r: r.code == 'NET').with_company(company).account_credit
        )
        self._load_chart(company)
        self._assert_configured(company)
        self.assertNotEqual(self._account('422', company), self._account('422'))

    def test_install_hook_configures_existing_companies(self):
        rule = self.structure.rule_ids.filtered(lambda r: r.code == 'BASIC').with_company(self.company)
        rule.account_debit = False
        self.env['account.chart.template']._load_payroll_accounts('ga', self.company)
        self._assert_configured(self.company)

    def test_existing_accounts_kept_unless_overwrite(self):
        rule = self.structure.rule_ids.filtered(lambda r: r.code == 'BASIC').with_company(self.company)
        rule.account_debit = self._account('6618')
        ChartTemplate = self.env['account.chart.template']
        ChartTemplate._l10n_ga_configure_payroll_accounts(self.company)
        self.assertEqual(rule.account_debit, self._account('6618'), 'D-60 : réglage du comptable conservé')
        ChartTemplate._l10n_ga_configure_payroll_accounts(self.company, overwrite=True)
        self.assertEqual(rule.account_debit, self._account('6611'))

    def test_server_action_overwrites(self):
        rule = self.structure.rule_ids.filtered(lambda r: r.code == 'NET').with_company(self.company)
        rule.account_credit = self._account('4286')
        action = self.env.ref('l10n_ga_hr_payroll_account.action_l10n_ga_configure_payroll_accounts')
        action.with_context(active_model='res.company', active_ids=self.company.ids, active_id=self.company.id).run()
        self.assertEqual(rule.account_credit, self._account('422'))

    def test_company_without_chart_is_ignored(self):
        company = self._new_company('Société sans plan')
        logger = 'odoo.addons.l10n_ga_hr_payroll_account.models.account_chart_template'
        with self.assertLogs(logger, 'WARNING') as logs:
            self.env['account.chart.template']._l10n_ga_configure_payroll_accounts(company)
        self.assertEqual(len(logs.output), 2, 'journal absent, puis comptes absents en un seul message')
        self.assertIn('pcg_422', logs.output[1])
        self.assertFalse(
            self.structure.rule_ids.filtered(lambda r: r.code == 'NET').with_company(company).account_credit
        )

    # --- contrôle GA_NO_ACCOUNT ------------------------------------------------------------------

    def test_missing_account_blocks_the_run(self):
        employee = self._complete('Sans compte')
        self.structure.rule_ids.filtered(lambda r: r.code == 'BASIC').with_company(self.company).account_debit = False
        with self.assertRaises(UserError) as error:
            self._run(employee, validate=False)
        self.assertIn('règles de paie sans compte comptable (BASIC)', str(error.exception), 'RG26 : lot bloqué')

    def test_missing_account_blocks_single_payslip(self):
        employee = self._complete('Bulletin seul')
        self.structure.rule_ids.filtered(lambda r: r.code == 'GA_IRPP').with_company(self.company).account_debit = False
        slip = self._payslip(employee, *SEPT)
        with self.assertRaises(UserError) as error:
            slip.action_payslip_done()
        self.assertIn('GA_IRPP', str(error.exception))

    def test_check_skipped_without_payroll_journal(self):
        slip = self._payslip(self._complete('Sans journal'), *SEPT, compute_sheet=False)
        self.structure.with_company(self.company).journal_id = False
        self.assertFalse(MissingRuleAccounts().applies(slip))
        self.assertIn('GA_NO_ACCOUNT', [check.code for check in slip._l10n_ga_payroll_checks()])


@tagged('post_install', '-at_install')
class TestTwoCompanies(GaPayrollAccountCase):
    """Deux sociétés au plan « ga » validées ensemble : chaque pièce n'utilise que ses comptes."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other = cls._new_company('Deuxième société Gabon')
        cls._load_chart(cls.other)
        cls.env = cls.env(context=dict(cls.env.context, allowed_company_ids=[cls.company.id, cls.other.id]))

    def test_each_move_uses_its_company_accounts(self):
        first = self._run(self._complete('Salarié A'), validate=False)
        second = self._run(self._complete('Salarié B', company=self.other), company=self.other, validate=False)
        slips = first.slip_ids | second.slip_ids
        slips.action_payslip_done()
        for slip in slips:
            move = slip.move_id
            self.assertTrue(move)
            self.assertEqual(move.company_id, slip.company_id)
            self.assertEqual(move.line_ids.account_id.company_ids, slip.company_id)
            self.assertIn(self._account('422', slip.company_id), move.line_ids.account_id)
