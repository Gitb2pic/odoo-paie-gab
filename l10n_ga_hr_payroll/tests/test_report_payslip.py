from datetime import date

from odoo.tests import tagged

from .common import GaPayrollCase

SEPT = (date(2026, 9, 1), date(2026, 9, 30))
REPORT = 'l10n_ga_hr_payroll.action_report_payslip_ga'


@tagged('post_install', '-at_install')
class TestReportPayslip(GaPayrollCase):
    """F7, RG24, D-47, D-48 : bulletin imprimé figé, mentions, lignes classées."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company.write({'l10n_ga_nif': 'NIF-EMP', 'l10n_ga_cnss_number': 'CNSS-EMP'})
        cls.employee = cls._employee(
            'Bulletin Figé',
            450_000,
            start=date(2019, 3, 1),
            registration_number='M100',
            ssnid='CNSS-100',
            l10n_ga_nif='NIF-100',
            job_title='Comptable',
            children=1,
            l10n_ga_transport_trips='2',
        )
        bank = cls.env['res.bank'].create({'name': 'BGFI Bank'})
        account = cls.env['res.partner.bank'].create(
            {'acc_number': 'GA-0001', 'partner_id': cls.employee.work_contact_id.id, 'bank_id': bank.id}
        )
        cls.employee.bank_account_ids = [(4, account.id)]

    def _html(self, slip):
        html, _format = self.env['ir.actions.report']._render_qweb_html(REPORT, slip.ids)
        return html.decode()

    def test_structure_uses_gabon_report(self):
        slip = self._payslip(self.employee, *SEPT)
        self.assertEqual(self.structure.report_id, self.env.ref(REPORT))
        self.assertEqual(list(slip._get_pdf_reports()), [self.env.ref(REPORT)])

    def test_validated_payslip_reprinted_identically(self):
        slip = self._validated(self.employee, *SEPT, inputs={'GA_TRANSP': 40_000})
        before = self._html(slip)
        for text in ('Bulletin Figé', 'M100', 'Comptable', 'CNSS-100', 'NIF-EMP', 'GA-0001', '01/03/2019'):
            self.assertIn(text, before)
        self.employee.write(
            {
                'name': 'Nom Changé',
                'job_title': 'Directeur',
                'ssnid': 'AUTRE',
                'children': 4,
                'registration_number': 'M999',
            }
        )
        self.employee.version_id.write({'wage': 900_000, 'l10n_ga_payment_mode': 'cash'})
        self.employee.bank_account_ids.acc_number = 'GA-9999'
        self.company.l10n_ga_nif = 'NIF-NOUVEAU'
        self.env['hr.rule.parameter.value'].search(
            [('rule_parameter_id.code', '=', 'l10n_ga_cnss_ceiling')], order='date_from desc', limit=1
        ).parameter_value = '9999999'
        slip.invalidate_recordset()
        self.assertEqual(self._html(slip), before)

    def test_draft_marked_not_validated_and_reads_current_file(self):
        slip = self._payslip(self.employee, *SEPT)
        html = self._html(slip)
        self.assertIn('Bulletin non validé', html)
        self.assertIn('Bulletin Figé', html)
        self.employee.name = 'Nom du jour'
        self.assertIn('Nom du jour', self._html(slip))
        slip.action_payslip_done()
        self.assertNotIn('Bulletin non validé', self._html(slip))

    def test_draft_without_lines_prints_identity(self):
        slip = self._payslip(self.employee, *SEPT, compute_sheet=False)
        data = slip._l10n_ga_report_data()
        self.assertFalse(data['frozen'])
        self.assertEqual(data['l10n_ga_employee_name'], 'Bulletin Figé')
        self.assertFalse(data['l10n_ga_gross'])
        self.assertIn('Bulletin non validé', self._html(slip))

    def test_frozen_identity_and_report_data(self):
        slip = self._validated(self.employee, *SEPT)
        self.assertEqual(
            (slip.l10n_ga_employee_name, slip.l10n_ga_registration_number, slip.l10n_ga_ssnid, slip.l10n_ga_nif),
            ('Bulletin Figé', 'M100', 'CNSS-100', 'NIF-100'),
        )
        self.assertEqual((slip.l10n_ga_bank_name, slip.l10n_ga_bank_account), ('BGFI Bank', 'GA-0001'))
        self.assertEqual((slip.l10n_ga_hire_date, slip.l10n_ga_payment_mode), (date(2019, 3, 1), 'transfer'))
        self.assertEqual((slip.l10n_ga_company_nif, slip.l10n_ga_company_cnss), ('NIF-EMP', 'CNSS-EMP'))
        data = slip._l10n_ga_report_data()
        self.assertTrue(data['frozen'])
        self.assertEqual(data['payment_mode_label'], 'Virement')
        self.assertEqual(data['marital_label'], 'Single')
        self.assertEqual(data['l10n_ga_gross'], slip.l10n_ga_gross)

    def _rows(self, slip):
        return {row['code']: row for row in slip._l10n_ga_report_rows()}

    def test_rows_follow_the_model(self):
        """Plan 2.7 b : ordre du modèle, organismes sur une ligne, totaux (D-54, D-55)."""
        self.company.l10n_ga_cash_rounding = 500
        employee = self._employee('Modèle', 450_000, start=date(2019, 3, 1), l10n_ga_transport_trips='2')
        employee.version_id.l10n_ga_payment_mode = 'cash'
        slip = self._payslip(employee, *SEPT, inputs={'GA_TRANSP': 35_000, 'GA_RESP': 105_000})
        rows = slip._l10n_ga_report_rows()
        codes = [row['code'] for row in rows]
        self.assertEqual(codes, sorted(codes, key=int))
        by_code = {row['code']: row for row in rows}
        totals = self._totals(slip)
        # CNSS salariale et patronale (PF + AT + AVID) sur la même ligne, avec base et taux
        cnss = by_code['25150']
        self.assertEqual(cnss['name'], 'CNSS')
        self.assertEqual((cnss['base'], cnss['amount']), (555_000, totals['GA_CNSS_SAL']))
        self.assertEqual(cnss['employer_amount'], totals['GA_CNSS_PF'] + totals['GA_CNSS_AT'] + totals['GA_CNSS_AVID'])
        self.assertAlmostEqual(cnss['base'] * cnss['rate'] / 100, -totals['GA_CNSS_SAL'], delta=1)
        self.assertAlmostEqual(cnss['base'] * cnss['employer_rate'] / 100, cnss['employer_amount'], delta=1)
        self.assertEqual(by_code['25170']['employer_amount'], totals['GA_CNAMGS_PAT'])
        self.assertEqual((by_code['25300']['amount'], by_code['25300']['employer_amount']), (None, totals['GA_CFP']))
        # Sections : imposables → TOTAL BRUT → cotisations → impôts → non imposables → totaux
        self.assertLess(codes.index('10000'), codes.index('20900'))
        self.assertLess(codes.index('20900'), codes.index('25150'))
        self.assertLess(
            codes.index('32500'),
            codes.index(
                slip.line_ids.filtered(lambda line: line.code == 'GA_TRANSP').salary_rule_id.l10n_ga_print_code
            ),
        )
        self.assertEqual(by_code['20900']['amount'], totals['BASIC'])
        self.assertEqual(by_code['70000']['amount'], totals['BASIC'] + totals['GA_TRANSP'] + totals['GA_RESP'])
        self.assertEqual(by_code['70000']['amount'] + by_code['75000']['amount'], totals['NET'])
        self.assertEqual(by_code['26990']['amount'], totals['GA_CNSS_SAL'] + totals['GA_CNAMGS_SAL'])
        self.assertEqual(by_code['31490']['base'], slip._l10n_ga_report_data()['l10n_ga_tcs_base'])
        self.assertEqual(by_code['80900']['amount'], totals['GA_NET_PAY'])
        self.assertIn('80000', by_code, 'espèces : net, reliquat et arrondi imprimés')
        self.assertNotIn(None, [row['name'] for row in rows])

    def test_transfer_prints_net_to_pay_only(self):
        slip = self._payslip(self.employee, *SEPT)
        by_code = self._rows(slip)
        self.assertNotIn('80000', by_code)
        self.assertEqual(by_code['80900']['name'], 'NET À PAYER')

    def test_basic_salary_split_for_unpaid_absence(self):
        """E4 : salaire mensuel + absences non payées = ligne BASIC (affichage seulement, B2)."""
        employee = self._employee('Absent', 450_000, start=date(2019, 3, 1))
        self._absence(employee, 'GA_ABS_INJ', date(2026, 9, 7), date(2026, 9, 8))
        slip = self._payslip(employee, *SEPT)
        by_code = self._rows(slip)
        basic = self._totals(slip)['BASIC']
        self.assertLess(basic, 450_000)
        self.assertEqual(by_code['10000']['amount'], 450_000)
        self.assertAlmostEqual(by_code['10000']['amount'] + by_code['10050']['amount'], basic, delta=0.01)
        self.assertEqual(by_code['10050']['base'], 16)
        self.assertEqual(by_code['20900']['amount'], basic)
        full = self._rows(self._payslip(self.employee, *SEPT))
        self.assertNotIn('10050', full)

    def test_benefit_in_kind_rows(self):
        employee = self._employee('Logé', 450_000, start=date(2019, 3, 1), l10n_ga_benefit_housing=True)
        slip = self._payslip(employee, *SEPT)
        by_code = self._rows(slip)
        self.assertEqual(by_code['30200']['amount'], self._totals(slip)['GA_AN_LOGT'])
        self.assertEqual(by_code['70000']['amount'] + by_code['75000']['amount'], self._totals(slip)['NET'])

    def test_line_bases_frozen(self):
        slip = self._validated(self.employee, *SEPT)
        cnss = slip.line_ids.filtered(lambda line: line.code == 'GA_CNSS_SAL')
        self.assertTrue(cnss.l10n_ga_base)
        self.assertAlmostEqual(cnss.l10n_ga_base * cnss.l10n_ga_rate / 100, -cnss.total, delta=1)
        self.assertTrue(slip.line_ids.filtered(lambda line: line.code == 'GA_TCS').l10n_ga_rate)

    def test_leave_counters_frozen(self):
        leave_type = self.env.ref('l10n_ga_hr_payroll.leave_type_ga_cp')
        employee = self._employee('Congés', 450_000, start=date(2019, 3, 1))
        allocation = self.env['hr.leave.allocation'].create(
            {
                'name': 'Droits 2026',
                'employee_id': employee.id,
                'holiday_status_id': leave_type.id,
                'number_of_days': 24,
                'date_from': date(2026, 1, 1),
            }
        )
        allocation.action_approve()
        slip = self._validated(employee, *SEPT)
        self.assertEqual((slip.l10n_ga_leave_acquired, slip.l10n_ga_leave_taken), (24, 0))
        self.assertEqual(slip.l10n_ga_leave_balance, 24)
        self.assertEqual(slip.l10n_ga_leave_base, self._totals(slip)['BASIC'])
        html = self._html(slip)
        self.assertIn('Base congés', html)
        self.assertIn('Émargement employé(e)', html)

    def test_amount_format(self):
        payslip = self.env['hr.payslip']
        self.assertEqual(payslip._l10n_ga_fmt(1234567.4), '1\u202f234\u202f567')
        self.assertEqual(payslip._l10n_ga_fmt(173.333, 2), '173,33')
        self.assertEqual(payslip._l10n_ga_fmt(None), '')
        self.assertEqual(payslip._l10n_ga_fmt(0), '0')
        self.assertEqual((payslip._l10n_ga_fmt_rate(2.5), payslip._l10n_ga_fmt_rate(16.0)), ('2,5', '16'))
        self.assertEqual(payslip._l10n_ga_fmt_rate(None), '')

    def test_pdf_pipeline(self):
        """Chaîne PDF du standard jusqu'à wkhtmltopdf (en test, Odoo renvoie le HTML sans lancer le binaire)."""
        slip = self._validated(self.employee, *SEPT)
        content, report_format = self.env['ir.actions.report']._render_qweb_pdf(REPORT, slip.ids)
        self.assertEqual(report_format, 'html')
        self.assertIn('BULLETIN DE SALAIRE', content.decode())
        self.assertEqual(content.decode().count('<!DOCTYPE html>'), 1)
