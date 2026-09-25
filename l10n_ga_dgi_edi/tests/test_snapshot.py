from datetime import date

from psycopg2 import IntegrityError  # pylint: disable=import-error

from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import F16_IRPP, SEPT, GaDeclarationCase


@tagged('post_install', '-at_install')
class TestSnapshot(GaDeclarationCase):
    """Patron 10 (ADR-06, RG11, RG14) : instantané figé, empreinte, rectificative, unicité, échéance."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.slip = cls._f16_slip()

    def _validated(self, **values):
        declaration = self._declaration(**values)
        declaration.action_compute()
        declaration.with_user(self.declarant).action_validate()
        return declaration

    def test_validation_freezes_values(self):
        declaration = self._validated()
        self.assertEqual(self._box(declaration, 'B_IRPP').value_amount, F16_IRPP)
        self.assertRegex(declaration.sha256, r'^[0-9a-f]{64}$')
        self.assertTrue(declaration._integrity_ok())
        names = sorted(declaration.snapshot_attachment_ids.mapped('name'))
        self.assertEqual(len(names), 2)
        self.assertTrue(names[1].endswith('.xlsx'), names)
        self.assertTrue(all(att.res_id == declaration.id for att in declaration.snapshot_attachment_ids))
        self.assertTrue(all(att.raw for att in declaration.snapshot_attachment_ids))

    def test_payslip_changed_after_validation(self):
        declaration = self._validated()
        sha = declaration.sha256
        irpp_line = self._line(self.slip, 'GA_IRPP')
        irpp_line.sudo().total = -99_999  # bulletin altéré après coup
        declaration.invalidate_recordset()
        self.assertEqual(self._box(declaration, 'B_IRPP').value_amount, F16_IRPP)
        self.assertEqual(declaration.sha256, sha)
        self.assertTrue(declaration._integrity_ok())
        self.slip.sudo().action_payslip_cancel()
        self.assertEqual(self._box(declaration, 'B_IRPP').value_amount, F16_IRPP)
        self.assertTrue(declaration._integrity_ok())
        action = declaration.action_check_integrity()
        self.assertEqual(action['params']['type'], 'success')

    def test_frozen_values_locked(self):
        declaration = self._validated()
        with self.assertRaises(UserError):
            self._box(declaration, 'B_IRPP').value_amount = 1
        with self.assertRaises(UserError):
            declaration.detail_ids[:1].amount = 1
        with self.assertRaises(UserError):
            declaration.detail_ids[:1].unlink()
        with self.assertRaises(UserError):
            declaration.date_to = date(2026, 9, 29)
        declaration.filing_number = 'DEP-1'  # hors instantané : modifiable

    def test_tampering_detected(self):
        declaration = self._validated()
        self._box(declaration, 'B_IRPP').with_context(l10n_ga_declaration_engine=True).value_amount = 1
        self.assertFalse(declaration._integrity_ok())
        action = declaration.action_check_integrity()
        self.assertEqual(action['params']['type'], 'danger')

    def test_rectification(self):
        declaration = self._validated()
        with self.assertRaises(UserError):
            declaration.action_create_rectification()  # validée, pas encore déposée
        declaration.with_user(self.declarant).action_mark_filed()
        action = declaration.action_create_rectification()
        rectification = self.env['l10n_ga.declaration'].browse(action['res_id'])
        self.assertEqual(rectification.rectified_id, declaration)
        self.assertEqual(rectification.state, 'draft')
        self.assertIn('rectificative', rectification.name)
        self.assertEqual((rectification.date_from, rectification.date_to), SEPT)
        rectification.action_compute()
        self.assertFalse(rectification.issue_ids.filtered(lambda i: i.code == 'GA_DECL_DUPLICATE'))
        rectification.with_user(self.declarant).action_validate()
        self.assertEqual(declaration.rectification_ids, rectification)
        self.assertEqual(declaration.state, 'filed')
        self.assertTrue(declaration._integrity_ok())

    @mute_logger('odoo.sql_db')
    def test_unique_period(self):
        first = self._declaration()
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self._declaration()
        first.action_cancel()
        second = self._declaration()  # une annulée n'empêche pas de refaire la période (D-65)
        self.assertEqual(second.state, 'draft')
        other_type = self._declaration_type('T_OTHER')
        self._declaration(decl_type=other_type)  # autre imprimé, même période

    @mute_logger('odoo.sql_db')
    def test_dates_constraint(self):
        with self.assertRaises(IntegrityError), self.cr.savepoint():
            self._declaration(period=(date(2026, 9, 30), date(2026, 9, 1)))

    def test_due_date_and_periods(self):
        monthly = self._declaration()
        self.assertEqual(monthly.due_date, date(2026, 10, 15))
        self.assertEqual(monthly.name, 'T_PAY 09/2026')
        yearly_type = self._declaration_type('T_YEAR', periodicity='yearly', due_months=4, due_day=30)
        self.assertEqual(yearly_type._period_bounds(date(2026, 7, 4)), (date(2026, 1, 1), date(2026, 12, 31)))
        yearly = self._declaration(decl_type=yearly_type, period=(date(2026, 1, 1), date(2026, 12, 31)))
        self.assertEqual(yearly.due_date, date(2027, 4, 30))
        self.assertEqual(yearly.name, 'T_YEAR 2026')
        quarterly_type = self._declaration_type('T_QUARTER', periodicity='quarterly', due_day=31)
        self.assertEqual(quarterly_type._period_bounds(date(2026, 8, 12)), (date(2026, 7, 1), date(2026, 9, 30)))
        quarterly = self._declaration(decl_type=quarterly_type, period=(date(2026, 7, 1), date(2026, 9, 30)))
        self.assertEqual(quarterly.due_date, date(2026, 10, 31))
        self.assertEqual(quarterly.name, 'T_QUARTER T3 2026')
        self.assertEqual(quarterly_type._due_date(date(2027, 1, 31)), date(2027, 2, 28))  # jour borné
        self.assertEqual(self.decl_type._period_bounds(date(2026, 2, 14)), (date(2026, 2, 1), date(2026, 2, 28)))
        monthly.due_date = date(2026, 10, 16)  # échéance modifiable avant validation
        self.assertEqual(monthly.due_date, date(2026, 10, 16))

    def test_type_validity(self):
        decl_type = self._declaration_type('T_DATED', active_from=date(2026, 7, 17), active_to=date(2026, 12, 31))
        self.assertFalse(decl_type._is_active_on(date(2026, 7, 16)))
        self.assertTrue(decl_type._is_active_on(date(2026, 7, 17)))
        self.assertFalse(decl_type._is_active_on(date(2027, 1, 1)))
        self.assertIsNone(decl_type._template_bytes())
