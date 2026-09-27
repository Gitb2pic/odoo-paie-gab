import base64
from ast import literal_eval
from datetime import date

from odoo.tests import tagged

from .common import F16_CFP, F16_FNH, F16_IRPP, F16_TCS, SEPT, GaDeclarationCase

Q3 = (date(2026, 7, 1), date(2026, 9, 30))
NNBSP = '\u202f'  # séparateur des milliers des imprimés (comme le rendu du classeur)


@tagged('post_install', '-at_install')
class TestForms(GaDeclarationCase):
    """ADR-20, FIX 03 : vue ID10 et imprimés au format de la V1, lus sur les cases figées ; menus de la paie."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._f16_slip()
        cls.id10 = cls._find(cls._type('ID10'))

    def _html(self, declaration):
        """Rendu de l'imprimé du type (HTML en mode test, PDF en production)."""
        content, _report_type = declaration._render_pdf()
        return content.decode()

    # --- vue ID10 --------------------------------------------------------------------------------

    def test_id10_display_fields_read_boxes(self):
        values = self._values(self.id10)
        decl = self.id10
        self.assertEqual((decl.id10_irpp, decl.id10_tcs, decl.id10_fnh), (F16_IRPP, F16_TCS, F16_FNH))
        self.assertEqual(decl.id10_withholding_total, values['L43'])
        self.assertEqual((decl.id10_cfp_base, decl.id10_cfp_amount), (values['R54'], F16_CFP))
        self.assertAlmostEqual(decl.id10_cfp_rate, values['R55'] * 100)
        self.assertEqual(decl.id10_cfp_l3, values['R51'])
        self.assertFalse(decl.id10_cfp_blank)
        self.assertEqual((decl.id10_nif, decl.id10_city, decl.id10_tax_center), ('NIF-TEST', 'Libreville', 'LBV-01'))
        self.assertTrue(decl.amount_total_words.endswith('francs CFA'))
        self.assertIn('mille', decl.amount_total_words)

    def test_id10_display_fields_follow_frozen_value(self):
        """La vue affiche la case stockée, jamais un recalcul : une case modifiée est reprise telle quelle."""
        self._box(self.id10, 'L40').value_amount = 1
        self.id10.invalidate_recordset(['id10_irpp'])
        self.assertEqual(self.id10.id10_irpp, 1)

    def test_id10_cfp_on_id28(self):
        self.company.l10n_ga_cfp_declaration = 'id28'
        self.id10.action_compute()
        self.assertTrue(self.id10.id10_cfp_blank)
        self.assertEqual(self.id10.id10_cfp_amount, 0)
        self.assertIn("CFP déclarée sur l'imprimé ID28", self._html(self.id10))

    def test_id10_action_uses_v1_views(self):
        action = self.env.ref('l10n_ga_dgi_edi.l10n_ga_declaration_action_id10')
        views = {v.view_mode: v.view_id for v in action.view_ids}
        self.assertEqual(views['form'], self.env.ref('l10n_ga_dgi_edi.l10n_ga_declaration_view_form_id10'))
        self.assertEqual(literal_eval(action.domain), [('type_code', '=', 'ID10')])
        self.assertEqual(literal_eval(action.context)['default_type_id'], self.id10.type_id.id)
        found = self.env['l10n_ga.declaration'].search(literal_eval(action.domain))
        self.assertIn(self.id10, found)
        self.assertEqual(set(found.mapped('type_code')), {'ID10'})

    # --- imprimés ----------------------------------------------------------------------------------

    def test_id10_form_report(self):
        html = self._html(self.id10)
        for text in (
            'RETENUES À LA SOURCE SUR LES SALAIRES ET',
            '1 - Identification du contribuable',
            '2 - Détermination des retenues sur salaires à payer',
            '3 - Détermination de la Contribution à la Formation Professionnelle à payer',
            "4 - Règlement de l'impôt",
            'Septembre 2026',
            'NIF-TEST',
            f'{F16_IRPP:,}'.replace(',', NNBSP),
            f'{F16_TCS:,}'.replace(',', NNBSP),
            '0,50 %',
        ):
            with self.subTest(text=text):
                self.assertIn(text, html)

    def test_id10_snapshot_is_v1_form(self):
        self.id10.with_user(self.declarant).action_validate()
        report = self.id10.snapshot_attachment_ids.filtered(lambda a: not a.name.endswith('.xlsx'))
        html = base64.b64decode(report.datas).decode()
        self.assertIn('RETENUES À LA SOURCE SUR LES SALAIRES ET', html)
        self.assertIn(self.id10.sha256, html)

    def test_print_actions(self):
        form = self.id10.action_print_form()
        self.assertEqual(form['report_name'], 'l10n_ga_dgi_edi.report_form')
        workbook = self.id10.action_print_workbook()
        self.assertEqual(workbook['report_name'], 'l10n_ga_dgi_edi.report_declaration')
        self.assertEqual(self.id10._l10n_ga_workbook_report(), self.env.ref('l10n_ga_dgi_edi.action_report_id10'))
        generic = self._declaration()
        self.assertEqual(generic._l10n_ga_form_template(), 'l10n_ga_dgi_edi.form_generic')
        self.assertEqual(generic._l10n_ga_workbook_report(), self.env.ref('l10n_ga_dgi_edi.action_report_declaration'))

    def test_generic_form_report(self):
        generic = self._declaration()
        generic.action_compute()
        html = self._html(generic)
        self.assertIn('IMPRIMÉ T_PAY', html)
        self.assertIn(f'{F16_IRPP:,}'.replace(',', NNBSP), html)

    def test_dts_form_report(self):
        dts = self._find(self._type('DTS_CNSS'), Q3)
        html = self._html(dts)
        self.assertIn('DÉCLARATION TRIMESTRIELLE DES SALAIRES CNSS', html)
        self.assertIn('CNSS-EMP', html)
        self.assertIn('F16', html)  # une ligne par salarié
        self.assertIn('Total des cotisations', html)

    def test_id28_form_report(self):
        self.company.l10n_ga_cfp_declaration = 'id28'
        id28 = self.env['l10n_ga.declaration']._l10n_ga_prepare(self.company, self._type('ID28'), *SEPT)
        html = self._html(id28)
        self.assertIn('FORMATION PROFESSIONNELLE', html)
        self.assertIn(f'{F16_CFP:,}'.replace(',', NNBSP), html)

    # --- formatage ---------------------------------------------------------------------------------

    def test_formatting_helpers(self):
        fmt = self.id10._l10n_ga_fmt
        self.assertEqual((fmt(1_234_567), fmt(None), fmt(''), fmt('texte')), ('1\u202f234\u202f567', '', '', 'texte'))
        self.assertEqual(fmt(0.5, 2), '0,50')
        self.assertEqual(self.id10._l10n_ga_month_label(), 'Septembre 2026')
        self.assertEqual(self.id10._l10n_ga_date('2026-09-30'), '30/09/2026')
        self.assertEqual(self.id10._l10n_ga_words(1_500), 'mille cinq cents francs CFA')
        self.assertEqual(self.id10._l10n_ga_date(False), '')
        self.assertEqual(self.id10._l10n_ga_payment_modes(), '')
        self.assertTrue(self.id10._l10n_ga_details(employees=True))
        self.assertEqual(self.id10._l10n_ga_details(box_code='NONE'), [])

    # --- menus de la paie : déclarations de salaires seulement ------------------------------------

    def test_payroll_actions_scope(self):
        self.assertEqual(self._type('ID10').scope, 'payroll')
        self.assertEqual(self.id10.scope, 'payroll')
        for xmlid in ('l10n_ga_declaration_action', 'l10n_ga_declaration_action_dashboard'):
            with self.subTest(action=xmlid):
                action = self.env.ref(f'l10n_ga_dgi_edi.{xmlid}')
                self.assertEqual(literal_eval(action.domain), [('scope', '=', 'payroll')])
        payments = self.env.ref('l10n_ga_dgi_edi.l10n_ga_declaration_payment_action')
        self.assertEqual(literal_eval(payments.domain), [('declaration_id.scope', '=', 'payroll')])
        menus = self.env.ref('l10n_ga_dgi_edi.menu_l10n_ga_declaration_root').child_id
        self.assertTrue(
            {'ID10 - Retenues mensuelles', 'DTS - Cotisations trimestrielles', 'DAS - ID19 à ID22'}
            <= set(menus.mapped('name'))
        )
