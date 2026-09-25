from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged

from ..models.l10n_ga_declaration import STATES
from .common import GaDeclarationCase

STATE_CODES = [code for code, _label in STATES]
ALLOWED = {
    ('draft', 'computed'),
    ('draft', 'cancel'),
    ('computed', 'computed'),
    ('computed', 'draft'),
    ('computed', 'validated'),
    ('computed', 'cancel'),
    ('validated', 'computed'),
    ('validated', 'filed'),
    ('filed', 'paid'),
    ('cancel', 'draft'),
}


@tagged('post_install', '-at_install')
class TestStateMachine(GaDeclarationCase):
    """Patron 7 : transitions gardées, droits du déclarant (02 §10, D-66)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.slip = cls._f16_slip()

    def test_transition_matrix(self):
        declaration = self._declaration()
        for source in STATE_CODES:
            for target in STATE_CODES:
                declaration.with_context(l10n_ga_declaration_engine=True).write({'state': source})
                with self.subTest(source=source, target=target):
                    if (source, target) in ALLOWED:
                        declaration._ensure_state(target)
                    else:
                        with self.assertRaises(UserError):
                            declaration._ensure_state(target)
        self.assertEqual(set(declaration._TRANSITIONS['paid']), set())

    def test_full_cycle_by_declarant(self):
        declaration = self._declaration().with_user(self.declarant)
        self.assertEqual(declaration.state, 'draft')
        declaration.action_compute()
        self.assertEqual(declaration.state, 'computed')
        declaration.action_compute()  # recalcul autorisé
        declaration.action_validate()
        self.assertEqual(declaration.state, 'validated')
        self.assertEqual(declaration.validated_by_id, self.declarant)
        declaration.filing_number = 'DEP-2026-10'
        declaration.action_mark_filed()
        self.assertEqual(declaration.state, 'filed')
        self.assertTrue(declaration.filing_date)
        declaration.action_mark_paid()
        self.assertEqual(declaration.state, 'paid')
        for action in ('action_compute', 'action_validate', 'action_mark_filed', 'action_reset_draft', 'action_cancel'):
            with self.subTest(action=action), self.assertRaises(UserError):
                getattr(declaration, action)()

    def test_forbidden_actions(self):
        declaration = self._declaration().with_user(self.declarant)
        with self.assertRaises(UserError):
            declaration.action_validate()  # brouillon non calculé
        with self.assertRaises(UserError):
            declaration.action_mark_filed()
        with self.assertRaises(UserError):
            declaration.action_mark_paid()
        with self.assertRaises(UserError):
            declaration.action_unvalidate()
        declaration.action_compute()
        with self.assertRaises(UserError):
            declaration.action_mark_paid()
        declaration.action_validate()
        with self.assertRaises(UserError):
            declaration.action_compute()  # jamais de recalcul d'une déclaration validée (RG14)
        with self.assertRaises(UserError):
            declaration.action_cancel()
        with self.assertRaises(UserError):
            declaration.action_create_rectification()

    def test_unvalidate_removes_snapshot(self):
        declaration = self._declaration().with_user(self.declarant)
        declaration.action_compute()
        declaration.action_validate()
        attachments = declaration.snapshot_attachment_ids
        self.assertTrue(attachments)
        declaration.action_unvalidate()
        self.assertEqual(declaration.state, 'computed')
        self.assertFalse(declaration.sha256)
        self.assertFalse(declaration.validated_by_id)
        self.assertFalse(attachments.exists())
        declaration.action_compute()  # de nouveau recalculable
        self.assertEqual(declaration.state, 'computed')

    def test_cancel_and_reset(self):
        declaration = self._declaration()
        declaration.action_compute()
        self.assertTrue(declaration.line_ids)
        declaration.action_reset_draft()
        self.assertEqual(declaration.state, 'draft')
        self.assertFalse(declaration.line_ids)
        self.assertFalse(declaration.detail_ids)
        declaration.action_cancel()
        self.assertEqual(declaration.state, 'cancel')
        declaration.action_reset_draft()
        self.assertEqual(declaration.state, 'draft')

    def test_rights_payroll_user_cannot_validate(self):
        declaration = self._declaration().with_user(self.payroll_user)
        declaration.action_compute()  # le gestionnaire de paie calcule
        self.assertEqual(declaration.state, 'computed')
        for action in ('action_validate', 'action_unvalidate', 'action_mark_filed', 'action_mark_paid'):
            with self.subTest(action=action), self.assertRaises(UserError):
                getattr(declaration, action)()

    def test_unlink_rules(self):
        declaration = self._declaration()
        declaration.action_compute()
        declaration.with_user(self.declarant).action_validate()
        with self.assertRaises(UserError):
            declaration.with_user(self.manager).unlink()
        draft = self._declaration(
            period=(self.slip.date_from.replace(month=8), self.slip.date_from.replace(day=31, month=8))
        )
        with self.assertRaises(AccessError):
            draft.with_user(self.payroll_user).unlink()
        draft.with_user(self.manager).unlink()
        self.assertFalse(draft.exists())

    def test_copy_forbidden(self):
        with self.assertRaises(UserError):
            self._declaration().copy()
