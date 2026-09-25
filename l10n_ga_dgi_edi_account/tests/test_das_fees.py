import base64
from datetime import date

from odoo.tests import tagged

from .common import YEAR, GaWithholdingCase


@tagged('post_install', '-at_install')
class TestDasFees(GaWithholdingCase):
    """Annexes DAS ID23, ID24, ID26 sur une année (base 06 §3.2, plan 5, D-97)."""

    def _annual(self, code):
        return self.env['l10n_ga.declaration']._l10n_ga_prepare(self.company, self._type_account(code), *YEAR)

    @staticmethod
    def _values(declaration):
        return {line.code: line._value() for line in declaration.line_ids}

    def test_id26_matches_id18(self):
        self._pay(self._bill(self.provider, 100_000, day=date(2026, 1, 10)), day=date(2026, 1, 20))
        self._pay(self._bill(self.provider, 50_000, day=date(2026, 3, 5)), day=date(2026, 3, 20))
        id26 = self._annual('ID26')
        values = self._values(id26)
        self.assertEqual((values['TOTAL_PAID'], values['TOTAL_WITHHELD']), (150_000, 14_250))
        id18s = self.env['l10n_ga.declaration'].search(
            [('type_id.code', '=', 'ID18'), ('company_id', '=', self.company.id)]
        )
        self.assertEqual(len(id18s), 2)
        self.assertEqual(values['TOTAL_WITHHELD'], sum(d.amount_total for d in id18s))
        self.assertNotIn('GA_DAS_MONTHLY', id26.issue_ids.mapped('code'))
        id18s.filtered(lambda d: d.date_from.month == 3).action_cancel()
        id26.action_compute()
        self.assertIn('GA_DAS_MONTHLY', id26.issue_ids.mapped('code'))

    def test_id24_sections(self):
        cemac = self._partner('Cabinet Douala', l10n_ga_is_resident=False, country_id=self.env.ref('base.cm').id)
        self._pay(self._bill(self.foreigner, 200_000, day=date(2026, 2, 1)), day=date(2026, 2, 10))
        self._pay(self._bill(cemac, 100_000, day=date(2026, 2, 1)), day=date(2026, 2, 10))
        id24 = self._annual('ID24')
        values = self._values(id24)
        self.assertEqual((values['PAID_OTHER'], values['PAID_CEMAC']), (200_000, 100_000))
        self.assertEqual(values['TOTAL_WITHHELD'], 60_000)
        self.assertFalse(id24.issue_ids.filtered(lambda i: i.severity == 'blocking'))

    def test_id23_employee_and_partial_payment(self):
        lawyer = self._partner('Maître Nze', l10n_ga_fee_category='C', vat='NIF-AV')
        employee = self._f16_employee('Administrateur salarié')
        employee.work_contact_id.write({'l10n_ga_fee_category': 'A', 'vat': 'NIF-ADM'})
        self._pay(self._bill(lawyer, 300_000, day=date(2026, 4, 1)), day=date(2026, 4, 15))
        partial = self._bill(lawyer, 100_000, day=date(2026, 11, 1))
        self._pay(partial, day=date(2026, 12, 15), amount=40_000)
        self._pay(partial, day=date(2027, 1, 15))  # hors exercice
        self._pay(self._bill(employee.work_contact_id, 50_000, day=date(2026, 6, 1)), day=date(2026, 6, 5))
        id23 = self._annual('ID23')
        values = self._values(id23)
        self.assertEqual((values['PAID_OTHER'], values['PAID_EMPLOYEE']), (340_000, 50_000))
        rows = {d.partner_id: d.payload for d in id23.detail_ids}
        self.assertEqual(rows[lawyer]['profession'][:1], 'C')
        self.assertEqual(rows[employee.work_contact_id]['section'], 'employee')

    def test_annual_workbook(self):
        self._pay(self._bill(self.provider, 100_000, day=date(2026, 1, 10)), day=date(2026, 1, 20))
        id26 = self._annual('ID26')
        id26.with_user(self.declarant).action_validate()
        report = id26.snapshot_attachment_ids.filtered(lambda a: not a.name.endswith('.xlsx'))
        html = base64.b64decode(report.datas).decode()
        self.assertIn('ID26 — Prestataires non assujettis', html)
        self.assertIn('Prestataire local', html)
        self.assertEqual(id26.due_date, date(2027, 4, 30))
