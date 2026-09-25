import base64
import io
import zipfile
from datetime import date

from openpyxl import load_workbook

from odoo.tests import tagged

from .common import (
    F16_CFP,
    F16_CNAMGS,
    F16_CNSS,
    F16_FNH,
    F16_IRPP,
    F16_SOCIAL_BASE,
    F16_TCS,
    SEPT,
    GaDeclarationCase,
)

JUNE = (date(2026, 6, 1), date(2026, 6, 30))
JULY = (date(2026, 7, 1), date(2026, 7, 31))
DEC_2025 = (date(2025, 12, 1), date(2025, 12, 31))
JAN_2026 = (date(2026, 1, 1), date(2026, 1, 31))
RETENUES = F16_IRPP + F16_TCS + F16_FNH
CFP_BOXES = ('R49', 'R50', 'R51', 'R52', 'R53', 'R54', 'R55', 'R56')


@tagged('post_install', '-at_install')
class TestId10(GaDeclarationCase):
    """ID10 (base 06 §1, plan 4.2) : Σ des bulletins payés du mois, cadre CFP, gabarit officiel."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.id10 = cls._type('ID10')

    def _id10(self, period=SEPT, company=None):
        declaration = self._find(self.id10, period, company)
        self.assertEqual(len(declaration), 1, 'ID10 préparée à la validation des bulletins (Observer)')
        return declaration

    def test_type_data(self):
        self.assertEqual((self.id10.periodicity, self.id10.period_basis), ('monthly', 'payment_date'))
        self.assertEqual(self.id10._due_date(date(2026, 9, 30)), date(2026, 10, 15))
        self.assertEqual(self.id10.report_id, self.env.ref('l10n_ga_dgi_edi.action_report_id10'))
        self.assertTrue(self.id10._template_bytes().startswith(b'PK'))
        cells = dict(self.id10.box_ids.mapped(lambda b: (b.code, b.cell_ref)))
        self.assertEqual((cells['L40'], cells['L43'], cells['R56'], cells['HDR_YEAR']), ('P40', 'P43', 'R56', 'K15'))

    def test_f16_single_payslip(self):
        slip = self._f16_slip()
        declaration = self._id10()
        values = self._values(declaration)
        self.assertEqual(
            [values[code] for code in ('L40', 'L41', 'L42', 'L43')], [F16_IRPP, F16_TCS, F16_FNH, RETENUES]
        )
        # Cadre 3 : L1 + L2 + L5 = assiette sociale (transport exclu), base plafonnée, taux daté.
        self.assertEqual(values['R49'], 450_000)
        self.assertEqual(values['R50'], F16_SOCIAL_BASE - 450_000)
        self.assertEqual(values['R49'] + values['R50'] + values['R53'], F16_SOCIAL_BASE)
        self.assertEqual((values['R51'], values['R52']), (F16_CNSS, F16_CNAMGS))
        self.assertEqual((values['R54'], values['R55'], values['R56']), (F16_SOCIAL_BASE, 0.005, F16_CFP))
        self.assertEqual(declaration.amount_total, RETENUES + F16_CFP)
        self.assertEqual(values['HDR_NIF'], 'NIF-TEST')
        self.assertEqual((values['HDR_YEAR'], values['HDR_MONTH'], values['HDR_TAX_CENTER']), (2026, 9, 'LBV-01'))
        self.assertFalse(declaration.issue_ids)
        irpp = declaration.detail_ids.filtered(lambda d: d.box_id.code == 'L40')
        self.assertEqual((irpp.employee_id, irpp.amount), (slip.employee_id, F16_IRPP))

    def test_sum_of_paid_payslips_only(self):
        self._f16_slip()
        self._f16_slip(self._f16_employee('Deuxième'))
        self._f16_slip(self._f16_employee('Brouillon'), validate=False)
        values = self._values(self._id10())
        self.assertEqual(values['L43'], 2 * RETENUES)
        self.assertEqual(values['R56'], 2 * F16_CFP)

    def test_december_paid_in_january(self):
        self._f16_slip(period=DEC_2025, payment_date=date(2026, 1, 5))
        self.assertFalse(self._find(self.id10, DEC_2025))
        january = self._id10(JAN_2026)
        self.assertTrue(self._values(january)['L41'])
        self.assertEqual(january.due_date, date(2026, 2, 15))

    def test_fnh_rate_change_17_july_2026(self):
        employee = self._f16_employee()
        june, july = (self._f16_slip(employee, period) for period in (JUNE, JULY))
        fnh = [sum(self._line(slip, 'GA_FNH').mapped('total')) for slip in (june, july)]
        self.assertEqual(fnh, [F16_SOCIAL_BASE * 0.02, F16_FNH])  # 2 % puis 3 % (paramètre daté)
        self.assertEqual([self._values(self._id10(p))['L42'] for p in (JUNE, JULY)], fnh)

    def test_cfp_ceiling_per_employee(self):
        rich = self._employee('Cadre', 2_000_000, ssnid='CNSS-C', l10n_ga_nif='NIF-C')
        self._payslip(rich, *SEPT).action_payslip_done()
        values = self._values(self._id10())
        ceiling = self.env['hr.rule.parameter']._get_parameter_from_code('l10n_ga_cfp_ceiling', SEPT[1])
        self.assertEqual(values['R49'] + values['R50'] + values['R53'], 2_000_000)
        self.assertEqual(values['R54'], ceiling)
        self.assertEqual(values['R56'], ceiling * values['R55'])

    def test_cfp_on_id28_leaves_frame_blank(self):
        self.company.l10n_ga_cfp_declaration = 'id28'
        self._f16_slip()
        declaration = self._id10()
        values = self._values(declaration)
        self.assertTrue(all(values[code] is None for code in CFP_BOXES))
        self.assertEqual(values['L43'], RETENUES)
        self.assertEqual(declaration.amount_total, RETENUES)

    def test_multi_company(self):
        self._f16_slip()
        other = self.env['res.company'].create(
            {
                'name': 'Autre société Gabon',
                'country_id': self.env.ref('base.ga').id,
                'currency_id': self.company.currency_id.id,
            }
        )
        env = self.env(context=dict(self.env.context, allowed_company_ids=[other.id, self.company.id]))
        employee = env['hr.employee'].create(
            {
                'name': 'Salarié autre société',
                'company_id': other.id,
                'date_version': date(2025, 1, 1),
                'contract_date_start': date(2025, 1, 1),
                'wage': 300_000,
                'structure_type_id': self.structure_type.id,
                'ssnid': 'CNSS-O',
            }
        )
        slip = env['hr.payslip'].create(
            {'name': 'Autre', 'employee_id': employee.id, 'date_from': SEPT[0], 'date_to': SEPT[1]}
        )
        slip.compute_sheet()
        slip.action_payslip_done()
        own, foreign = self._id10(), self._id10(company=other)
        self.assertEqual(self._values(own)['L43'], RETENUES)
        self.assertEqual(foreign.detail_ids.employee_id, employee)
        self.assertNotIn(employee, own.detail_ids.employee_id)

    def test_template_filled_with_values(self):
        self._f16_slip()
        declaration = self._id10()
        declaration.with_user(self.declarant).action_validate()
        xlsx = declaration.snapshot_attachment_ids.filtered(lambda a: a.name.endswith('.xlsx'))
        content = base64.b64decode(xlsx.datas)
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            for name in archive.namelist():
                if name.startswith('xl/worksheets/'):
                    self.assertNotIn(b'<f>', archive.read(name), 'formules du modèle remplacées par des valeurs')
        sheet = load_workbook(io.BytesIO(content))['RASS-CFP']
        expected = {
            'K15': 2026,
            'Q15': 9,
            'E17': 'NIF-TEST',
            'E23': self.company.name,
            'P27': 'Libreville',
            'Q33': 'LBV-01',
            'P40': F16_IRPP,
            'P41': F16_TCS,
            'P42': F16_FNH,
            'P43': RETENUES,
            'R54': F16_SOCIAL_BASE,
            'R55': 0.005,
            'R56': F16_CFP,
        }
        self.assertEqual({cell: sheet[cell].value for cell in expected}, expected)
        self.assertEqual(sheet['B40'].value, 'Impôt sur le Revenu des Personnes Physiques :')  # gabarit intact
        report = declaration.snapshot_attachment_ids - xlsx
        html = base64.b64decode(report.datas).decode()
        self.assertIn('Détermination des retenues sur salaires', html)
        self.assertIn('NIF-TEST', html)
