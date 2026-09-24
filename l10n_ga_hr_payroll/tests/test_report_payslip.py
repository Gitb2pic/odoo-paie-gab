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

    def test_report_lines_classified(self):
        self.company.l10n_ga_cash_rounding = 500
        employee = self._employee('Espèces classées', 450_000, start=date(2019, 3, 1))
        employee.version_id.l10n_ga_payment_mode = 'cash'
        slip = self._payslip(employee, *SEPT, inputs={'GA_TRANSP': 40_000})
        kinds = {line['code']: line['kind'] for line in slip._l10n_ga_report_lines()}
        self.assertEqual(kinds['BASIC'], 'gain')
        self.assertEqual(kinds['GA_TRANSP'], 'gain')
        self.assertEqual(kinds['GA_CNSS_SAL'], 'deduction')
        self.assertEqual(kinds['GA_IRPP'], 'deduction')
        self.assertEqual(kinds['GA_CNSS_PF'], 'employer')
        self.assertEqual((kinds['GROSS'], kinds['NET']), ('total', 'total'))
        self.assertEqual(kinds['GA_NET_PAY'], 'pay')
        html = self._html(slip)
        self.assertIn('Net à payer', html)
        self.assertIn('Cumuls de l’année', html)
        self.assertIn('Reliquat d’arrondi reporté', html)

    def test_benefit_in_kind_line(self):
        employee = self._employee('Logé', 450_000, start=date(2019, 3, 1), l10n_ga_benefit_housing=True)
        slip = self._payslip(employee, *SEPT)
        benefits = [line for line in slip._l10n_ga_report_lines() if line['kind'] == 'benefit']
        self.assertTrue(benefits)
        self.assertIn('avantage en nature, non versé', self._html(slip))

    def test_amount_format(self):
        self.assertEqual(self.env['hr.payslip']._l10n_ga_fmt(1234567.4), '1 234 567')
        self.assertEqual(self.env['hr.payslip']._l10n_ga_fmt(False), '0')

    def test_pdf_pipeline(self):
        """Chaîne PDF du standard jusqu'à wkhtmltopdf (en test, Odoo renvoie le HTML sans lancer le binaire)."""
        slip = self._validated(self.employee, *SEPT)
        content, report_format = self.env['ir.actions.report']._render_qweb_pdf(REPORT, slip.ids)
        self.assertEqual(report_format, 'html')
        self.assertIn('Bulletin de paie', content.decode())
