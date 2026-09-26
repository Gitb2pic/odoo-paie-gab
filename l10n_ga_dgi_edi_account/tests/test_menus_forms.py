from ast import literal_eval
from datetime import date

from odoo.exceptions import AccessError
from odoo.tests import tagged

from .common import YEAR, GaWithholdingCase

NNBSP = ' '  # séparateur des milliers des imprimés
ACCOUNT_CODES = {'ID18', 'ID27', 'ID23', 'ID24', 'ID26'}


@tagged('post_install', '-at_install')
class TestMenusForms(GaWithholdingCase):
    """FIX 03 : imprimés de la comptabilité dans Comptabilité → Analyse (et seulement eux), format V1."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._f16_slip()  # une ID10 (paie) existe à côté des déclarations de la comptabilité
        cls._pay(cls._bill(cls.provider, 100_000))
        cls.id18 = cls._find(cls._type_account('ID18'), (date(2026, 9, 1), date(2026, 9, 30)))
        cls.id10 = cls._find(cls._type('ID10'))
        cls.accountant = cls._user('ga_decl_accountant', 'account.group_account_user')

    def _html(self, declaration):
        content, _report_type = declaration._render_pdf()
        return content.decode()

    # --- rangement ---------------------------------------------------------------------------------

    def test_types_scope(self):
        types = self.env['l10n_ga.declaration.type'].search([('code', 'in', list(ACCOUNT_CODES))])
        self.assertEqual(set(types.mapped('scope')), {'account'})
        self.assertEqual(self._type('ID10').scope, 'payroll')

    def test_menu_under_accounting_reporting(self):
        root = self.env.ref('l10n_ga_dgi_edi_account.menu_l10n_ga_declaration_account_root')
        self.assertEqual(root.parent_id, self.env.ref('account.menu_finance_reports'))
        for menu in root.child_id:
            with self.subTest(menu=menu.name):
                action = menu.action
                found = self.env[action.res_model].search(literal_eval(action.domain or '[]'))
                declarations = found if action.res_model == 'l10n_ga.declaration' else found.declaration_id
                self.assertTrue(set(declarations.mapped('type_code')) <= ACCOUNT_CODES)
        dashboard = self.env.ref('l10n_ga_dgi_edi_account.l10n_ga_declaration_action_account')
        found = self.env['l10n_ga.declaration'].search(literal_eval(dashboard.domain))
        self.assertIn(self.id18, found)
        self.assertNotIn(self.id10, found)
        payroll = self.env.ref('l10n_ga_dgi_edi.l10n_ga_declaration_action')
        self.assertNotIn(self.id18, self.env['l10n_ga.declaration'].search(literal_eval(payroll.domain)))

    # --- sécurité : le comptable ne voit que les imprimés de la comptabilité ------------------------

    def test_accountant_sees_only_accounting_declarations(self):
        Declaration = self.env['l10n_ga.declaration'].with_user(self.accountant)
        visible = Declaration.search([('company_id', '=', self.company.id)])
        self.assertIn(self.id18, visible)
        self.assertEqual(set(visible.mapped('type_code')) - ACCOUNT_CODES, set())
        self.assertTrue(self.id18.with_user(self.accountant).line_ids)
        self.assertTrue(self.id18.with_user(self.accountant).detail_ids)
        with self.assertRaises(AccessError):
            self.id10.with_user(self.accountant).read(['amount_total'])
        lines = self.env['l10n_ga.declaration.line'].with_user(self.accountant).search([])
        self.assertFalse(lines.filtered(lambda line: line.declaration_id.scope != 'account'))
        issues = self.env['l10n_ga.check.issue'].with_user(self.accountant).search([])
        self.assertFalse(issues.filtered(lambda issue: issue.declaration_id.scope != 'account'))

    def test_accountant_recomputes_accounting_declaration(self):
        self.id18.with_user(self.accountant).action_compute()
        self.assertEqual(self.id18.amount_total, 9_500)

    def test_payroll_user_still_sees_everything(self):
        visible = self.env['l10n_ga.declaration'].with_user(self.declarant).search([])
        self.assertIn(self.id10, visible)
        self.assertIn(self.id18, visible)

    # --- imprimés V1 -------------------------------------------------------------------------------

    def test_id18_form(self):
        html = self._html(self.id18)
        self.assertIn('2 - Détail des retenues du mois', html)
        self.assertIn('NIF-PREST', html)
        self.assertIn(f'{9_500:,}'.replace(',', NNBSP), html)
        self.assertIn(f'{100_000:,}'.replace(',', NNBSP), html)
        self.assertEqual(self.id18._l10n_ga_form_template(), 'l10n_ga_dgi_edi_account.form_withholding')
        self.assertEqual(
            self.id18._l10n_ga_workbook_report(), self.env.ref('l10n_ga_dgi_edi.action_report_declaration')
        )

    def test_fee_annex_form(self):
        cemac = self._partner('Cabinet Douala', l10n_ga_is_resident=False, country_id=self.env.ref('base.cm').id)
        self._pay(self._bill(cemac, 100_000, day=date(2026, 2, 1)), day=date(2026, 2, 10))
        id24 = self.env['l10n_ga.declaration']._l10n_ga_prepare(self.company, self._type_account('ID24'), *YEAR)
        sections = id24._l10n_ga_fee_sections()
        self.assertEqual([len(rows) for _label, rows in sections], [1, 0])
        html = self._html(id24)
        self.assertIn('BORDEREAU RÉCAPITULATIF', html)
        self.assertIn('Cabinet Douala', html)
        self.assertIn('A) Bénéficiaires de la CEMAC', html)
        self.assertEqual(
            id24._l10n_ga_workbook_report(), self.env.ref('l10n_ga_dgi_edi_account.action_report_das_annex')
        )
